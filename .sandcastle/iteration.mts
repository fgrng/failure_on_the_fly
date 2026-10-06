// Ablauf einer Sandcastle-Iteration. Die Außenwelt kommt über drei schmale
// Schnittstellen herein (Tracker, Repo, Agents), damit sich der Ablauf gegen
// Fakes testen lässt. Die echten Implementierungen liegen in tracker.mts,
// repo.mts und agents.mts, verdrahtet in main.mts.

export type Ticket = {
  number: number;
  title: string;
  body: string;
  labels: string[];
  comments: string[];
};

/** Ein Issue mit dem Stand seiner Sub-Issues, etwa eine Spec. */
export type IssueSummary = {
  number: number;
  open: boolean;
  labels: string[];
  subIssues: { total: number; completed: number };
};

export type PlannedIssue = { id: string; title: string; branch: string };

/** Ergebnis eines Agent-Laufs: neue Commits (SHAs) und ob das Abschlusssignal kam. */
export type AgentRun = { commits: string[]; completed: boolean };

export interface Tracker {
  /** Offene Tickets mit `ready-for-agent`, ohne `Spec`, ohne offenen Blocker. */
  readyTickets(): Promise<Ticket[]>;
  /** Das Eltern-Issue, oder undefined, wenn es keines gibt. */
  parentOf(issue: number): Promise<IssueSummary | undefined>;
  issue(issue: number): Promise<IssueSummary>;
  close(issue: number, comment: string): Promise<void>;
}

export interface Repo {
  /** Ob `ref` vollständig in `branch` enthalten ist (`merge-base --is-ancestor`). */
  contains(branch: string, ref: string): Promise<boolean>;
}

/** Implementer und Review eines Tickets teilen sich eine Sandbox. */
export interface TicketSession {
  implement(): Promise<AgentRun>;
  review(): Promise<AgentRun>;
}

export interface Agents {
  /** Der Planner stellt Tickets mit überlappenden Dateien zurück. */
  plan(tickets: Ticket[]): Promise<PlannedIssue[]>;
  /** Öffnet eine Sandbox auf dem Ticket-Branch und gibt sie nach `work` wieder frei. */
  onTicketBranch<T>(
    issue: PlannedIssue,
    work: (session: TicketSession) => Promise<T>,
  ): Promise<T>;
  /** Der Merger mergt die Branches in den aktiven Branch des Hosts. */
  merge(branches: string[]): Promise<AgentRun>;
}

export type IterationDeps = {
  tracker: Tracker;
  repo: Repo;
  agents: Agents;
  /** Branch, in den gemergt wird und gegen den Ticket-Branches gemessen werden. */
  targetBranch: string;
  log?: (message: string) => void;
  /** Höchstzahl der Tickets, die gleichzeitig implementiert und reviewt werden. */
  maxParallel?: number;
};

/** `planned == 0` heißt: der Backlog ist leer, die äußere Schleife kann enden. */
export type IterationResult = { planned: number };

/**
 * Eine Iteration: planen, je Ticket implementieren und reviewen, mergen,
 * gemergte Tickets schließen und Specs schließen, deren Sub-Issues alle zu sind.
 */
export async function runIteration(deps: IterationDeps): Promise<IterationResult> {
  const { tracker, agents, targetBranch } = deps;
  const log = deps.log ?? console.log;

  const tickets = await tracker.readyTickets();
  const issues = await agents.plan(tickets);
  if (issues.length === 0) {
    log("No issues to work on.");
    return { planned: 0 };
  }

  log(`Planning complete. ${issues.length} issue(s) to work in parallel:`);
  for (const issue of issues) log(`  #${issue.id}: ${issue.title} -> ${issue.branch}`);

  const readyIssues = await implementAndReview(deps, issues, log);
  const branches = readyIssues.map((i) => i.branch);

  log(`\nExecution complete. ${branches.length} branch(es) to merge:`);
  for (const branch of branches) log(`  ${branch}`);
  if (branches.length === 0) {
    log("No completed branches. Nothing to merge.");
    return { planned: issues.length };
  }

  await agents.merge(branches);
  log("\nBranches merged.");

  await closeMergedIssues(deps, readyIssues, log);
  return { planned: issues.length };
}

// Implementiert und reviewt die Tickets mit einem Pool von maxParallel
// Workern und liefert die Tickets, deren Branch bereit zum Merge ist.
async function implementAndReview(
  deps: IterationDeps,
  issues: PlannedIssue[],
  log: (message: string) => void,
): Promise<PlannedIssue[]> {
  const { agents, repo, targetBranch } = deps;
  const queue = [...issues];
  const ready: PlannedIssue[] = [];

  const worker = async (): Promise<void> => {
    for (let issue = queue.shift(); issue; issue = queue.shift()) {
      const current = issue;
      try {
        const readyToMerge = await agents.onTicketBranch(current, async (session) => {
          const implement = await session.implement();
          const producedCommits = implement.commits.length > 0;
          // Ein Branch kann fertige Arbeit aus einer früheren Iteration tragen,
          // auch wenn der Implementer diesmal nichts committet hat.
          const hasUnmergedWork =
            producedCommits || !(await repo.contains(targetBranch, current.branch));

          // Ohne Abschlusssignal ist der Branch halbfertig: Er behält seine
          // Commits für eine spätere Iteration, wird aber weder reviewt noch gemergt.
          if (hasUnmergedWork && !implement.completed) {
            log(
              `  #${current.id}: no completion signal - ${current.branch} keeps its progress, skipping review and merge.`,
            );
          }
          if (!(implement.completed && hasUnmergedWork)) return false;

          if (!producedCommits) {
            log(
              `  #${current.id}: no new commits, but ${current.branch} is ahead of ${targetBranch} - reviewing anyway.`,
            );
          }
          await session.review();
          return true;
        });
        if (readyToMerge) ready.push(current);
      } catch (error) {
        // Ein kaputtes Ticket soll die übrigen in der Warteschlange nicht aufhalten.
        log(`  ! #${current.id} (${current.branch}) failed: ${error}`);
      }
    }
  };

  const workers = Math.min(deps.maxParallel ?? 4, queue.length);
  await Promise.all(Array.from({ length: workers }, worker));
  return ready;
}

// Schließt jedes Ticket, dessen Branch nachweislich im Ziel-Branch liegt, und
// danach jede berührte Spec, deren Sub-Issues alle geschlossen sind.
async function closeMergedIssues(
  deps: IterationDeps,
  issues: PlannedIssue[],
  log: (message: string) => void,
): Promise<void> {
  const { tracker, repo, targetBranch } = deps;
  const touchedSpecs = new Set<number>();

  for (const issue of issues) {
    if (!(await repo.contains(targetBranch, issue.branch))) {
      log(`  #${issue.id}: ${issue.branch} is not in ${targetBranch} - leaving the issue open.`);
      continue;
    }
    try {
      await tracker.close(Number(issue.id), "Completed by Sandcastle");
      log(`  #${issue.id}: closed.`);
    } catch (error) {
      log(`  ! Could not close #${issue.id}: ${error}`);
      continue;
    }
    try {
      const parent = await tracker.parentOf(Number(issue.id));
      if (parent && isOpenSpec(parent)) touchedSpecs.add(parent.number);
    } catch (error) {
      log(`  ! Could not fetch parent of #${issue.id}: ${error}`);
    }
  }

  // Jede Spec wird erst gelesen, wenn alle Tickets dieser Iteration zu sind.
  for (const specNumber of touchedSpecs) {
    try {
      const spec = await tracker.issue(specNumber);
      const { total, completed } = spec.subIssues;
      if (isOpenSpec(spec) && total > 0 && completed === total) {
        await tracker.close(specNumber, "All sub-issues completed by Sandcastle");
        log(`  Spec #${specNumber}: all sub-issues closed - closed.`);
      }
    } catch (error) {
      log(`  ! Could not check Spec #${specNumber}: ${error}`);
    }
  }
}

function isOpenSpec(issue: IssueSummary): boolean {
  return issue.open && issue.labels.includes("Spec");
}

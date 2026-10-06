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
  branchExists(branch: string): Promise<boolean>;
  /** Legt `branch` auf dem Stand von `base` an, ohne den Checkout des Hosts zu berühren. */
  createBranch(branch: string, base: string): Promise<void>;
}

/** Implementer und Review eines Tickets teilen sich eine Sandbox. */
export interface TicketSession {
  implement(): Promise<AgentRun>;
  review(): Promise<AgentRun>;
}

export interface Agents {
  /** Der Planner stellt Tickets mit überlappenden Dateien zurück. */
  plan(tickets: Ticket[]): Promise<PlannedIssue[]>;
  /**
   * Öffnet eine Sandbox auf dem Ticket-Branch und gibt sie nach `work` wieder
   * frei. Fehlt der Ticket-Branch, zweigt er von `integrationBranch` ab.
   */
  onTicketBranch<T>(
    issue: PlannedIssue,
    integrationBranch: string,
    work: (session: TicketSession) => Promise<T>,
  ): Promise<T>;
  /** Der Merger mergt die Branches in `into`. */
  merge(into: string, branches: string[]): Promise<AgentRun>;
}

/** Von hier zweigen neue Integrations-Branches ab. */
export const MAIN_BRANCH = "main";

export type IterationDeps = {
  tracker: Tracker;
  repo: Repo;
  agents: Agents;
  /** Ziel-Branch der Tickets ohne Eltern-Spec: der aktive Branch des Hosts. */
  targetBranch: string;
  log?: (message: string) => void;
  /** Höchstzahl der Tickets, die gleichzeitig implementiert und reviewt werden. */
  maxParallel?: number;
};

/** `planned == 0` heißt: der Backlog ist leer, die äußere Schleife kann enden. */
export type IterationResult = { planned: number };

/** Ein geplantes Ticket mit dem Branch, in den es gemergt wird. */
type Assignment = PlannedIssue & { integrationBranch: string };

/**
 * Eine Iteration: planen, je Ticket implementieren und reviewen, je
 * Integrations-Branch mergen und gemergte Tickets schließen.
 */
export async function runIteration(deps: IterationDeps): Promise<IterationResult> {
  const { tracker, agents } = deps;
  const log = deps.log ?? console.log;

  const tickets = await tracker.readyTickets();
  const issues = await agents.plan(tickets);
  if (issues.length === 0) {
    log("No issues to work on.");
    return { planned: 0 };
  }

  log(`Planning complete. ${issues.length} issue(s) to work in parallel:`);
  for (const issue of issues) log(`  #${issue.id}: ${issue.title} -> ${issue.branch}`);

  const assignments = await assignIntegrationBranches(deps, issues, log);
  const readyIssues = await implementAndReview(deps, assignments, log);

  log(`\nExecution complete. ${readyIssues.length} branch(es) to merge:`);
  for (const issue of readyIssues) log(`  ${issue.branch} -> ${issue.integrationBranch}`);
  if (readyIssues.length === 0) {
    log("No completed branches. Nothing to merge.");
    return { planned: issues.length };
  }

  const byIntegrationBranch = Map.groupBy(readyIssues, (i) => i.integrationBranch);
  for (const [into, group] of byIntegrationBranch) {
    // Ein Merger je Integrations-Branch: Scheitert einer, bleiben die anderen unberührt.
    try {
      await agents.merge(
        into,
        group.map((i) => i.branch),
      );
      log(`\nBranches merged into ${into}.`);
    } catch (error) {
      log(`  ! Merging into ${into} failed: ${error}`);
    }
    await closeMergedIssues(deps, group, log);
  }
  return { planned: issues.length };
}

// Ticket mit Eltern-Spec n -> spec/<n>, sonst der Ziel-Branch des Hosts.
// Fehlt ein Integrations-Branch, entsteht er von main. Ein Ticket, dessen
// Eltern-Issue sich nicht lesen lässt, wird ausgelassen statt falsch geleitet.
async function assignIntegrationBranches(
  deps: IterationDeps,
  issues: PlannedIssue[],
  log: (message: string) => void,
): Promise<Assignment[]> {
  const { tracker, repo, targetBranch } = deps;
  const assignments: Assignment[] = [];
  for (const issue of issues) {
    let integrationBranch: string;
    try {
      const parent = await tracker.parentOf(Number(issue.id));
      integrationBranch = parent && isSpec(parent) ? `spec/${parent.number}` : targetBranch;
      if (!(await repo.branchExists(integrationBranch))) {
        await repo.createBranch(integrationBranch, MAIN_BRANCH);
        log(`  ${integrationBranch}: created from ${MAIN_BRANCH}.`);
      }
    } catch (error) {
      log(`  ! #${issue.id}: no integration branch, skipping: ${error}`);
      continue;
    }
    assignments.push({ ...issue, integrationBranch });
  }
  return assignments;
}

// Implementiert und reviewt die Tickets mit einem Pool von maxParallel
// Workern und liefert die Tickets, deren Branch bereit zum Merge ist.
async function implementAndReview(
  deps: IterationDeps,
  issues: Assignment[],
  log: (message: string) => void,
): Promise<Assignment[]> {
  const { agents, repo } = deps;
  const queue = [...issues];
  const ready: Assignment[] = [];

  const worker = async (): Promise<void> => {
    for (let issue = queue.shift(); issue; issue = queue.shift()) {
      const current = issue;
      const into = current.integrationBranch;
      try {
        const readyToMerge = await agents.onTicketBranch(current, into, async (session) => {
          const implement = await session.implement();
          const producedCommits = implement.commits.length > 0;
          // Ein Branch kann fertige Arbeit aus einer früheren Iteration tragen,
          // auch wenn der Implementer diesmal nichts committet hat.
          const hasUnmergedWork =
            producedCommits || !(await repo.contains(into, current.branch));

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
              `  #${current.id}: no new commits, but ${current.branch} is ahead of ${into} - reviewing anyway.`,
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

// Schließt jedes Ticket, dessen Branch nachweislich in seinem
// Integrations-Branch liegt. Die Spec bleibt offen; sie schließt ihr PR.
async function closeMergedIssues(
  deps: IterationDeps,
  issues: Assignment[],
  log: (message: string) => void,
): Promise<void> {
  const { tracker, repo } = deps;
  for (const issue of issues) {
    const into = issue.integrationBranch;
    if (!(await repo.contains(into, issue.branch))) {
      log(`  #${issue.id}: ${issue.branch} is not in ${into} - leaving the issue open.`);
      continue;
    }
    try {
      await tracker.close(Number(issue.id), `Completed by Sandcastle, merged into ${into}`);
      log(`  #${issue.id}: closed.`);
    } catch (error) {
      log(`  ! Could not close #${issue.id}: ${error}`);
    }
  }
}

function isSpec(issue: IssueSummary): boolean {
  return issue.labels.includes("Spec");
}

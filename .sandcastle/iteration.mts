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
  /** Die Issues, die dieses Ticket blockieren (Blocked-by-Kanten). */
  blockedBy: number[];
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
  /** Die lokalen Branches, deren Name mit `prefix` beginnt. */
  branches(prefix: string): Promise<string[]>;
  /**
   * Mergt main in `branch`, ohne den Checkout des Hosts zu berühren. Bei
   * einem Konflikt bleibt `branch` unverändert.
   */
  mergeMain(branch: string): Promise<"clean" | "conflict">;
  /** Der Commit, auf dem `branch` steht. */
  head(branch: string): Promise<string>;
  /** Setzt `branch` auf `head` zurück, ohne den Checkout des Hosts zu berühren. */
  resetBranch(branch: string, head: string): Promise<void>;
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

/** Der fortlaufende Integrations-Branch der Tickets ohne Eltern-Spec. */
export const STANDALONE_BRANCH = "sandcastle/standalone";

export type IterationDeps = {
  tracker: Tracker;
  repo: Repo;
  agents: Agents;
  /** Ziel-Branch der Tickets ohne Eltern-Spec: der aktive Branch des Hosts. */
  targetBranch: string;
  log?: (message: string) => void;
  /** Höchstzahl der Tickets, die gleichzeitig implementiert und reviewt werden. */
  maxParallel?: number;
  /** Beschränkt den Lauf auf die Sub-Issues dieser Spec (`--spec <n>`). */
  spec?: number;
};

export type UpdateDeps = Pick<IterationDeps, "tracker" | "repo" | "agents" | "log">;

/**
 * Laufbeginn: mergt main in jeden aktiven Integrations-Branch, damit Tickets
 * von einem aktuellen Stand abzweigen. Nur bei einem Konflikt startet der
 * Merger. Scheitert er, bleibt der Branch unverändert und steht in `failed`.
 */
export async function updateIntegrationBranches(deps: UpdateDeps): Promise<UpdateResult> {
  const log = deps.log ?? console.log;
  const failed: string[] = [];
  for (const branch of await activeIntegrationBranches(deps, log)) {
    let updated = false;
    try {
      updated = await mergeMainInto(deps, branch, log);
    } catch (error) {
      log(`  ! ${branch}: ${error}`);
    }
    if (!updated) {
      failed.push(branch);
      log(`  ! ${branch}: could not merge ${MAIN_BRANCH}, branch left unchanged.`);
    }
  }
  return { failed };
}

// Mergt main in `branch`, bei Konflikt über den Merger. Liefert, ob main
// danach enthalten ist; sonst steht `branch` wieder auf seinem alten Stand.
async function mergeMainInto(
  deps: UpdateDeps,
  branch: string,
  log: (message: string) => void,
): Promise<boolean> {
  const { repo, agents } = deps;
  if ((await repo.mergeMain(branch)) === "clean") return true;

  log(`  ${branch}: conflict with ${MAIN_BRANCH}, starting the merger.`);
  const before = await repo.head(branch);
  let resolved = false;
  try {
    const run = await agents.merge(branch, [MAIN_BRANCH]);
    resolved = run.completed && (await repo.contains(branch, MAIN_BRANCH));
  } catch (error) {
    log(`  ! Merger on ${branch} failed: ${error}`);
  }
  // Eine halbe Auflösung soll kein Ticket als Ausgangsstand erben.
  if (!resolved) await repo.resetBranch(branch, before);
  return resolved;
}

/** Die Integrations-Branches, in die main zu Laufbeginn nicht gemergt werden konnte. */
export type UpdateResult = { failed: string[] };

// Aktiv ist jeder bestehende `spec/<n>`, dessen Spec noch offen ist, und
// `sandcastle/standalone`, falls es ihn gibt. Den Branch einer geschlossenen
// Spec hat ihr PR schon nach main gebracht.
async function activeIntegrationBranches(
  deps: UpdateDeps,
  log: (message: string) => void,
): Promise<string[]> {
  const { tracker, repo } = deps;
  const active: string[] = [];
  if (await repo.branchExists(STANDALONE_BRANCH)) active.push(STANDALONE_BRANCH);
  for (const branch of await repo.branches("spec/")) {
    const spec = Number(branch.slice("spec/".length));
    if (!Number.isInteger(spec)) continue;
    try {
      if ((await tracker.issue(spec)).open) active.push(branch);
    } catch (error) {
      log(`  ! ${branch}: could not read spec #${spec}, skipping: ${error}`);
    }
  }
  return active;
}

/** `planned == 0` heißt: der Backlog ist leer, die äußere Schleife kann enden. */
export type IterationResult = { planned: number };

/** Ein geplantes Ticket mit dem Branch, in den es gemergt wird. */
type Assignment = PlannedIssue & { integrationBranch: string };

/**
 * Eine Iteration: planen, je Ticket implementieren und reviewen, je
 * Integrations-Branch mergen und gemergte Tickets schließen.
 */
export async function runIteration(deps: IterationDeps): Promise<IterationResult> {
  const { agents } = deps;
  const log = deps.log ?? console.log;

  const issues = await agents.plan(await frontier(deps, log));
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

// Die Tickets, die der Planner zu sehen bekommt: die bereiten Tickets des
// Trackers, mit `--spec` nur die Sub-Issues dieser Spec. Offene Blocker hat
// der Tracker schon ausgefiltert; ein geschlossener Blocker aus einem anderen
// Integrations-Branch zählt erst, wenn er auf main liegt. Ein Ticket, dessen
// Eltern-Issues sich nicht lesen lassen, fällt heraus.
async function frontier(deps: IterationDeps, log: (message: string) => void): Promise<Ticket[]> {
  const { tracker } = deps;
  const tickets: Ticket[] = [];
  for (const ticket of await tracker.readyTickets()) {
    try {
      const spec = specOf(await tracker.parentOf(ticket.number));
      if (deps.spec !== undefined && spec !== deps.spec) continue;
      const pending = await blockersNotOnMain(deps, ticket, spec);
      if (pending.length > 0) {
        log(`  #${ticket.number}: waiting for ${pending.map((b) => `#${b}`).join(", ")} on ${MAIN_BRANCH}.`);
        continue;
      }
    } catch (error) {
      log(`  ! #${ticket.number}: parent unreadable, skipping: ${error}`);
      continue;
    }
    tickets.push(ticket);
  }
  return tickets;
}

// Die Blocker des Tickets aus einer anderen Spec (oder von außerhalb jeder
// Spec), deren Ticket-Branch noch nicht in main liegt. Eine geschlossene Spec
// hat ihr PR nach main gebracht; ihre Tickets zählen auch ohne Ticket-Branch.
async function blockersNotOnMain(
  deps: IterationDeps,
  ticket: Ticket,
  spec: number | undefined,
): Promise<number[]> {
  const { tracker, repo } = deps;
  const pending: number[] = [];
  for (const blocker of ticket.blockedBy) {
    const parent = await tracker.parentOf(blocker);
    if (specOf(parent) === spec) continue;
    if (parent && isSpec(parent) && !parent.open) continue;
    if (!(await repo.contains(MAIN_BRANCH, ticketBranch(blocker)))) pending.push(blocker);
  }
  return pending;
}

// Der Planner vergibt diesen Namen deterministisch (siehe plan-prompt.md).
function ticketBranch(issue: number): string {
  return `sandcastle/issue-${issue}`;
}

function specOf(parent: IssueSummary | undefined): number | undefined {
  return parent && isSpec(parent) ? parent.number : undefined;
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

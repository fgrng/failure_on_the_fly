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

/** Ein Pull Request; `head` ist der Branch, der gemergt werden soll. */
export type PullRequest = {
  number: number;
  head: string;
  base: string;
  title: string;
  body: string;
  state: "open" | "merged" | "closed";
};

export interface Tracker {
  /** Offene Tickets mit `ready-for-agent`, ohne `Spec`, ohne offenen Blocker. */
  readyTickets(): Promise<Ticket[]>;
  /** Das Eltern-Issue, oder undefined, wenn es keines gibt. */
  parentOf(issue: number): Promise<IssueSummary | undefined>;
  issue(issue: number): Promise<IssueSummary>;
  close(issue: number, comment: string): Promise<void>;
  comment(issue: number, comment: string): Promise<void>;
  /** Ersetzt das Label `remove` durch `add`. */
  swapLabel(issue: number, remove: string, add: string): Promise<void>;
  /** Der offene PR von `head`, sonst der zuletzt angelegte, sonst undefined. */
  pullRequest(head: string): Promise<PullRequest | undefined>;
  createPullRequest(pr: { head: string; base: string; title: string; body: string }): Promise<void>;
  updatePullRequest(number: number, text: { title: string; body: string }): Promise<void>;
}

export interface Repo {
  /** Holt den Stand von origin, ohne den Checkout des Hosts zu berühren. */
  fetch(): Promise<void>;
  /** Der Branch, den der Checkout des Hosts gerade ausgecheckt hat. */
  hostBranch(): Promise<string>;
  /** Ob `ref` vollständig in `branch` enthalten ist (`merge-base --is-ancestor`). */
  contains(branch: string, ref: string): Promise<boolean>;
  /** Ob eine Commit-Nachricht in `ref` auf das Issue verweist, etwa `(#12` oder `(#12,`. */
  mentionsIssue(ref: string, issue: number): Promise<boolean>;
  /** Ob es den lokalen Branch gibt. */
  branchExists(branch: string): Promise<boolean>;
  /** Legt `branch` auf dem Stand von `base` an, ohne den Checkout des Hosts zu berühren. */
  createBranch(branch: string, base: string): Promise<void>;
  /** Die lokalen Branches, deren Name mit `prefix` beginnt. */
  branches(prefix: string): Promise<string[]>;
  /**
   * Mergt MAIN_REF in `branch`, ohne den Checkout des Hosts zu berühren. Bei
   * einem Konflikt bleibt `branch` unverändert.
   */
  mergeMain(branch: string): Promise<"clean" | "conflict">;
  /** Der Commit, auf dem `branch` steht. */
  head(branch: string): Promise<string>;
  /** Setzt `branch` auf `head` zurück, ohne den Checkout des Hosts zu berühren. */
  resetBranch(branch: string, head: string): Promise<void>;
  /** Ob `branch` genau auf seinem Stand in origin steht. */
  isPushed(branch: string): Promise<boolean>;
  /** Pusht `branch` nach origin; eine neu begonnene Historie ersetzt die alte. */
  push(branch: string): Promise<void>;
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
  /** Reviewt `branch` gegen main mit `code-review`, Maßstab ist die Spec. */
  reviewSpec(spec: number, branch: string): Promise<SpecReview>;
  /** Ein Implementer behebt die Befunde auf `branch`. */
  fixFindings(spec: number, branch: string, findings: string[]): Promise<AgentRun>;
  /** Titel und Text des PRs von `branch`, geschrieben mit dem Skill `pr`. */
  writePullRequest(spec: number, branch: string): Promise<PullRequestText>;
}

/**
 * Befunde des Spec-Reviews: Standards und Korrektheit werden behoben,
 * Spec-Befunde gehen als offene Punkte in den PR-Text.
 */
export type SpecReview = { standards: string[]; correctness: string[]; spec: string[] };

export type PullRequestText = { title: string; body: string };

/** Ziel jedes PRs. */
export const MAIN_BRANCH = "main";

/**
 * Der Stand von main auf GitHub, wie ihn der Fetch zu Laufbeginn geholt hat.
 * Gegen ihn misst der Lauf, und von ihm zweigen neue Integrations-Branches
 * ab; das lokale main des Hosts bleibt dabei außen vor.
 */
export const MAIN_REF = `origin/${MAIN_BRANCH}`;

/** Der fortlaufende Integrations-Branch der Tickets ohne Eltern-Spec. */
export const STANDALONE_BRANCH = "sandcastle/standalone";

export type IterationDeps = {
  tracker: Tracker;
  repo: Repo;
  agents: Agents;
  log?: (message: string) => void;
  /** Höchstzahl der Tickets, die gleichzeitig implementiert und reviewt werden. */
  maxParallel?: number;
  /** Beschränkt den Lauf auf die Sub-Issues dieser Spec (`--spec <n>`). */
  spec?: number;
};

export type UpdateDeps = Pick<IterationDeps, "tracker" | "repo" | "agents" | "log">;

/**
 * Laufbeginn: holt den Stand von origin und mergt MAIN_REF in jeden aktiven
 * Integrations-Branch, damit Tickets von einem aktuellen Stand abzweigen. Nur
 * bei einem Konflikt startet der Merger. Scheitert er, bleibt der Branch
 * unverändert und steht in `failed`. Ohne Fetch bricht der Lauf ab.
 */
export async function updateIntegrationBranches(deps: UpdateDeps): Promise<UpdateResult> {
  const log = deps.log ?? console.log;
  const failed: string[] = [];
  // Nur hier, nicht je Iteration: Was der Lauf gegen MAIN_REF misst, soll zu
  // dem Stand passen, der in den Integrations-Branches steckt.
  await deps.repo.fetch();
  const host = await deps.repo.hostBranch();
  // Vor dem Merge von main, sonst wäre der Branch nicht mehr auf seinem
  // gepushten Stand und bliebe stehen.
  try {
    if (host === STANDALONE_BRANCH) log(checkedOutByHost(STANDALONE_BRANCH));
    else await restartStandaloneAfterMerge(deps, log);
  } catch (error) {
    log(`  ! ${STANDALONE_BRANCH}: restart failed: ${error}`);
  }
  for (const branch of await activeIntegrationBranches(deps, log)) {
    if (branch === host) {
      log(checkedOutByHost(branch));
      continue;
    }
    let updated = false;
    try {
      updated = await mergeMainInto(deps, branch, log);
    } catch (error) {
      log(`  ! ${branch}: ${error}`);
    }
    if (!updated) {
      failed.push(branch);
      log(`  ! ${branch}: could not merge ${MAIN_REF}, branch left unchanged.`);
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

  log(`  ${branch}: conflict with ${MAIN_REF}, starting the merger.`);
  return mergeOrReset(deps, branch, [MAIN_REF], log, () => repo.contains(branch, MAIN_REF));
}

// Lässt den Merger `branches` in `into` mergen. Liefert, ob er mit
// Abschlusssignal endete und `verified` zutrifft; sonst steht `into` wieder
// auf dem Stand davor, damit kein Ticket eine halbe Auflösung erbt.
async function mergeOrReset(
  deps: UpdateDeps,
  into: string,
  branches: string[],
  log: (message: string) => void,
  verified: () => Promise<boolean> = async () => true,
): Promise<boolean> {
  const { repo, agents } = deps;
  const before = await repo.head(into);
  let merged = false;
  try {
    merged = (await agents.merge(into, branches)).completed && (await verified());
  } catch (error) {
    log(`  ! Merger on ${into} failed: ${error}`);
  }
  if (!merged) await repo.resetBranch(into, before);
  return merged;
}

/** Die Integrations-Branches, in die main zu Laufbeginn nicht gemergt werden konnte. */
export type UpdateResult = { failed: string[] };

// Den Branch, den der Host ausgecheckt hat, fasst der Lauf nicht an: kein
// Update, keine Tickets, keine Abschlussphase. Ein Worktree dafür ginge
// nicht, und ein Agent im Checkout des Hosts störte dessen Arbeit.
function checkedOutByHost(branch: string): string {
  return `  ! ${branch} is checked out in the host checkout - skipped.`;
}

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
 * Integrations-Branch mergen und gemergte Tickets schließen. Am Ende werden
 * sandcastle/standalone veröffentlicht und fertige Specs abgeschlossen.
 */
export async function runIteration(deps: IterationDeps): Promise<IterationResult> {
  const log = deps.log ?? console.log;
  const { planned, landed } = await planImplementAndMerge(deps, log);
  await publishStandalone(deps, landed, log);
  await finishCompletedSpecs(deps, log);
  return { planned };
}

// Liefert die Zahl der geplanten Tickets und die Tickets, die in ihrem
// Integrations-Branch gelandet sind.
async function planImplementAndMerge(
  deps: IterationDeps,
  log: (message: string) => void,
): Promise<{ planned: number; landed: Assignment[] }> {
  const { agents } = deps;
  const issues = await agents.plan(await frontier(deps, log));
  if (issues.length === 0) {
    log("No issues to work on.");
    return { planned: 0, landed: [] };
  }

  log(`Planning complete. ${issues.length} issue(s) to work in parallel:`);
  for (const issue of issues) log(`  #${issue.id}: ${issue.title} -> ${issue.branch}`);

  const assignments = await assignIntegrationBranches(deps, issues, log);
  const readyIssues = await implementAndReview(deps, assignments, log);

  log(`\nExecution complete. ${readyIssues.length} branch(es) to merge:`);
  for (const issue of readyIssues) log(`  ${issue.branch} -> ${issue.integrationBranch}`);
  if (readyIssues.length === 0) {
    log("No completed branches. Nothing to merge.");
    return { planned: issues.length, landed: [] };
  }

  const landed: Assignment[] = [];
  const byIntegrationBranch = Map.groupBy(readyIssues, (i) => i.integrationBranch);
  for (const [into, group] of byIntegrationBranch) {
    // Ein Merger je Integrations-Branch: Scheitert einer, bleiben die anderen unberührt.
    const branches = group.map((i) => i.branch);
    if (!(await mergeOrReset(deps, into, branches, log))) {
      log(`  ! ${into}: merger did not finish, branch reset - no ticket closed.`);
      continue;
    }
    log(`\nBranches merged into ${into}.`);
    landed.push(...(await closeMergedIssues(deps, group, log)));
  }
  return { planned: issues.length, landed };
}

// Die Tickets, die der Planner zu sehen bekommt: die bereiten Tickets des
// Trackers, mit `--spec` nur die Sub-Issues dieser Spec. Offene Blocker hat
// der Tracker schon ausgefiltert; ein geschlossener Blocker aus einem anderen
// Integrations-Branch zählt erst, wenn er auf main liegt. Hat die Spec schon
// einen offenen PR, geht das Ticket an einen Menschen. Ein Ticket, dessen
// Eltern-Issues sich nicht lesen lassen oder dessen Integrations-Branch der
// Host ausgecheckt hat, fällt heraus.
async function frontier(deps: IterationDeps, log: (message: string) => void): Promise<Ticket[]> {
  const { tracker, repo } = deps;
  const host = await repo.hostBranch();
  const tickets: Ticket[] = [];
  for (const ticket of await tracker.readyTickets()) {
    try {
      const spec = specOf(await tracker.parentOf(ticket.number));
      if (deps.spec !== undefined && spec !== deps.spec) continue;
      if (integrationBranchOf(spec) === host) {
        log(`  #${ticket.number}: ${checkedOutByHost(host).trim()}`);
        continue;
      }
      if (spec !== undefined && (await hasOpenPullRequest(tracker, spec))) {
        await handOverLateTicket(tracker, ticket.number, spec);
        log(`  #${ticket.number}: spec #${spec} already has an open PR, handed over to a human.`);
        continue;
      }
      const pending = await blockersNotOnMain(deps, ticket, spec);
      if (pending.length > 0) {
        log(`  #${ticket.number}: waiting for ${pending.map((b) => `#${b}`).join(", ")} on ${MAIN_REF}.`);
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

async function hasOpenPullRequest(tracker: Tracker, spec: number): Promise<boolean> {
  return (await tracker.pullRequest(`spec/${spec}`))?.state === "open";
}

// Ein Nachzügler würde still den PR im Review vergrößern. Der Label-Wechsel
// nimmt ihn aus der Frontier, damit der Kommentar nur einmal entsteht.
async function handOverLateTicket(tracker: Tracker, issue: number, spec: number): Promise<void> {
  await tracker.comment(
    issue,
    `Sandcastle plant dieses Ticket nicht ein: Spec #${spec} hat schon einen offenen PR. ` +
      "Nachzügler gehören in eine neue Spec. Das Label steht deshalb jetzt auf `ready-for-human`.",
  );
  await tracker.swapLabel(issue, "ready-for-agent", "ready-for-human");
}

// Die Blocker des Tickets aus einer anderen Spec (oder von außerhalb jeder
// Spec), die noch nicht auf main liegen. Auf main liegt ein Blocker, wenn sein
// Ticket-Branch dort enthalten ist oder ein Commit auf ihn verweist (`(#<n>`).
// Eine geschlossene Spec hat ihr PR nach main gebracht; ihre Tickets zählen
// auch ohne beides.
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
    if (await repo.contains(MAIN_REF, ticketBranch(blocker))) continue;
    if (await repo.mentionsIssue(MAIN_REF, blocker)) continue;
    pending.push(blocker);
  }
  return pending;
}

// Der Planner vergibt diesen Namen deterministisch (siehe plan-prompt.md).
function ticketBranch(issue: number): string {
  return `sandcastle/issue-${issue}`;
}

// Die Nummer der Eltern-Spec, oder undefined, wenn das Eltern-Issue fehlt
// oder keine Spec ist.
function specOf(parent: IssueSummary | undefined): number | undefined {
  return parent && isSpec(parent) ? parent.number : undefined;
}

const SPEC_PREFIX = "spec/";

// Der Integrations-Branch einer Spec.
function specBranch(spec: number): string {
  return `${SPEC_PREFIX}${spec}`;
}

// Die Spec-Nummer eines Branches `spec/<n>`, sonst undefined.
function specOfBranch(branch: string): number | undefined {
  if (!branch.startsWith(SPEC_PREFIX)) return undefined;
  const spec = Number(branch.slice(SPEC_PREFIX.length));
  return Number.isInteger(spec) ? spec : undefined;
}

// Ticket mit Eltern-Spec n -> spec/<n>, sonst sandcastle/standalone.
function integrationBranchOf(spec: number | undefined): string {
  return spec === undefined ? STANDALONE_BRANCH : specBranch(spec);
}

// Leitet jedes Ticket in seinen Integrations-Branch. Fehlt der Branch,
// entsteht er von main. Ein Ticket, dessen Eltern-Issue sich nicht lesen
// lässt, wird ausgelassen statt falsch geleitet.
async function assignIntegrationBranches(
  deps: IterationDeps,
  issues: PlannedIssue[],
  log: (message: string) => void,
): Promise<Assignment[]> {
  const { tracker, repo } = deps;
  const assignments: Assignment[] = [];
  for (const issue of issues) {
    let integrationBranch: string;
    try {
      integrationBranch = integrationBranchOf(specOf(await tracker.parentOf(Number(issue.id))));
      if (!(await repo.branchExists(integrationBranch))) {
        await repo.createBranch(integrationBranch, MAIN_REF);
        log(`  ${integrationBranch}: created from ${MAIN_REF}.`);
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
// Integrations-Branch liegt, und liefert diese Tickets. Die Spec bleibt
// offen; sie schließt ihr PR.
async function closeMergedIssues(
  deps: IterationDeps,
  issues: Assignment[],
  log: (message: string) => void,
): Promise<Assignment[]> {
  const { tracker, repo } = deps;
  const landed: Assignment[] = [];
  for (const issue of issues) {
    const into = issue.integrationBranch;
    if (!(await repo.contains(into, issue.branch))) {
      log(`  #${issue.id}: ${issue.branch} is not in ${into} - leaving the issue open.`);
      continue;
    }
    landed.push(issue);
    try {
      await tracker.close(Number(issue.id), `Completed by Sandcastle, merged into ${into}`);
      log(`  #${issue.id}: closed.`);
    } catch (error) {
      log(`  ! Could not close #${issue.id}: ${error}`);
    }
  }
  return landed;
}

// Ist der letzte PR von sandcastle/standalone gemergt, beginnt der Branch
// neu von main, damit der nächste PR nur neue Tickets enthält. Commits, die
// noch nicht gepusht sind, gehören nicht zu diesem PR; dann bleibt er stehen.
async function restartStandaloneAfterMerge(
  deps: UpdateDeps,
  log: (message: string) => void,
): Promise<void> {
  const { tracker, repo } = deps;
  if (!(await repo.branchExists(STANDALONE_BRANCH))) return;
  if ((await tracker.pullRequest(STANDALONE_BRANCH))?.state !== "merged") return;
  if (!(await repo.isPushed(STANDALONE_BRANCH))) {
    log(`  ! ${STANDALONE_BRANCH} has unpushed commits - not restarting from ${MAIN_REF}.`);
    return;
  }
  await repo.resetBranch(STANDALONE_BRANCH, await repo.head(MAIN_REF));
  log(`${STANDALONE_BRANCH}: pull request merged, restarted from ${MAIN_REF}.`);
}

// Hat sandcastle/standalone Commits, die nicht auf main liegen, wird der
// Branch gepusht. Sein PR wird angelegt oder, wenn er offen ist, um die
// gelandeten Tickets ergänzt.
async function publishStandalone(
  deps: IterationDeps,
  landed: Assignment[],
  log: (message: string) => void,
): Promise<void> {
  const { tracker, repo } = deps;
  if (!(await repo.branchExists(STANDALONE_BRANCH))) return;
  if (await repo.contains(MAIN_REF, STANDALONE_BRANCH)) return;
  try {
    await repo.push(STANDALONE_BRANCH);
    const tickets = landed
      .filter((i) => i.integrationBranch === STANDALONE_BRANCH)
      .map((i) => `- #${i.id}: ${i.title}`);
    const pr = await tracker.pullRequest(STANDALONE_BRANCH);
    if (pr?.state === "open") {
      const listed = pr.body.split("\n").filter((line) => line.startsWith("- #"));
      const body = standalonePrBody([...new Set([...listed, ...tickets])]);
      await tracker.updatePullRequest(pr.number, { title: pr.title, body });
      log(`\n${STANDALONE_BRANCH}: pushed, pull request #${pr.number} updated.`);
    } else {
      await tracker.createPullRequest({
        head: STANDALONE_BRANCH,
        base: MAIN_BRANCH,
        title: "Sandcastle: Tickets ohne Spec",
        body: standalonePrBody(tickets),
      });
      log(`\n${STANDALONE_BRANCH}: pushed, pull request opened.`);
    }
  } catch (error) {
    log(`  ! Publishing ${STANDALONE_BRANCH} failed: ${error}`);
  }
}

// Abschlussphase für jede Spec, deren Sub-Issues alle geschlossen sind und
// die noch keinen offenen PR hat. Scheitert eine, kommen die anderen trotzdem dran.
async function finishCompletedSpecs(
  deps: IterationDeps,
  log: (message: string) => void,
): Promise<void> {
  for (const spec of await completedSpecs(deps, log)) {
    try {
      await finishSpec(deps, spec, log);
    } catch (error) {
      log(`  ! Finishing spec #${spec} failed: ${error}`);
    }
  }
}

// Die Specs, deren Integrations-Branch bereit für den PR ist: Spec offen,
// alle Sub-Issues geschlossen, kein offener PR, Commits, die main noch fehlen,
// und nicht im Checkout des Hosts ausgecheckt.
async function completedSpecs(
  deps: IterationDeps,
  log: (message: string) => void,
): Promise<number[]> {
  const { tracker, repo } = deps;
  const host = await repo.hostBranch();
  const specs: number[] = [];
  for (const branch of await repo.branches(SPEC_PREFIX)) {
    const spec = specOfBranch(branch);
    if (spec === undefined) continue;
    if (deps.spec !== undefined && spec !== deps.spec) continue;
    if (branch === host) {
      log(checkedOutByHost(branch));
      continue;
    }
    try {
      const { open, subIssues } = await tracker.issue(spec);
      if (!open || subIssues.total === 0 || subIssues.completed !== subIssues.total) continue;
      if (await hasOpenPullRequest(tracker, spec)) continue;
      if (await repo.contains(MAIN_REF, branch)) continue;
    } catch (error) {
      log(`  ! ${branch}: could not check spec #${spec}, skipping: ${error}`);
      continue;
    }
    specs.push(spec);
  }
  return specs;
}

// Spec-Review, Behebung der Standards- und Korrektheitsbefunde, PR-Text,
// dann Push und PR. Endet die Behebung ohne Abschlusssignal, bleibt der PR
// aus; die nächste Iteration beginnt die Abschlussphase von vorn.
async function finishSpec(
  deps: IterationDeps,
  spec: number,
  log: (message: string) => void,
): Promise<void> {
  const { tracker, repo, agents } = deps;
  const branch = `spec/${spec}`;
  log(`\n=== Finishing spec #${spec} on ${branch} ===`);

  const review = await agents.reviewSpec(spec, branch);
  const toFix = [...review.standards, ...review.correctness];
  if (toFix.length > 0) {
    const fix = await agents.fixFindings(spec, branch, toFix);
    if (!fix.completed) {
      log(`  ! ${branch}: findings not fixed (no completion signal) - no pull request yet.`);
      return;
    }
  }

  const text = await agents.writePullRequest(spec, branch);
  await repo.push(branch);
  await tracker.createPullRequest({
    head: branch,
    base: MAIN_BRANCH,
    title: text.title,
    body: specPrBody(text.body, review.spec, spec),
  });
  log(`${branch}: pushed, pull request opened.`);
}

// Spec-Befunde entscheidet ein Mensch; sie stehen deshalb wörtlich im PR.
// `Closes` am Ende schließt die Spec beim Merge des PRs.
function specPrBody(body: string, openPoints: string[], spec: number): string {
  const parts = [body.trim()];
  if (openPoints.length > 0) {
    parts.push(["## Offene Punkte", "", ...openPoints.map((p) => `- ${p}`)].join("\n"));
  }
  parts.push(`Closes #${spec}`);
  return parts.join("\n\n");
}

function standalonePrBody(ticketLines: string[]): string {
  return [
    "Von Sandcastle umgesetzte Tickets ohne Eltern-Spec, je Ticket reviewt:",
    "",
    ...ticketLines,
  ].join("\n");
}

function isSpec(issue: IssueSummary): boolean {
  return issue.labels.includes("Spec");
}

// Fakes für die Systemgrenzen der Ablauf-Funktion: Tracker (gh), Repo (git)
// und Agents (Sandcastle). Sie halten ihren Zustand im Speicher und
// protokollieren, was der Ablauf mit ihnen getan hat.

import type {
  AgentRun,
  Agents,
  IssueSummary,
  PlannedIssue,
  Repo,
  Ticket,
  TicketSession,
  Tracker,
} from "../iteration.mts";

export function ticket(number: number, title = `Ticket ${number}`): Ticket {
  return { number, title, body: "", labels: ["ready-for-agent"], comments: [], blockedBy: [] };
}

type TrackedIssue = {
  number: number;
  open: boolean;
  labels: string[];
  parent?: number;
  blockedBy?: number[];
  ticket?: Ticket;
};

export class FakeTracker implements Tracker {
  private issues = new Map<number, TrackedIssue>();
  /** Jedes Schließen mit seinem Kommentar, in Aufrufreihenfolge. */
  readonly closed: { number: number; comment: string }[] = [];

  addTicket(t: Ticket, options: { parent?: number; blockedBy?: number[] } = {}): void {
    this.issues.set(t.number, {
      number: t.number,
      open: true,
      labels: t.labels,
      parent: options.parent,
      blockedBy: options.blockedBy ?? [],
      ticket: { ...t, blockedBy: options.blockedBy ?? [] },
    });
  }

  addSpec(number: number, options: { open?: boolean } = {}): void {
    this.issues.set(number, { number, open: options.open ?? true, labels: ["Spec"] });
  }

  isOpen(number: number): boolean {
    return this.get(number).open;
  }

  /** Wie `-is:blocked`: Tickets mit offenem Blocker fehlen. */
  async readyTickets(): Promise<Ticket[]> {
    return [...this.issues.values()].flatMap((i) =>
      i.open && i.ticket && i.blockedBy?.every((b) => !this.isOpen(b)) ? [i.ticket] : [],
    );
  }

  async parentOf(number: number): Promise<IssueSummary | undefined> {
    const parent = this.get(number).parent;
    return parent === undefined ? undefined : this.issue(parent);
  }

  async issue(number: number): Promise<IssueSummary> {
    const issue = this.get(number);
    const subIssues = [...this.issues.values()].filter((i) => i.parent === number);
    return {
      number,
      open: issue.open,
      labels: issue.labels,
      subIssues: {
        total: subIssues.length,
        completed: subIssues.filter((i) => !i.open).length,
      },
    };
  }

  async close(number: number, comment: string): Promise<void> {
    this.get(number).open = false;
    this.closed.push({ number, comment });
  }

  private get(number: number): TrackedIssue {
    const issue = this.issues.get(number);
    if (!issue) throw new Error(`FakeTracker: Issue #${number} unbekannt`);
    return issue;
  }
}

// Ein Branch ist die Menge der Commits, die er enthält.
export class FakeRepo implements Repo {
  private refs = new Map<string, Set<string>>();
  private nextSha = 1;
  /** Branches, deren Merge mit main einen Konflikt ergibt. */
  readonly conflicting = new Set<string>();

  constructor(...branches: string[]) {
    for (const branch of branches) this.refs.set(branch, new Set());
  }

  async branchExists(branch: string): Promise<boolean> {
    return this.refs.has(branch);
  }

  async createBranch(branch: string, base: string): Promise<void> {
    if (!this.refs.has(branch)) this.refs.set(branch, new Set(this.commits(base)));
  }

  async branches(prefix: string): Promise<string[]> {
    return [...this.refs.keys()].filter((b) => b.startsWith(prefix));
  }

  async mergeMain(branch: string): Promise<"clean" | "conflict"> {
    if (this.conflicting.has(branch)) return "conflict";
    this.merge("main", branch);
    return "clean";
  }

  commit(branch: string): string {
    const sha = `c${this.nextSha++}`;
    this.commits(branch).add(sha);
    return sha;
  }

  merge(source: string, into: string): void {
    for (const sha of this.commits(source)) this.commits(into).add(sha);
  }

  // Der Stand eines Branches: seine Commits, sortiert und verkettet.
  async head(branch: string): Promise<string> {
    return [...this.commits(branch)].sort().join(",");
  }

  async resetBranch(branch: string, head: string): Promise<void> {
    this.refs.set(branch, new Set(head ? head.split(",") : []));
  }

  async contains(branch: string, ref: string): Promise<boolean> {
    const target = this.commits(branch);
    return [...this.commits(ref)].every((sha) => target.has(sha));
  }

  private commits(branch: string): Set<string> {
    const commits = this.refs.get(branch);
    if (!commits) throw new Error(`FakeRepo: Branch ${branch} unbekannt`);
    return commits;
  }
}

/** Was der Implementer für ein Ticket tut: neue Commits und Abschlusssignal. */
export type ImplementerScript = { commits: number; completed: boolean };

export class FakeAgents implements Agents {
  /** Die Ticketliste jedes Planner-Aufrufs. */
  readonly plannedWith: Ticket[][] = [];
  /** Ticket-IDs, für die der Implementer lief. */
  readonly implemented: string[] = [];
  /** Ticket-IDs, für die das Review lief. */
  readonly reviewed: string[] = [];
  /** Ziel und Branch-Liste jedes Merger-Aufrufs. */
  readonly mergedWith: { into: string; branches: string[] }[] = [];
  /** Integrations-Branch, von dem jede geöffnete Ticket-Sandbox ausging. */
  readonly startedFrom: { id: string; base: string }[] = [];

  /** Implementer-Verhalten je Ticket-ID. Default: ein Commit mit Abschlusssignal. */
  readonly implementers = new Map<string, ImplementerScript>();
  /** Branches, deren Merge der Merger nicht schafft. */
  readonly unmergeable = new Set<string>();
  /** Ticket-IDs, die der Planner wegen Überschneidungen zurückstellt. */
  readonly deferred = new Set<string>();
  /** Ticket-IDs, deren Sandbox mit einem Fehler abbricht. */
  readonly failing = new Set<string>();

  constructor(private repo: FakeRepo) {}

  async plan(tickets: Ticket[]): Promise<PlannedIssue[]> {
    this.plannedWith.push(tickets);
    return tickets
      .map((t) => ({
        id: String(t.number),
        title: t.title,
        branch: `sandcastle/issue-${t.number}`,
      }))
      .filter((issue) => !this.deferred.has(issue.id));
  }

  async onTicketBranch<T>(
    issue: PlannedIssue,
    integrationBranch: string,
    work: (session: TicketSession) => Promise<T>,
  ): Promise<T> {
    if (this.failing.has(issue.id)) throw new Error(`Sandbox für #${issue.id} abgebrochen`);
    this.startedFrom.push({ id: issue.id, base: integrationBranch });
    await this.repo.createBranch(issue.branch, integrationBranch);
    const script = this.implementers.get(issue.id) ?? { commits: 1, completed: true };
    return work({
      implement: async (): Promise<AgentRun> => {
        this.implemented.push(issue.id);
        const commits = Array.from({ length: script.commits }, () =>
          this.repo.commit(issue.branch),
        );
        return { commits, completed: script.completed };
      },
      review: async (): Promise<AgentRun> => {
        this.reviewed.push(issue.id);
        return { commits: [], completed: true };
      },
    });
  }

  async merge(into: string, branches: string[]): Promise<AgentRun> {
    this.mergedWith.push({ into, branches });
    for (const branch of branches) {
      if (!this.unmergeable.has(branch)) this.repo.merge(branch, into);
    }
    // Scheitert der Merger, hinterlässt er einen halbfertigen Commit und kein Abschlusssignal.
    if (branches.some((b) => this.unmergeable.has(b))) {
      return { commits: [this.repo.commit(into)], completed: false };
    }
    return { commits: [], completed: true };
  }
}

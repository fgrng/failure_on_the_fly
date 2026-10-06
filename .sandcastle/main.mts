// Parallel Planner with Codex auth — plan → implement → review → merge
//
// The driver wires the real Tracker (gh), Repo (git) and Agents (Sandcastle)
// into the iteration flow in iteration.mts and runs the outer loop:
//   Plan:      The tracker yields the unblocked tickets (`ready-for-agent`,
//              not `Spec`, not `is:blocked`). The driver drops tickets whose
//              closed blocker from another spec is not on main yet and, with
//              `--spec <n>`, every ticket outside spec <n>. The planner gets
//              that list, drops tickets likely to conflict with each other
//              and names each branch.
//   Implement: One implementer per ticket, up to MAX_PARALLEL concurrently.
//              A ticket with parent Spec <n> branches off its integration
//              branch `spec/<n>` (created from main if missing); a ticket
//              without a Spec still branches off the host branch.
//   Review:    Only for branches whose implementer signalled completion.
//   Merge:     One merger per integration branch merges its reviewed ticket
//              branches; spec branches get their own worktree, so the host
//              checkout stays untouched. The driver then closes every ticket
//              whose branch landed. A Spec stays open; its PR closes it.
//
// The outer loop repeats up to MAX_ITERATIONS times, stopping early once the
// backlog is exhausted (a plan with no issues).
//
// Usage:
//   npm run sandcastle                  — Claude Code line-up (default)
//   npm run sandcastle -- --agent codex — Codex line-up
//   npm run sandcastle:codex            — same, without the `--` dance
//   npm run sandcastle -- --spec 321    — only the sub-issues of spec #321

import { parseArgs } from "node:util";
import { DEFAULT_LINEUP, LINEUPS, sandcastleAgents } from "./agents.mts";
import { runIteration } from "./iteration.mts";
import { currentBranch, gitRepo } from "./repo.mts";
import { githubTracker } from "./tracker.mts";

// Maximum number of plan→execute→merge iterations to run before stopping.
const MAX_ITERATIONS = 10;

// Maximum number of issues to implement+review concurrently within one iteration.
const MAX_PARALLEL = 4;

const { values: cliArgs } = parseArgs({
  options: {
    agent: { type: "string", short: "a", default: DEFAULT_LINEUP },
    spec: { type: "string" },
  },
});

const lineupName = cliArgs.agent ?? DEFAULT_LINEUP;
const lineup = LINEUPS[lineupName];

if (!lineup) {
  console.error(
    `Unknown --agent "${lineupName}". Available: ${Object.keys(LINEUPS).join(", ")}`,
  );
  process.exit(1);
}

const spec = cliArgs.spec === undefined ? undefined : Number(cliArgs.spec);
if (spec !== undefined && !Number.isInteger(spec)) {
  console.error(`--spec expects an issue number, got "${cliArgs.spec}".`);
  process.exit(1);
}

console.log(`Agent line-up: ${lineupName}`);
if (spec !== undefined) console.log(`Limited to the sub-issues of spec #${spec}.`);

const deps = {
  tracker: githubTracker,
  repo: gitRepo,
  agents: sandcastleAgents(lineup),
  targetBranch: currentBranch(),
  maxParallel: MAX_PARALLEL,
  spec,
};

for (let iteration = 1; iteration <= MAX_ITERATIONS; iteration++) {
  console.log(`\n=== Iteration ${iteration}/${MAX_ITERATIONS} ===\n`);
  const { planned } = await runIteration(deps);
  if (planned === 0) break;
}

console.log("\nAll done.");

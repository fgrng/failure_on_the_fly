// Parallel Planner with Codex auth — plan → implement → review → merge
//
// This template drives a four-phase workflow, processing multiple issues in
// parallel per iteration:
//   Phase 1 (Plan):      The planner agent inspects the open issues, builds a
//                        dependency graph, and emits a <plan> of unblocked
//                        issues, each with a deterministic branch name.
//   Phase 2 (Implement): One implementer agent per issue implements the change
//                        on the issue's branch (using RGR) and commits. Runs up
//                        to MAX_PARALLEL issues concurrently.
//   Phase 2b (Review):   The reviewer agent reviews each branch that carries
//                        unmerged work — in the same sandbox — and refines it.
//   Phase 3 (Merge):     The merger agent merges every reviewed branch back
//                        together and closes the corresponding issues.
//
// Which model runs which phase is configured in one place below (see "Agents").
// Every sandbox mounts the host ~/.codex and ~/.claude directories read-only
// and copies the auth material into place, so both CLIs are authenticated
// regardless of which one a phase is configured to use.
//
// The outer loop repeats up to MAX_ITERATIONS times, stopping early once the
// backlog is exhausted (a plan with no issues).
//
// Usage:
//   npm run sandcastle                  — Claude Code line-up (default)
//   npm run sandcastle -- --agent codex — Codex line-up
//   npm run sandcastle:codex            — same, without the `--` dance

import { execFileSync } from "node:child_process";
import os from "node:os";
import path from "node:path";
import { parseArgs } from "node:util";
import * as sandcastle from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";
import { z } from "zod";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

// Configure mounts for the .codex / .claude folders containing auth info.
// <user>
const hostCodexHome = path.join(os.homedir(), ".codex");
const sandboxCodexMount = "/mnt/host-codex";
const sandboxCodexHome = "/home/agent/.codex";

const hostClaudeHome = path.join(os.homedir(), ".claude");
const sandboxClaudeMount = "/mnt/host-claude";
const sandboxClaudeHome = "/home/agent/.claude";
// </user>

// Maximum number of plan→execute→merge iterations to run before stopping.
const MAX_ITERATIONS = 10;

// Maximum number of issues to implement+review concurrently within one iteration.
const MAX_PARALLEL = 4;

// Maximum agent invocations the implementer gets per issue. The implement
// prompt is written as a Ralph loop ("REPEAT until done", "notes for next
// iteration"), which only works if the agent is re-invoked after a run that
// ends without the completion signal. Sandcastle's default is 1, which would
// silently cut the loop after a single invocation.
const MAX_IMPLEMENT_ITERATIONS = 20;

// ---------------------------------------------------------------------------
// Agents — one place to swap models per phase
// ---------------------------------------------------------------------------
//
// One line-up per CLI, picked at startup with `--agent`. Both CLIs are
// installed in the image and both are authenticated by the hooks below, so
// either line-up works as-is.

type Lineup = {
  planner: sandcastle.AgentProvider;
  implementer: sandcastle.AgentProvider;
  reviewer: sandcastle.AgentProvider;
  merger: sandcastle.AgentProvider;
};

const LINEUPS: Record<string, Lineup> = {
  claude: {
    planner: sandcastle.claudeCode("claude-sonnet-5", { effort: "medium" }),
    implementer: sandcastle.claudeCode("claude-opus-5", { effort: "medium" }),
    reviewer: sandcastle.claudeCode("claude-opus-5", { effort: "high" }),
    merger: sandcastle.claudeCode("claude-opus-5", { effort: "high" }),
  },
  codex: {
    planner: sandcastle.codex("gpt-5.6-terra"),
    implementer: sandcastle.codex("gpt-5.6-sol", { effort: "medium" }),
    reviewer: sandcastle.codex("gpt-5.6-sol", { effort: "high" }),
    merger: sandcastle.codex("gpt-5.6-sol", { effort: "high" }),
  },
};

const DEFAULT_LINEUP = "claude";

const { values: cliArgs } = parseArgs({
  options: { agent: { type: "string", short: "a", default: DEFAULT_LINEUP } },
});

const lineupName = cliArgs.agent ?? DEFAULT_LINEUP;
const lineup = LINEUPS[lineupName];

if (!lineup) {
  console.error(
    `Unknown --agent "${lineupName}". Available: ${Object.keys(LINEUPS).join(", ")}`,
  );
  process.exit(1);
}

console.log(`Agent line-up: ${lineupName}`);

const plannerAgent = lineup.planner;
const implementerAgent = lineup.implementer;
const reviewerAgent = lineup.reviewer;
const mergerAgent = lineup.merger;

// Shape the planner must emit inside its <plan> tag. Validated by Sandcastle,
// so a malformed or missing plan fails with a schema error instead of a raw
// JSON.parse crash.
const planSchema = z.object({
  issues: z.array(
    z.object({ id: z.string(), title: z.string(), branch: z.string() }),
  ),
});

// docker() sandbox config wiring the read-only host auth mounts and CODEX_HOME.
// Called fresh per sandbox so each phase gets its own configured container.
// Claude Code needs no equivalent env var — /home/agent/.claude is already the
// default config location for the agent user inside the sandbox.
const agentSandbox = () =>
  docker({
    env: { CODEX_HOME: sandboxCodexHome },
    mounts: [
      { hostPath: hostCodexHome, sandboxPath: sandboxCodexMount, readonly: true },
      { hostPath: hostClaudeHome, sandboxPath: sandboxClaudeMount, readonly: true },
    ],
  });

// Hooks run inside the sandbox before the agent starts. uv sync ensures fresh
// dependencies; both the managed Python 3.14 toolchain and the project's locked
// wheels are pre-provisioned in the image (see .sandcastle/Dockerfile), so sync
// installs from uv's warm cache and only links the .venv instead of downloading
// the interpreter and dependencies. The second and third commands copy the
// Codex and Claude Code auth material from the read-only mounts into the
// respective config directories so both CLIs are authenticated.
const hooks = {
  host: {
    // config/settings.py reads SECRET_KEY from the environment via .env, but
    // .env is gitignored and therefore absent from a fresh worktree — every
    // `uv run pytest` the prompts ask for would die with KeyError: 'SECRET_KEY'.
    // .env.example carries a placeholder secret, which is all the test suite
    // needs. Guarded by `test -f` so the phases that run against the host
    // checkout directly (planner, merger — branch strategy "head") never
    // overwrite the developer's real .env.
    onWorktreeReady: [{ command: "test -f .env || cp .env.example .env" }],
  },
  sandbox: {
    onSandboxReady: [
      // The image (see .sandcastle/Dockerfile) pre-warms uv's cache, so this
      // normally installs from cache in seconds. The raised timeout is a safety
      // net for a cold cache (first run after a uv.lock change / image rebuild),
      // where wheels are still downloaded.
      { command: "uv sync", timeoutMs: 120_000 },
      {
        command: [
          `mkdir -p "${sandboxCodexHome}"`,
          `test -f "${sandboxCodexMount}/auth.json"`,
          `cp "${sandboxCodexMount}/auth.json" "${sandboxCodexHome}/auth.json"`,
          `if [ -f "${sandboxCodexMount}/config.toml" ]; then cp "${sandboxCodexMount}/config.toml" "${sandboxCodexHome}/config.toml"; fi`,
        ].join(" && "),
      },
      {
        command: [
          `mkdir -p "${sandboxClaudeHome}"`,
          `test -f "${sandboxClaudeMount}/.credentials.json"`,
          `cp "${sandboxClaudeMount}/.credentials.json" "${sandboxClaudeHome}/.credentials.json"`,
          // The host settings.json carries three host-only keys that break or
          // mislead inside the container, so they are stripped rather than
          // copied verbatim:
          //   sandbox       — enables a nested bubblewrap/socat sandbox that is
          //                   absent from the image and, with failIfUnavailable
          //                   set, aborts the agent. It would also be redundant
          //                   next to the Docker sandbox we already run in.
          //   statusLine    — shells out to a script under the host's home.
          //   enabledPlugins— resolves against ~/.claude/plugins, which is not
          //                   copied into the sandbox.
          `if [ -f "${sandboxClaudeMount}/settings.json" ]; then jq 'del(.sandbox, .statusLine, .enabledPlugins)' "${sandboxClaudeMount}/settings.json" > "${sandboxClaudeHome}/settings.json"; fi`,
        ].join(" && "),
      },
    ],
  },
};

// Nothing to copy from the host into the worktree — the uv sync hook above
// provisions the virtualenv and managed Python from scratch inside the sandbox.
const copyToWorktree: string[] = [];

// The branch the driver was started on — the same branch Sandcastle injects as
// TARGET_BRANCH into the prompts, and the baseline every issue branch is
// measured against.
const targetBranch = execFileSync("git", ["rev-parse", "--abbrev-ref", "HEAD"], {
  encoding: "utf8",
}).trim();

// True when the branch already carries commits that are not on the target
// branch — a finished implementation from an earlier iteration that still needs
// review and merge, even though the implementer committed nothing this run.
function branchIsAheadOfTarget(branch: string): boolean {
  try {
    const count = execFileSync(
      "git",
      ["rev-list", "--count", `${targetBranch}..${branch}`],
      { encoding: "utf8" },
    ).trim();
    return count !== "" && count !== "0";
  } catch (error) {
    console.error(`  ! Could not inspect branch ${branch}:`, error);
    return false;
  }
}

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------

for (let iteration = 1; iteration <= MAX_ITERATIONS; iteration++) {
  console.log(`\n=== Iteration ${iteration}/${MAX_ITERATIONS} ===\n`);

  // -------------------------------------------------------------------------
  // Phase 1: Plan — the planner analyzes issues and picks parallelizable work
  // -------------------------------------------------------------------------
  const plan = await sandcastle.run({
    sandbox: agentSandbox(),
    hooks,
    copyToWorktree,
    name: "Planner",
    // Reading and reasoning only, no code to write. Structured output requires
    // exactly one iteration, so this is not merely a default worth spelling out.
    maxIterations: 1,
    agent: plannerAgent,
    promptFile: "./.sandcastle/plan-prompt.md",
    output: sandcastle.Output.object({ tag: "plan", schema: planSchema }),
  });

  const issues = plan.output.issues;

  if (issues.length === 0) {
    console.log("No issues to work on. Exiting.");
    break;
  }

  console.log(
    `Planning complete. ${issues.length} issue(s) to work in parallel:`
  );
  for (const issue of issues) {
    console.log(`  #${issue.id}: ${issue.title} → ${issue.branch}`);
  }

  // -------------------------------------------------------------------------
  // Phase 2: Implement + Review — implement then review each branch. A pool of
  // MAX_PARALLEL workers pulls issues off a shared queue, so a long-running
  // issue never blocks a free slot.
  // -------------------------------------------------------------------------
  type IssueOutcome = { issue: (typeof issues)[number]; merge: boolean };

  const queue = [...issues];
  const worker = async (): Promise<IssueOutcome[]> => {
    const outcomes: IssueOutcome[] = [];
    while (true) {
      const issue = queue.shift();
      if (!issue) return outcomes;

      try {
        await using sandbox = await sandcastle.createSandbox({
          sandbox: agentSandbox(),
          branch: issue.branch,
          hooks,
          copyToWorktree,
        });

        const implement = await sandbox.run({
          name: "Implementer #" + issue.id,
          maxIterations: MAX_IMPLEMENT_ITERATIONS,
          agent: implementerAgent,
          promptFile: "./.sandcastle/implement-prompt.md",
          promptArgs: {
            TASK_ID: issue.id,
            ISSUE_TITLE: issue.title,
            BRANCH: issue.branch,
          },
        });

        const producedCommits = implement.commits.length > 0;
        const hasUnmergedWork =
          producedCommits || branchIsAheadOfTarget(issue.branch);

        if (hasUnmergedWork) {
          if (!producedCommits) {
            console.log(
              `  #${issue.id}: no new commits, but ${issue.branch} is ahead of ${targetBranch} — reviewing anyway.`
            );
          }
          await sandbox.run({
            name: "Reviewer #" + issue.id,
            // A single pass over the finished diff, matching the prompt.
            maxIterations: 1,
            agent: reviewerAgent,
            promptFile: "./.sandcastle/review-prompt.md",
            promptArgs: {
              BRANCH: issue.branch,
              // TARGET_BRANCH is a built-in prompt arg (auto-injected as the
              // host's active branch at run() time, i.e. main) and must not be
              // passed explicitly — doing so throws PromptError.
            },
          });
        }

        outcomes.push({ issue, merge: hasUnmergedWork });
      } catch (error) {
        // Keep the worker alive so one broken issue does not starve the rest
        // of the queue.
        console.error(`  ✗ #${issue.id} (${issue.branch}) failed: ${error}`);
        outcomes.push({ issue, merge: false });
      }
    }
  };

  const settled = await Promise.allSettled(
    Array.from({ length: Math.min(MAX_PARALLEL, queue.length) }, worker)
  );

  for (const outcome of settled) {
    if (outcome.status === "rejected") console.error(outcome.reason);
  }

  const completedIssues = settled.flatMap((outcome) =>
    outcome.status === "fulfilled"
      ? outcome.value.flatMap((entry) => (entry.merge ? [entry.issue] : []))
      : []
  );

  const completedBranches = completedIssues.map((i) => i.branch);

  console.log(
    `\nExecution complete. ${completedBranches.length} branch(es) to merge:`
  );
  for (const branch of completedBranches) {
    console.log(`  ${branch}`);
  }

  if (completedBranches.length === 0) {
    console.log("No commits produced. Nothing to merge.");
    continue;
  }

  // -------------------------------------------------------------------------
  // Phase 3: Merge — one agent merges all branches together
  // -------------------------------------------------------------------------
  await sandcastle.run({
    sandbox: agentSandbox(),
    hooks,
    copyToWorktree,
    name: "Merger",
    maxIterations: 10,
    agent: mergerAgent,
    promptFile: "./.sandcastle/merge-prompt.md",
    promptArgs: {
      BRANCHES: completedBranches.map((b) => `- ${b}`).join("\n"),
      ISSUES: completedIssues
        .map((i) => `- #${i.id}: ${i.title}`)
        .join("\n"),
    },
  });

  console.log("\nBranches merged.");
}

console.log("\nAll done.");

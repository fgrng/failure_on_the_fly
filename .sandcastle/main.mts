// Parallel Planner with Codex auth — plan → implement → review → merge
//
// This template drives a four-phase workflow, processing multiple issues in
// parallel per iteration:
//   Phase 1 (Plan):      A codex agent inspects the open issues, builds a
//                        dependency graph, and emits a <plan> of unblocked
//                        issues, each with a deterministic branch name.
//   Phase 2 (Implement): One codex agent per issue implements the change on the
//                        issue's branch (using RGR) and commits. Runs up to
//                        MAX_PARALLEL issues concurrently.
//   Phase 2b (Review):   A claude-code agent reviews each branch that produced
//                        commits — in the same sandbox — and refines it.
//   Phase 3 (Merge):     A claude-code agent merges every branch with commits
//                        back together and closes the corresponding issues.
//
// Agents: Codex handles planning + implementation; Claude Code handles review +
// merge. Every sandbox mounts the host ~/.codex directory read-only and copies
// auth.json/config.toml into CODEX_HOME so the Codex CLI is authenticated.
//
// The outer loop repeats up to MAX_ITERATIONS times, stopping early once the
// backlog is exhausted (a plan with no issues).
//
// Usage:
//   npx tsx .sandcastle/main.mts
// Or add to package.json:
//   "scripts": { "sandcastle": "npx tsx .sandcastle/main.mts" }

import * as sandcastle from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

// Configure mount for .codex folder containing auth info.
// <user>
import os from "node:os";
import path from "node:path";

const hostCodexHome = path.join(os.homedir(), ".codex");
const sandboxCodexMount = "/mnt/host-codex";
const sandboxCodexHome = "/home/agent/.codex";
// </user>

// Maximum number of plan→execute→merge iterations to run before stopping.
const MAX_ITERATIONS = 10;

// Maximum number of issues to implement+review concurrently within one iteration.
const MAX_PARALLEL = 4;

// docker() sandbox config wiring the read-only host .codex mount and CODEX_HOME.
// Called fresh per sandbox so each phase gets its own configured container.
const codexSandbox = () =>
  docker({
    env: { CODEX_HOME: sandboxCodexHome },
    mounts: [
      { hostPath: hostCodexHome, sandboxPath: sandboxCodexMount, readonly: true },
    ],
  });

// Hooks run inside the sandbox before the agent starts. uv sync ensures fresh
// dependencies; the managed Python 3.14 toolchain is pre-provisioned in the
// image (see .sandcastle/Dockerfile), so sync only links the .venv instead of
// re-downloading the interpreter. The second command copies the Codex auth
// material from the read-only mount into CODEX_HOME so the Codex CLI is
// authenticated.
const hooks = {
  sandbox: {
    onSandboxReady: [
      { command: "uv sync" },
      {
        command: [
          `mkdir -p "${sandboxCodexHome}"`,
          `test -f "${sandboxCodexMount}/auth.json"`,
          `cp "${sandboxCodexMount}/auth.json" "${sandboxCodexHome}/auth.json"`,
          `if [ -f "${sandboxCodexMount}/config.toml" ]; then cp "${sandboxCodexMount}/config.toml" "${sandboxCodexHome}/config.toml"; fi`,
        ].join(" && "),
      },
    ],
  },
};

// Nothing to copy from the host into the worktree — the uv sync hook above
// provisions the virtualenv and managed Python from scratch inside the sandbox.
const copyToWorktree: string[] = [];

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------

for (let iteration = 1; iteration <= MAX_ITERATIONS; iteration++) {
  console.log(`\n=== Iteration ${iteration}/${MAX_ITERATIONS} ===\n`);

  // -------------------------------------------------------------------------
  // Phase 1: Plan — a codex agent analyzes issues and picks parallelizable work
  // -------------------------------------------------------------------------
  const plan = await sandcastle.run({
    sandbox: codexSandbox(),
    hooks,
    copyToWorktree,
    name: "Planner",
    agent: sandcastle.codex("gpt-5.6-terra"),
    promptFile: "./.sandcastle/plan-prompt.md",
  });

  const planMatch = plan.stdout.match(/<plan>([\s\S]*?)<\/plan>/);
  if (!planMatch) {
    throw new Error(
      "Planner did not produce a <plan> tag.\n\n" + plan.stdout
    );
  }

  const { issues } = JSON.parse(planMatch[1]) as {
    issues: { id: string; title: string; branch: string }[];
  };

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
  // Phase 2: Implement + Review — implement then review each branch,
  // max MAX_PARALLEL in parallel. Implement runs on codex, review on claude.
  // -------------------------------------------------------------------------
  let running = 0;
  const queue: (() => void)[] = [];
  const acquire = () =>
    running < MAX_PARALLEL
      ? (running++, Promise.resolve())
      : new Promise<void>((resolve) => queue.push(resolve));
  const release = () => {
    running--;
    const next = queue.shift();
    if (next) {
      running++;
      next();
    }
  };

  const settled = await Promise.allSettled(
    issues.map(async (issue) => {
      await acquire();
      try {
        await using sandbox = await sandcastle.createSandbox({
          sandbox: codexSandbox(),
          branch: issue.branch,
          hooks,
          copyToWorktree,
        });

        const result = await sandbox.run({
          name: "Implementer #" + issue.id,
          agent: sandcastle.codex("gpt-5.6-terra", { effort: "medium" }),
          promptFile: "./.sandcastle/implement-prompt.md",
          promptArgs: {
            TASK_ID: issue.id,
            ISSUE_TITLE: issue.title,
            BRANCH: issue.branch,
          },
        });

        if (result.commits.length > 0) {
          await sandbox.run({
            name: "Reviewer #" + issue.id,
            agent: sandcastle.codex("gpt-5.6-sol"),
            promptFile: "./.sandcastle/review-prompt.md",
            promptArgs: {
              BRANCH: issue.branch,
              // TARGET_BRANCH is a built-in prompt arg (auto-injected as the
              // host's active branch at run() time, i.e. main) and must not be
              // passed explicitly — doing so throws PromptError.
            },
          });
        }

        return result;
      } finally {
        release();
      }
    })
  );

  for (const [i, outcome] of settled.entries()) {
    if (outcome.status === "rejected") {
      console.error(
        `  ✗ #${issues[i].id} (${issues[i].branch}) failed: ${outcome.reason}`
      );
    }
  }

  const completedIssues = settled
    .map((outcome, i) => ({ outcome, issue: issues[i] }))
    .filter(
      (
        entry
      ): entry is {
        outcome: PromiseFulfilledResult<
          Awaited<ReturnType<typeof sandcastle.run>>
        >;
        issue: (typeof issues)[number];
      } =>
        entry.outcome.status === "fulfilled" &&
        entry.outcome.value.commits.length > 0
    )
    .map((entry) => entry.issue);

  const completedBranches = completedIssues.map((i) => i.branch);

  console.log(
    `\nExecution complete. ${completedBranches.length} branch(es) with commits:`
  );
  for (const branch of completedBranches) {
    console.log(`  ${branch}`);
  }

  if (completedBranches.length === 0) {
    console.log("No commits produced. Nothing to merge.");
    continue;
  }

  // -------------------------------------------------------------------------
  // Phase 3: Merge — one claude-code agent merges all branches together
  // -------------------------------------------------------------------------
  await sandcastle.run({
    sandbox: codexSandbox(),
    hooks,
    copyToWorktree,
    name: "Merger",
    maxIterations: 10,
    agent: sandcastle.claudeCode("claude-opus-4-6"),
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

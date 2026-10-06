// Agents über Sandcastle: Line-ups je CLI, Docker-Sandbox mit den
// Auth-Mounts des Hosts und die Agent-Läufe der einzelnen Phasen.

import os from "node:os";
import path from "node:path";
import * as sandcastle from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";
import { z } from "zod";
import type { AgentRun, Agents, PlannedIssue, Ticket, TicketSession } from "./iteration.mts";
import { currentBranch } from "./repo.mts";

// Configure mounts for the .codex / .claude folders containing auth info.
// <user>
const hostCodexHome = path.join(os.homedir(), ".codex");
const sandboxCodexMount = "/mnt/host-codex";
const sandboxCodexHome = "/home/agent/.codex";

const hostClaudeHome = path.join(os.homedir(), ".claude");
const sandboxClaudeMount = "/mnt/host-claude";
const sandboxClaudeHome = "/home/agent/.claude";
// </user>

// Maximum agent invocations the implementer gets per issue. The implement
// prompt is written as a Ralph loop ("REPEAT until done", "notes for next
// iteration"), which only works if the agent is re-invoked after a run that
// ends without the completion signal. Sandcastle's default is 1, which would
// silently cut the loop after a single invocation.
const MAX_IMPLEMENT_ITERATIONS = 20;

// ---------------------------------------------------------------------------
// Line-ups — one place to swap models per phase
// ---------------------------------------------------------------------------
//
// One line-up per CLI, picked at startup with `--agent`. Both CLIs are
// installed in the image and both are authenticated by the hooks below, so
// either line-up works as-is.

export type Lineup = {
  planner: sandcastle.AgentProvider;
  implementer: sandcastle.AgentProvider;
  reviewer: sandcastle.AgentProvider;
  merger: sandcastle.AgentProvider;
};

export const LINEUPS: Record<string, Lineup> = {
  claude: {
    planner: sandcastle.claudeCode("claude-sonnet-5", { effort: "medium" }),
    implementer: sandcastle.claudeCode("claude-opus-5-5", { effort: "medium" }),
    reviewer: sandcastle.claudeCode("claude-opus-5-5", { effort: "high" }),
    merger: sandcastle.claudeCode("claude-opus-5-5", { effort: "high" }),
  },
  codex: {
    planner: sandcastle.codex("gpt-5.6-terra"),
    implementer: sandcastle.codex("gpt-5.6-sol", { effort: "medium" }),
    reviewer: sandcastle.codex("gpt-5.6-sol", { effort: "high" }),
    merger: sandcastle.codex("gpt-5.6-sol", { effort: "high" }),
  },
};

export const DEFAULT_LINEUP = "claude";

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
    // checkout directly (planner, and the merger into the host branch —
    // branch strategy "head") never
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

function agentRun(result: {
  commits: readonly { sha: string }[];
  completionSignal?: string;
}): AgentRun {
  return {
    commits: result.commits.map((c) => c.sha),
    completed: result.completionSignal !== undefined,
  };
}

/** Die echten Agents eines Line-ups, jeder Lauf in einer eigenen Docker-Sandbox. */
export function sandcastleAgents(lineup: Lineup): Agents {
  return {
    async plan(tickets: Ticket[]): Promise<PlannedIssue[]> {
      const plan = await sandcastle.run({
        sandbox: agentSandbox(),
        hooks,
        copyToWorktree,
        name: "Planner",
        // Reading and reasoning only, no code to write. Structured output
        // requires exactly one iteration, so this is not merely a default.
        maxIterations: 1,
        agent: lineup.planner,
        promptFile: "./.sandcastle/plan-prompt.md",
        promptArgs: { ISSUES: JSON.stringify(tickets, null, 2) },
        output: sandcastle.Output.object({ tag: "plan", schema: planSchema }),
      });
      return plan.output.issues;
    },

    async onTicketBranch<T>(
      issue: PlannedIssue,
      integrationBranch: string,
      work: (session: TicketSession) => Promise<T>,
    ): Promise<T> {
      await using sandbox = await sandcastle.createSandbox({
        sandbox: agentSandbox(),
        branch: issue.branch,
        // Nur für einen neuen Ticket-Branch; ein bestehender behält seinen Stand.
        baseBranch: integrationBranch,
        hooks,
        copyToWorktree,
      });
      const promptArgs = {
        TASK_ID: issue.id,
        ISSUE_TITLE: issue.title,
        BRANCH: issue.branch,
        // TARGET_BRANCH is a built-in prompt arg (auto-injected as the host's
        // active branch at run() time) and must not be passed explicitly —
        // doing so throws PromptError. The branch the ticket merges into
        // therefore travels as its own argument.
        INTEGRATION_BRANCH: integrationBranch,
      };
      return await work({
        implement: async () =>
          agentRun(
            await sandbox.run({
              name: "Implementer #" + issue.id,
              maxIterations: MAX_IMPLEMENT_ITERATIONS,
              agent: lineup.implementer,
              promptFile: "./.sandcastle/implement-prompt.md",
              promptArgs,
            }),
          ),
        review: async () =>
          agentRun(
            await sandbox.run({
              name: "Reviewer #" + issue.id,
              // A single pass over the finished diff, matching the prompt.
              maxIterations: 1,
              agent: lineup.reviewer,
              promptFile: "./.sandcastle/review-prompt.md",
              promptArgs,
            }),
          ),
      });
    },

    async merge(into: string, branches: string[]): Promise<AgentRun> {
      // Ein Integrations-Branch bekommt einen eigenen Worktree, damit der
      // Checkout des Hosts unberührt bleibt. Nur der aktive Branch des Hosts
      // (Tickets ohne Spec) wird direkt im Checkout gemergt, weil git einen
      // Branch nicht in zwei Worktrees zugleich auscheckt.
      const branchStrategy: sandcastle.BranchStrategy =
        into === currentBranch() ? { type: "head" } : { type: "branch", branch: into };
      return agentRun(
        await sandcastle.run({
          sandbox: agentSandbox(),
          branchStrategy,
          hooks,
          copyToWorktree,
          name: `Merger ${into}`,
          maxIterations: 10,
          agent: lineup.merger,
          promptFile: "./.sandcastle/merge-prompt.md",
          promptArgs: {
            BRANCHES: branches.map((b) => `- ${b}`).join("\n"),
            INTEGRATION_BRANCH: into,
          },
        }),
      );
    },
  };
}

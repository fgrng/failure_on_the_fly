// Repo über `git` im Checkout des Hosts.

import { execFileSync } from "node:child_process";
import type { Repo } from "./iteration.mts";

/** Der aktive Branch des Hosts, bei Sandcastle zugleich TARGET_BRANCH der Prompts. */
export function currentBranch(): string {
  return execFileSync("git", ["rev-parse", "--abbrev-ref", "HEAD"], {
    encoding: "utf8",
  }).trim();
}

export const gitRepo: Repo = {
  async contains(branch: string, ref: string): Promise<boolean> {
    try {
      execFileSync("git", ["merge-base", "--is-ancestor", ref, branch], {
        stdio: "ignore",
      });
      return true;
    } catch {
      // Exit-Code 1 heißt „nicht enthalten“; ein unbekannter Ref zählt ebenso.
      return false;
    }
  },

  async branchExists(branch: string): Promise<boolean> {
    try {
      execFileSync("git", ["rev-parse", "--verify", "--quiet", `refs/heads/${branch}`], {
        stdio: "ignore",
      });
      return true;
    } catch {
      return false;
    }
  },

  async createBranch(branch: string, base: string): Promise<void> {
    // `git branch` setzt nur die Ref; der Checkout des Hosts bleibt, wo er ist.
    execFileSync("git", ["branch", branch, base], { stdio: "ignore" });
  },

  async resetBranch(branch: string, base: string): Promise<void> {
    // Scheitert, solange der Branch in einem Worktree ausgecheckt ist.
    execFileSync("git", ["branch", "--force", branch, base], { stdio: "ignore" });
  },

  async isPushed(branch: string): Promise<boolean> {
    try {
      const [local, remote] = execFileSync(
        "git",
        ["rev-parse", `refs/heads/${branch}`, `refs/remotes/origin/${branch}`],
        { encoding: "utf8", stdio: "pipe" },
      )
        .trim()
        .split("\n");
      return local === remote;
    } catch {
      return false;
    }
  },

  async push(branch: string): Promise<void> {
    // Nach einem Neustart von main ist der Push kein Fast-Forward. Die Lease
    // schützt Commits auf origin, die dieser Checkout noch nicht kennt.
    execFileSync("git", ["push", "--force-with-lease", "origin", `${branch}:${branch}`], {
      stdio: "pipe",
    });
  },
};

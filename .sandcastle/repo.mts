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
};

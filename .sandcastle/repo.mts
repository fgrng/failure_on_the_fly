// Repo über `git` im Checkout des Hosts.

import { execFileSync } from "node:child_process";
import { MAIN_BRANCH, type Repo } from "./iteration.mts";

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

  async branches(prefix: string): Promise<string[]> {
    return git(["for-each-ref", "--format=%(refname:short)", `refs/heads/${prefix}`])
      .split("\n")
      .filter(Boolean);
  },

  async mergeMain(branch: string): Promise<"clean" | "conflict"> {
    if (await gitRepo.contains(branch, MAIN_BRANCH)) return "clean";
    // Ein Branch, der in einem Worktree ausgecheckt ist, würde dort hinter dem
    // Rücken des Checkouts verschoben.
    if (checkedOutBranches().has(branch)) {
      throw new Error(`${branch} is checked out in a worktree`);
    }
    const head = await gitRepo.head(branch);
    let tree: string;
    try {
      // Mergt ohne Worktree und ohne Index; Exit-Code 1 heißt Konflikt.
      tree = git(["merge-tree", "--write-tree", head, MAIN_BRANCH]).split("\n")[0];
    } catch (error) {
      if ((error as { status?: number }).status === 1) return "conflict";
      throw error;
    }
    const commit = git([
      "commit-tree",
      tree,
      "-p",
      head,
      "-p",
      MAIN_BRANCH,
      "-m",
      `Merge branch '${MAIN_BRANCH}' into ${branch}`,
    ]).trim();
    git(["update-ref", `refs/heads/${branch}`, commit, head]);
    return "clean";
  },

  async head(branch: string): Promise<string> {
    return git(["rev-parse", `refs/heads/${branch}`]).trim();
  },

  async resetBranch(branch: string, head: string): Promise<void> {
    git(["update-ref", `refs/heads/${branch}`, head]);
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

function git(args: string[]): string {
  return execFileSync("git", args, { encoding: "utf8", stdio: "pipe" });
}

// Die Branches, die in irgendeinem Worktree des Repos ausgecheckt sind.
function checkedOutBranches(): Set<string> {
  return new Set(
    git(["worktree", "list", "--porcelain"])
      .split("\n")
      .filter((line) => line.startsWith("branch refs/heads/"))
      .map((line) => line.slice("branch refs/heads/".length)),
  );
}

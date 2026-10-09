import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, renameSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { gitRepo } from "./repo.mts";

// Ein frisches Repo als Arbeitsverzeichnis, dessen origin/main auf dem ersten
// Commit steht; gitRepo arbeitet immer im Arbeitsverzeichnis.
function freshRepo(): (...args: string[]) => string {
  const dir = mkdtempSync(join(tmpdir(), "sandcastle-repo-"));
  process.chdir(dir);
  const git = (...args: string[]) =>
    execFileSync("git", ["-c", "user.name=Test", "-c", "user.email=test@example.org", ...args], {
      encoding: "utf8",
    });
  git("init", "--quiet", "--initial-branch=main");
  return git;
}

// Legt `file` mit `content` an und committet es.
function commitFile(git: (...args: string[]) => string, file: string, content: string): void {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, content);
  git("add", "--all");
  git("commit", "--quiet", "-m", `add ${file}`);
}

const MIGRATION = "from django.db import migrations\n\n\nclass Migration(migrations.Migration):\n    operations = []\n";

test("eine neue Datei mit Umlaut im Namen zählt wie geschrieben", async () => {
  const git = freshRepo();
  commitFile(git, "README.md", "x\n");
  git("update-ref", "refs/remotes/origin/main", "HEAD");
  git("switch", "--quiet", "-c", "spec/30");
  commitFile(git, "vignetten/migrations/0002_übung.py", MIGRATION);

  assert.deepEqual(await gitRepo.addedFiles("spec/30"), ["vignetten/migrations/0002_übung.py"]);
});

test("eine neue Datei, die eine gelöschte ähnlich ersetzt, zählt als neu", async () => {
  const git = freshRepo();
  commitFile(git, "vignetten/migrations/0001_initial.py", MIGRATION);
  git("update-ref", "refs/remotes/origin/main", "HEAD");
  git("switch", "--quiet", "-c", "spec/30");
  renameSync("vignetten/migrations/0001_initial.py", "vignetten/migrations/0001_squashed.py");
  git("add", "--all");
  git("commit", "--quiet", "-m", "squash");

  assert.deepEqual(await gitRepo.addedFiles("spec/30"), ["vignetten/migrations/0001_squashed.py"]);
});

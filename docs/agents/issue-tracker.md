# Backlog: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`
- **Link a blocking edge**: see [Dependency edges](#dependency-edges-blocked-by) below — use GitHub's native issue dependencies, not just a `Blocked by #N` line in the body.

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## Dependency edges (blocked-by)

Record blocking edges as **native GitHub dependencies**, not just `Blocked by #N` body text. `gh` has no flag for it; use the REST API. Gotcha: pass the blocker's **numeric database `id`** (not `#number`) as a **typed integer** (`-F`, not `-f`). Publish blockers first.

```bash
blocker_id=$(gh api repos/OWNER/REPO/issues/<blocker-number> --jq '.id')
gh api --method POST repos/OWNER/REPO/issues/<blocked-number>/dependencies/blocked_by -F issue_id="$blocker_id"
# verify (gh issue view --json blockedBy has no .number — use this):
gh api repos/OWNER/REPO/issues/<blocked-number>/dependencies/blocked_by --jq '[.[].number]'
```

## When a skill says "publish to the backlog"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

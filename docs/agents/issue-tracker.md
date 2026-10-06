# Issue tracker: GitHub

Issues and specs live as GitHub issues in this repo; use the `gh` CLI.

- **Read**: `gh issue view <n> --comments`.
- **List**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, filtered with `--label` / `--state`.
- **Closing work**: `gh issue close <n> --comment "..."`, following [Closing work](#closing-work) below.
- **PRs as a request surface: no.** _(`/triage` reads this flag.)_ PRs here come from integration branches and are the maintainer's own work.

## Closing work

Code reaches `main` only through a pull request from an **integration branch**:

- Spec `<n>` (labelled `Spec`) has its own integration branch `spec/<n>`, created from `main` on first use. Its tickets branch off it and merge back into it.
- Tickets without a parent spec share the rolling integration branch `sandcastle/standalone`.

Sandcastle runs `git fetch origin` at the start of every run and measures everything against `origin/main`; below, `main` means `origin/main`. It never touches the checkout it was started from: an integration branch checked out there is skipped for the whole run (no update, none of its tickets, no closing phase), and the log says so.

Each issue closes at its own merge:

- **Ticket**: closes once its branch is in its integration branch, not `main`. Sandcastle closes it itself after verifying the merge with `git merge-base --is-ancestor`; agents leave it open. If the merger ends without its completion signal, Sandcastle resets the integration branch to its state before the merger and closes none of its tickets.
- **Blocker from the same spec**: counts as done once it is merged into `spec/<n>` (the script then closes it).
- **Blocker from another spec**: counts as done only once that spec is closed and merged into `main`, via its PR or, if merged by hand, because `spec/<m>` is contained in `main`.
- **Blocker without a spec**: counts as done once it is on `main`: its `sandcastle/issue-<n>` branch is there, or a commit there references it as `(#<n>` (keep this commit convention).
- **Spec**: closes when its PR merges into `main`, through the `Closes #<n>` that ends the PR body. That PR is the only way a spec closes, so leave parent issues untouched (state, body, labels) while writing, implementing or closing tickets.

When every sub-issue of a spec is closed and `spec/<n>` has no open PR, Sandcastle runs the spec's **closing phase**: `code-review` over the whole spec against `main`, a fix of its standards and correctness findings, a PR text from the `pr` skill with the spec findings as "Offene Punkte", then push and PR from `spec/<n>` to `main`. A failed closing phase is retried by the next run, not by later iterations of the same run. From then on the spec is **locked**: Sandcastle comments on its remaining tickets and moves them from `ready-for-agent` to `ready-for-human`. Late work goes into a new spec.

`sandcastle/standalone` has no closing phase. Whenever it has commits not on `main`, Sandcastle pushes it and opens or extends its PR; after that PR merges, the next run restarts the branch from `main`.

The maintainer merges every PR by hand, with a merge commit, once CI is green. The merge commit keeps each ticket's commits and issue references in `main`'s history for `code-review` and `retro`.

## Relationships: sub-issues and blocking edges

Both endpoints take the other issue's numeric **database `id`** (`gh api repos/{owner}/{repo}/issues/<n> --jq .id`, not the `#number` or `node_id`) as a typed integer (`-F`, not `-f`). Publish parents and blockers first. `gh api` fills in `{owner}/{repo}` itself.

```bash
# child as sub-issue of a spec or wayfinder map
gh api --method POST repos/{owner}/{repo}/issues/<parent>/sub_issues -F sub_issue_id=<child-id>
# blocking edge (native dependency, not "Blocked by #N" body text)
gh api --method POST repos/{owner}/{repo}/issues/<blocked>/dependencies/blocked_by -F issue_id=<blocker-id>
# verify (gh issue view --json blockedBy has no .number)
gh api repos/{owner}/{repo}/issues/<blocked>/dependencies/blocked_by --jq '[.[].number]'
```

A ticket is unblocked when `issue_dependencies_summary.blocked_by` is 0 (it counts open blockers only).

## Wayfinding operations

Used by `/wayfinder`.

- **Map**: one issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body.
- **Child ticket**: a sub-issue of the map, labelled `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`).
- **Frontier**: the map's open, unassigned sub-issues with zero open blockers; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: comment the answer, close the ticket, then append a context pointer (gist + link) to the map's Decisions-so-far.

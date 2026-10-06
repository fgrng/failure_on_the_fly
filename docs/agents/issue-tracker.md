# Issue tracker: GitHub

Issues and specs live as GitHub issues in this repo; use the `gh` CLI.

- **Read**: `gh issue view <n> --comments`.
- **List**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, filtered with `--label` / `--state`.
- **Closing work**: `gh issue close <n> --comment "..."`. Work lands on `main` directly; PRs are optional and never required to close a ticket.
- **PRs as a request surface: no.** _(`/triage` reads this flag.)_

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

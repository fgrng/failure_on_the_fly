# Triage Labels

All five triage roles use their canonical names as labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.

## Spec

Label every spec issue (from `/to-spec`) **`Spec`**, alongside `ready-for-agent`. Sandcastle (`.sandcastle/tracker.mts`) hands the planner `ready-for-agent` issues minus `Spec` minus `is:blocked`, so AFK agents run a spec's unblocked tickets, never the spec itself; both would touch the same files and collide. Ticket order comes from native blocked-by edges, not from the planner: a blocker in the same spec releases its ticket once merged into the spec branch, a blocker from another spec only once that spec is closed and merged into `main` (details in `issue-tracker.md#closing-work`). `npm run sandcastle -- --spec <n>` limits a run to the sub-issues of spec `<n>`. Tickets are sub-issues of their spec and carry no type label.

Sandcastle changes a label only at the lock: once spec `<n>` has an open PR, Sandcastle comments on its remaining tickets and swaps `ready-for-agent` for `ready-for-human`. Integration branches, when tickets and specs close, and the PR flow are in [issue-tracker.md](issue-tracker.md#closing-work).

## Other labels

- **`question`**: an open design decision for the maintainer. Distinct from `needs-info`, which waits on the reporter.
- Older issues and comments say `AFK` / `HITL`; read them as `ready-for-agent` / `ready-for-human`.

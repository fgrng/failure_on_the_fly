# Triage Labels

All five triage roles use their canonical names as labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.

## Spec

Label every spec issue (from `/to-spec`) **`Spec`**, alongside `ready-for-agent`. Sandcastle (`.sandcastle/tracker.mts`) hands the planner `ready-for-agent` issues minus `Spec` minus `is:blocked`, so AFK agents run a spec's unblocked tickets, never the spec itself; both would touch the same files and collide. Ticket order comes from native blocked-by edges, not from the planner. `.sandcastle/iteration.mts` closes a ticket once its branch is merged, and closes the spec once all its sub-issues are closed. Tickets are sub-issues of their spec and carry no type label.

## Other labels

- **`question`**: an open design decision for the maintainer. Distinct from `needs-info`, which waits on the reporter.
- Older issues and comments say `AFK` / `HITL`; read them as `ready-for-agent` / `ready-for-human`.

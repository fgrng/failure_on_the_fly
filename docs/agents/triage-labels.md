# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's backlog.

| Label in mattpocock/skills | Label in our backlog | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `Sandcastle`         | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

## Spec vs. Ticket

Two labels separate specification from executable work:

| Label    | Meaning                                                                                                   |
| -------- | -------------------------------------------------------------------------------------------------------- |
| `Spec`   | A specification / umbrella issue that describes a requirement. **Never carries `Sandcastle`** — AFK agents must not implement a spec directly; it is only the source for decomposed tickets. |
| `Ticket` | An executable sub-task that implements part of a `Spec`. Carries `Sandcastle` once it is ready for work.  |

A `Spec` and its `Ticket`s overlap heavily (same files, same models). If a spec kept the `Sandcastle` label, the planner would pick up both the spec and its tickets and produce duplicate, conflicting branches. Keep `Sandcastle` on tickets only.

## Agent state labels

The `agent:*` labels track an issue's position in the AFK-agent workflow:

| Label               | Meaning                                                                                                                                                     |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agent:implement`   | Ready for the implement workflow to run.                                                                                                                    |
| `agent:queued`      | Ready for agent work, but waiting on declared native GitHub blockers. Auto-promotes when blockers clear — see [queued-promotion.md](./queued-promotion.md). |
| `agent:in-progress` | An implement run is currently active.                                                                                                                       |
| `agent:review`      | PR is ready for the automated review workflow.                                                                                                              |
| `agent:blocked`     | A run failed or was refused; needs human attention before retry.                                                                                            |
| `agent:to-issues`   | Spec is ready to be decomposed into sub-issues (tickets).                                                                                                              |

# TASK

Fix the findings of the spec review of spec #{{SPEC}} on its integration branch `{{INTEGRATION_BRANCH}}` (your current branch). It becomes a pull request to `main` once you are done.

<findings>

{{FINDINGS}}

</findings>

Read the spec with `gh issue view {{SPEC}} --comments` for context. Fix only these findings; do not pick up other work.

# EXECUTION

- **Standards findings:** fix them. Behaviour stays exactly as it is; only the shape of the code changes.
- **Correctness findings:** write a test that shows the bug first, then fix it.

Do not comment on or close any issue; the driver script opens the pull request.

# FEEDBACK LOOPS

1. Run `uv run pytest` to see the starting state.
2. Make the changes and commit them in one commit whose message starts with `RALPH: Spec-Review -` and references `(Spec #{{SPEC}})`.
3. Run `uv run pytest` again and fix whatever fails. The branch must end green.

Once complete, and only if `uv run pytest` is green, output <promise>COMPLETE</promise>.

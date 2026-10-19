# TASK

Fix the findings of the spec review of spec #{{SPEC}} on its integration branch `{{INTEGRATION_BRANCH}}` (your current branch). It becomes a pull request to `main` once you are done.

<standards>

{{STANDARDS}}

</standards>

<correctness>

{{CORRECTNESS}}

</correctness>

An empty block has no findings.

Read the spec with `gh issue view {{SPEC}}` and its comments with `gh issue view {{SPEC}} --comments` for context; `--comments` alone omits the issue text. Fix only these findings; do not pick up other work.

# EXECUTION

- **`<standards>`:** fix them. Behaviour stays exactly as it is; only the shape of the code changes.
- **`<correctness>`:** write a test that shows the bug first, then fix it.

Do not comment on or close any issue; the driver script opens the pull request.

# FEEDBACK LOOPS

The branch is green, so there is no starting run: every change reached it through a full `uv run pytest` (the merger, the ticket reviewer before a fast-forward, or the driver after merging `main`).

1. Make the changes and commit them in one commit whose message starts with `RALPH: Spec-Review -` and references `(Spec #{{SPEC}})`.
2. Run `uv run pytest` and fix whatever fails. The branch must end green. Skip this if your commit changes only Markdown files.

Once complete, and only if these tests are green or were skipped, output <promise>COMPLETE</promise>.

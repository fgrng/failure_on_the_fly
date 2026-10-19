# TASK

Fix issue {{TASK_ID}}: {{ISSUE_TITLE}}

Pull in the issue with `gh issue view <ID>` and its comments with `gh issue view <ID> --comments`; `--comments` alone omits the issue text. If it has a parent PRD, pull that in too.

Only work on the issue specified.

Work on branch {{BRANCH}}. It branched off `{{INTEGRATION_BRANCH}}` and will be merged back into it. Make commits and run tests.

# CONTEXT

Here are the last 10 commits:

<recent-commits>

!`git log -n 10 --format="%H%n%ad%n%B---" --date=short`

</recent-commits>

# EXPLORATION

Explore the repo and fill your context window with relevant information that will allow you to complete the task.

Pay extra attention to test files that touch the relevant parts of the code.

# EXECUTION

If applicable, use RGR to complete the task.

1. RED: write one test
2. GREEN: write the implementation to pass that test
3. REPEAT until done
4. REFACTOR the code

# FEEDBACK LOOPS

Run only the tests your change can affect, never the whole suite; the merger runs `uv run pytest` after you.

Run the test modules of the apps you touched, e.g. `uv run pytest vignetten/tests` or a single test file. Before committing, make sure these tests pass.

If you changed only Markdown files, run no tests: no test reads them.

# COMMIT

Make a git commit. The commit message must:

1. Start with `RALPH:` prefix
2. Include task completed + PRD reference
3. Key decisions made
4. Files changed
5. Blockers or notes for next iteration

Keep it concise.

# THE ISSUE

Before you output COMPLETE, check every acceptance criterion of the issue against your change. A criterion you did not meet, met only in part, or deliberately left out goes into one comment on the issue, in German, quoting the criterion and saying why: `gh issue comment <ID> --body-file -`. A note in the commit message does not reach the person who decides.

If the task is not complete, leave a comment on the issue with what was done.

Do not close the issue - this will be done later.

Once complete, output <promise>COMPLETE</promise>.

# FINAL RULES

ONLY WORK ON A SINGLE TASK.

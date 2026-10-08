# TASK

Spec #{{SPEC}} adds these migrations on its integration branch `{{INTEGRATION_BRANCH}}` (your current branch). It becomes a pull request to `main` once you are done.

<migrations>

{{MIGRATIONS}}

</migrations>

Tests that run exactly these migrations (via `MigrationExecutor`, migrating forward and back) checked them while the spec was built. They do not belong on `main` (ADR-0031). Remove them.

# EXECUTION

- Remove only tests that run one of the migrations above. Leave tests of older migrations, already on `main`, as they are.
- Do not touch production code or migrations.
- Remove helpers that no test uses any more.
- If no test runs these migrations, change nothing.

Do not comment on or close any issue; the driver script opens the pull request.

# FEEDBACK LOOPS

The branch is green, so there is no starting run.

1. Commit the removal in one commit whose message starts with `RALPH: Migrationstests -` and references `(Spec #{{SPEC}})`.
2. Run `uv run pytest` and fix whatever fails. The branch must end green.

Once complete, and only if these tests are green, or you changed nothing, output <promise>COMPLETE</promise>.

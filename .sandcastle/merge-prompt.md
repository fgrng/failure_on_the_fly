# TASK

Merge the following branches into the current branch, `{{INTEGRATION_BRANCH}}`:

{{BRANCHES}}

For each branch:

1. Run `git merge <branch> --no-edit`
2. If there are merge conflicts, resolve them intelligently by reading both sides and choosing the correct resolution

After all branches are merged, run `{{TESTS}}` once and fix whatever fails. Then make a single commit summarizing the merge.

Do not close any issues; the driver script closes them after verifying each merge.

Once you've merged everything you can, output <promise>COMPLETE</promise>.

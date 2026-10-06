# ISSUES

Here are the open issues in the repo:

<issues-json>

!`gh issue list --state open --label ready-for-agent --search "-label:Spec -is:blocked" --limit 100 --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`

</issues-json>

The list above has already been filtered to issues ready for work. Issues with an open blocked-by dependency are excluded, so every listed issue is unblocked.

# TASK

Pick the issues to work on in parallel this iteration. Each runs on its own branch and all branches are merged afterwards, so avoid merge conflicts:

- Judge whether issues are likely to modify overlapping files or modules (same model, view, template, migration, or test module).
- For each conflict-prone pair, plan only one of them (the lower issue number). The other stays open and is picked up in a later iteration.

Assign each planned issue a branch name using the exact format `sandcastle/issue-{id}` (no slug or other suffix). This must be deterministic so that re-planning the same issue always produces the same branch name and accumulated progress is preserved.

# OUTPUT

Output your plan as a JSON object wrapped in `<plan>` tags:

<plan>
{"issues": [{"id": "42", "title": "Fix auth bug", "branch": "sandcastle/issue-42"}]}
</plan>

Include every listed issue except those deferred because of a conflict. If the list is empty, output `<plan>{"issues": []}</plan>` so the run can exit cleanly. Always emit the `<plan>` tags.

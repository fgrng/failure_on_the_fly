# Domain Docs

How the engineering skills should consume and maintain this repo's domain documentation.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary. It says *what* a term means; the *why* lives in the ADRs.
- **`docs/adr/`** — read the ADRs that touch the area you're about to work in. Skip files whose frontmatter says `superseded` or `deprecated` unless you need the historical reasoning; follow `superseded-by` instead.

Open questions are not kept in a file. They live as issues in the tracker (see `issue-tracker.md`).

## File structure

```
/
├── CONTEXT.md
└── docs/adr/
    ├── 0001-fehlermuster-als-einziger-oberbegriff.md
    └── …
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

A term earns a glossary entry when code, an ADR, or the user interface carries it. Architecture vocabulary (seams, sinks, mixins) does not belong in the glossary; its home is the ADR that introduces it.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (raise it in the ticket you're working on).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_

## ADR conventions

### The decision text is immutable

Once an ADR is accepted, its decision text is not rewritten. Everything that changes afterwards is expressed through the frontmatter status, one amendment block, and new ADRs. Git history is not a substitute: a reader following an ADR reference from a code comment must find the reasoning that shaped that code, not today's version of it.

The one-off consolidation in #235 (2026-09) merged and re-labelled older ADRs. That was the exception that established this rule.

### Frontmatter

```yaml
---
status: accepted | amended | superseded | deprecated
amended-by: [ADR-0037, "#168"]   # only with amended
superseded-by: ADR-0039          # only with superseded
deprecated-by: "#123"            # optional with deprecated
---
```

- **`accepted`** — the decision holds as written.
- **`amended`** — the decision holds, but a later ADR or issue narrows, extends, or corrects a fact in it. The text stays; a single amendment block under the title carries the delta.
- **`superseded`** — the decision no longer holds; another ADR replaces it. The text stays as the reasoning of its time. Amendment blocks are removed, the frontmatter carries the warning.
- **`deprecated`** — the decision was withdrawn without a successor. `deprecated-by` may point to the issue that withdrew it, or be omitted.

No `date`, no `deciders`, no list of who references the ADR (no backward list). The number in the filename orders ADRs in time.

### Issue or ADR?

An amendment may cite an issue instead of an ADR when only a *fact inside the rule* changed: a number, a name, a colour, a provider. When the *rule itself* changed, a new ADR is required. Test: *would a test break if I still followed the old wording?* If yes, write an ADR.

### Skeleton

Every ADR file follows the same shape, with German section headings:

1. Frontmatter.
2. `# Title` — a sentence that states the decision.
3. Optionally **exactly one** amendment block directly under the title, a blockquote in the form
   `> **Nachgeführt durch ADR-0037, #168:** …`. Never a blockquote in the middle of the text.
4. The decision text, with free sub-headings.
5. Optionally `## Erwogene Optionen`.
6. `## Folgen`.

English headings (`Considered Options`, `Consequences`) are not used.

### Numbering

Take the next free number at merge time, not when the branch is created. Two branches that each claim the next number collide. Until merge, refer to the ADR by its working title.

### Where ADR references may appear

- **Glossary (`CONTEXT.md`)** — at the term that would be incomplete without the decision, as `(ADR-0036)`. Never as a full-text copy of the ADR.
- **Code and templates** — only where the implementation would otherwise look like a mistake.
- **Tests** — freely; a test that guards an ADR rule should name it.
- **README** — never. Its readers are users and operators, not maintainers.
- **ADRs themselves** — forward references to other ADRs are fine; no backward list of what references this one.

Never reference a `superseded` or `deprecated` ADR from the glossary or README. Follow `superseded-by` and point at the successor.

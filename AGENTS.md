When changing public-facing behavior, update docs/verhalten.md (behaviour per area); check README.md only for setup and deployment changes.

Checks: the pre-commit hook (`.githooks/pre-commit`) runs ruff, mdformat and the missing-migrations check on every commit.

## Abschlusslauf

Außerhalb von Sandcastle vor jedem Commit: `uv run pytest`, `uv run ruff format .`, `uv run ruff check .`.

## Agent skills

- **Domain docs**: terminology in GLOSSARY.md, decisions in docs/adr/ (single-context). See docs/agents/domain.md.
- **Issue tracker**: GitHub issues via `gh`. See docs/agents/issue-tracker.md.
- **Triage labels**: canonical names plus `Spec`. See docs/agents/triage-labels.md.
- **Image generation**: framing-story illustrations (`static/images/session/`) via the quota-limited `agy` CLI. See docs/agents/image-generation.md.

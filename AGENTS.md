When changing public-facing behavior, update docs/verhalten.md (behaviour per area); check README.md only for setup and deployment changes.

Checks: the pre-commit hook (`.githooks/pre-commit`) runs ruff, mdformat and the missing-migrations check on every commit.

## Abschlusslauf

Außerhalb von Sandcastle vor jedem Commit: `uv run pytest`, `uv run ruff format .`, `uv run ruff check .`.

## Agent skills

- **Domain docs**: terminology in GLOSSARY.md, decisions in docs/adr/ (single-context). See docs/agents/domain.md.
- **Writing or changing an ADR**: follow docs/adr/README.md; it overrides the domain-modeling skill's ADR-FORMAT.md.
- **Issue tracker**: GitHub issues via `gh`. See docs/agents/issue-tracker.md.
- **Triage labels**: canonical names plus `Spec`. See docs/agents/triage-labels.md.
- **Simulation ohne App**: einen Gesprächsschritt mit Vignette und Prompt-Entwurf per `uv run scripts/simulieren.py` durchspielen. See docs/agents/simulieren.md.
- **Evals ohne App**: Evalgespräche k-mal spielen, Bewerter-Prompts rendern, Urteile zählen (`scripts/evalgespraech.py`, `bewerter_prompt.py`, `urteile_zaehlen.py`). See docs/evals/README.md, Abschnitt «Durchspielen ohne App».
- **App im Browser**: Produktivinstanz (https://onthefly.fgrng.de/, Schreiben nur nach Freigabe) und Dev-Server per `playwright-cli` bedienen, etwa um Vignetten und Kern-Fassungen aus `docs/` einzutragen oder Verhalten und Aussehen zu prüfen. Vor jeder Browserarbeit docs/agents/playwright/README.md lesen, dann die Datei des Bereichs.
- **Image generation**: framing-story illustrations (`static/images/session/`) via the quota-limited `agy` CLI. See docs/agents/image-generation.md.

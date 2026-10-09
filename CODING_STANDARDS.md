# Coding Standards

NEVER use emoji, or unicode that emulates emoji (e.g. ✓, ✗). The only exception is when writing tests and testing the impact of multibyte characters.

## Documentation and Comments

Always write documentation files, issues and comments in German.

Ruff enforces formatting, lint, type hints in signatures and docstrings for public objects (`[tool.ruff.lint]` in `pyproject.toml`, pre-commit hook in `.githooks/`).

Non-public methods need no docstring, but they should have a comment that describes what the method does. This comment should appear after the def line.

Keep comments up-to-date with code changes.

Include examples in docstrings for complex functions.

MUST avoid including redundant comments which are tautological or self-demonstating (e.g. cases where it is easily parsable what the code does at a glance so the comment does)

MUST avoid including comments which leak what this file contains, or leak the original user prompt, ESPECIALLY if it's irrelevant to the output code.

## Testing

### Core Principle

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't break unless behavior changed.

### Good Tests

Integration-style tests that exercise real code paths through public APIs. They describe _what_ the system does, not _how_.

- Test behavior users/callers care about
- Use the public API only
- Survive internal refactors
- One logical assertion per test

### Bad Tests

Red flags:

- Mocking internal collaborators (your own classes/modules)
- Testing private methods
- Asserting on call counts/order of internal calls
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means (e.g. querying a DB) instead of through the interface

Ruff enforces "Testing private methods" mechanically: `SLF001` and `PLC2701` reject access to private members and imports of private names, in tests and production code alike. Exempt are migrations and a transition list in `pyproject.toml` that only gets shorter. Constraint tests that check a DB invariant through an internal seam (e.g. `objects._erstellen`) may do so with a per-line `# noqa: SLF001`, never a per-file exemption.

Build test setup through the public way: `config/tests/aufbau.py` provides accounts with roles, an active model configuration, the final simulation core, vignette drafts and final vignettes.

### What Tests Never Check

**Never the wording of documentation** (ADRs, GLOSSARY.md, README, verhalten.md). An acceptance criterion "the docs name X" is met by updating the docs, not by a test.

- Bad: `assert "Selbsteinsicht" in Path("GLOSSARY.md").read_text()`
- Good: no test; the commit updates GLOSSARY.md.

**Never source code** (CSS declarations, JS expressions, Python AST). Exceptions: import-graph guards (ADR-0016) and lint-style rules over _all_ files of a kind (e.g. "feature CSS uses only semantic tokens").

- Bad: `assert "display: none" in Path("static/css/vignette.css").read_text()`
- Good: render the page and assert on what the user gets, e.g. the element is missing from the response.

**Never expected values from the module under test.** Take them from a fixed literal, a worked example or a spec, not from the module's constants or calculations.

- Bad: `assert ergebnis == MAX_VERSUCHE` with `MAX_VERSUCHE` imported from the module, or an expected value recomputed with the module's own helper.
- Good: `assert ergebnis == 3`, with the 3 taken from the spec.

Enum members (Django choices such as `Sitzung.Status.ABGESCHLOSSEN`) are fine as expected values when the test checks *which* state results; they name the state, they don't compute it. Where the stored spelling itself is the promise (e.g. the export, ADR-0029), expect the literal (`"abgeschlossen"`).

**Never the absence of fields or methods.** Removed code is gone; a test for `not hasattr(Vignette, "titel")` guards nothing a caller can observe.

- Bad: `assert not hasattr(Vignette, "titel")`
- Good: no test; if the removal changes behaviour, test the behaviour.

### Mocking

Mock at **system boundaries** only:

- External APIs (llm-provider, email, etc.)
- Time/randomness
- File system or databases when a real instance isn't practical

**Never mock your own classes/modules or internal collaborators.** If something is hard to test without mocking internals, redesign the interface.

Prefer SDK-style interfaces over generic fetchers at boundaries — each function is independently mockable with a single return shape, no conditional logic in test setup.

### TDD Workflow: Vertical Slices

Do NOT write all tests first, then all implementation. That produces tests that verify _imagined_ behavior and are insensitive to real changes.

Correct approach — one test, one implementation, repeat:

```
RED→GREEN: test1→impl1
RED→GREEN: test2→impl2
RED→GREEN: test3→impl3
```

Each test responds to what you learned from the previous cycle. Never refactor while RED — get to GREEN first.

## Interface Design

### Deep Modules

Prefer deep modules: small interface, deep implementation. A few methods with simple params hiding complex logic behind them.

Avoid shallow modules: large interface with many methods that just pass through to thin implementation. When designing, ask: can I reduce the number of methods? Can I simplify the parameters? Can I hide more complexity inside?

### Design for Testability

1. **Accept dependencies, don't create them** — pass external dependencies in rather than constructing them internally.
2. **Return results, don't produce side effects** — a function that returns a value is easier to test than one that mutates state.
3. **Small surface area** — fewer methods = fewer tests needed, fewer params = simpler test setup.

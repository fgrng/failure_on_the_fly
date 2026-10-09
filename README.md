# failure_on_the_fly

Web-basierter Simulator von Schüler:innen für fachspezifische Fehlermuster. Angehende
Lehrpersonen führen ein kurzes Diagnosegespräch mit einer LLM-simulierten
Schüler:in, die kongruent zu einem beschriebenen Fehlermuster handelt, und
stellen danach eine Diagnose auf. Die Plattform dient dem Training diagnostischer
Gesprächsführung und als Erhebungsinstrument für diagnostische Kompetenzen von Lehrpersonen.

Django-Anwendung mit SQLite; Sprachmodell und Transkription laufen über
austauschbare Anbieter (insbes. `openrouter`).

## Rollen

| Rolle          | Tut                                                                           | Einstieg                  |
| -------------- | ----------------------------------------------------------------------------- | ------------------------- |
| Autor:in       | schreibt und erprobt Vignetten                                                | `/vignetten/`           |
| Ausbilder:in   | stellt Trainings aus finalen Vignetten zusammen                               | `/trainings/eigene/`    |
| Forschende     | baut Erhebungen mit finalen Vignetten und Fragebögen; exportiert Datenspuren | `/erhebungen/eigene/`   |
| Administration | betreibt die Instanz, legt Konten an, konfiguriert die Anbieter               | `/admin/`, `/system/` |

Die drei fachlichen Rollen sind Django-Groups; die Administration ist der
Superuser. Erhebungsteilnehmende brauchen kein Konto: Sie spielen pseudonym
über einen Teilnahme-Link und ein Token.

Was die Anwendung in jedem Bereich genau tut, steht in
[docs/verhalten.md](docs/verhalten.md).

## Lokale Entwicklungsumgebung

Voraussetzung ist [uv](https://docs.astral.sh/uv/) und Python ≥ 3.14.

1. **Abhängigkeiten installieren** (inklusive Entwicklungswerkzeuge):

   ```
   uv sync
   ```
2. **Konfiguration anlegen.** Kopiere `.env.example` nach `.env` — mindestens
   ein beliebiger `SECRET_KEY` und `DEBUG=True`:

   ```
   cp .env.example .env
   ```
3. **Datenbank migrieren:**

   ```
   uv run python manage.py migrate
   ```
4. **Entwicklungsdaten befüllen.** Der Seed legt Testkonten, einen finalen
   Simulationskern, eine aktive Modell-Konfiguration auf dem Anbieter `fake`,
   finale Vignetten sowie ein veröffentlichtes und ein Entwurfs-Training an.
   Er ist idempotent und läuft nur mit `DEBUG=True`:

   ```
   uv run python manage.py entwicklungsdaten_anlegen
   ```

   Alle Testkonten teilen das Passwort `entwicklung`:

   | Konto     | Rolle                   |
   | --------- | ----------------------- |
   | `autor` | alle Rollen (Superuser) |
   | `studi` | ohne Rolle              |
5. **Pre-commit-Hook aktivieren.** Der Hook in `.githooks/` prüft vor jedem
   Commit Formatierung und Lint mit Ruff. Die Einstellung gilt auch für alle
   Worktrees des Klons:

   ```
   git config core.hooksPath .githooks
   ```
6. **Server starten:**

   ```
   uv run python manage.py runserver
   ```

   Die Anwendung ist dann unter http://127.0.0.1:8000/ erreichbar.

Die Testsuite läuft mit `uv run pytest`.

Der Seed aktiviert das Fake-Sprachmodell, damit sich Diagnosegespräche ohne
Zugangsdaten durchklicken lassen. Für echte Antworten wird unter
`/system/modell-konfiguration/` eine Konfiguration mit Anbieter, Modellnamen
und Token angelegt und aktiviert.

## Entwicklungsarbeit mit Coding Agents

Unter `.sandcastle/` liegt ein Skript für [Sandcastle](https://github.com/mattpocock/sandcastle), das offene Issues mit
dem Label `ready-for-agent` (ohne `Spec`, nicht blockiert) in Docker-Sandboxen
abarbeitet: planen, implementieren, reviewen, mergen. Voraussetzung sind Node,
Docker und die Zugangsdaten aus `.sandcastle/.env.example`, kopiert nach
`.sandcastle/.env`. Dann:

```
npm install
npm run sandcastle:build-image
npm run sandcastle
```

Das Sandbox-Image wird nicht automatisch gebaut; ohne den mittleren Schritt
bricht der Lauf mit `Image 'sandcastle:failure_on_the_fly' not found locally`
ab. Zu wiederholen ist er nach jeder Änderung an `.sandcastle/Dockerfile` und
nach jeder an `uv.lock` — das Image hält den vorgewärmten uv-Cache, aus dem
die Sandbox ihre Abhängigkeiten zieht, statt sie neu zu laden.

Codex und Claude Code friert der Docker-Cache auf dem Stand des ersten Builds
ein. `npm run sandcastle:refresh-tools` baut nur diese beiden Schichten neu und
holt die aktuellen Versionen; Python und der uv-Cache bleiben gecacht.

Welche Modelle die vier Rollen (Planner, Implementer, Reviewer, Merger)
fahren, wählt `--agent`:

```
npm run sandcastle                    # Claude Code, der Default
npm run sandcastle:codex              # Codex
npm run sandcastle -- --agent codex   # dasselbe ausgeschrieben
```

Ohne weitere Argumente arbeitet ein Lauf alle bereiten Tickets ab;
`npm run sandcastle -- --spec <n>` beschränkt ihn auf Spec `<n>`: Er plant
nur ihre Sub-Issues ein, aktualisiert nur `spec/<n>` und schließt nur diese
Spec ab; `sandcastle/standalone` und andere Spec-Branches bleiben unberührt.
Die Reihenfolge folgt den Blocked-by-Kanten im Tracker: Ein
Blocker derselben Spec gibt sein Ticket frei, sobald er in `spec/<n>`
gemergt und damit geschlossen ist. Ein Blocker aus einer anderen Spec gibt es
erst frei, wenn diese Spec geschlossen und nach `main` gemergt ist, über ihren
PR oder von Hand. Ein Blocker ohne Spec zählt, sobald sein Code auf `main`
liegt, also sein Ticket-Branch dort enthalten ist oder ein Commit dort auf
ihn verweist (`(#<n>` in der Commit-Nachricht).

Zu Beginn jedes Laufs holt das Skript mit `git fetch origin` den Stand von
GitHub. „`main`“ heißt im Folgenden immer `origin/main`; das lokale `main`
bleibt unberührt und darf veraltet sein. Den Checkout, in dem der Lauf
gestartet wurde, fasst das Skript nicht an. Steht er auf einem
Integrations-Branch, lässt der Lauf diesen Branch aus: kein Update, keine
Tickets seiner Spec, keine Abschlussphase. Das Log meldet das.

Aus Sandcastle kommt Code nur über einen Pull Request von einem
Integrations-Branch nach `main`. Tickets ohne Spec, die interaktiv umgesetzt
werden, landen dagegen direkt auf `main`, mit `(#<n>` in der Commit-Nachricht.
Für Sandcastle gilt:

- Tickets einer Spec `<n>` zweigen vom Integrations-Branch `spec/<n>` ab und
  werden dorthin gemergt; das Skript legt ihn bei Bedarf von `main` an.
  Tickets ohne Spec sammeln sich auf `sandcastle/standalone`.
- Zu Beginn jedes Laufs mergt das Skript `main` in jeden aktiven
  Integrations-Branch; nur bei einem Konflikt löst ein Merger-Agent auf.
- Gemergt und geschlossen werden nur Tickets, deren Implementer sein
  Abschlusssignal gegeben hat und deren Branch nachweislich im
  Integrations-Branch liegt. Das Schließen übernimmt das Skript. Endet der
  Merger ohne Abschlusssignal, setzt das Skript den Integrations-Branch auf
  seinen Stand davor zurück und schließt keines seiner Tickets.
- Sind alle Tickets einer Spec geschlossen, folgt ihre Abschlussphase: ein
  `code-review` über die ganze Spec gegen `main`, die Behebung der Standards-
  und Korrektheitsbefunde, das Streichen der Tests auf die Migrationen, die
  die Spec neu anlegt (nur wenn es welche gibt), ein PR-Text mit dem Skill
  `pr`. Spec-Befunde stehen
  darin als „Offene Punkte“, am Ende `Closes #<n>`. Das Skript pusht
  `spec/<n>` und legt den PR an; die Spec schließt GitHub beim Merge.
  Scheitert die Abschlussphase, versucht sie erst der nächste Lauf erneut.
- Hat eine Spec schon einen offenen PR, plant das Skript ihre übrigen Tickets
  nicht mehr ein, sondern kommentiert sie und stellt sie auf
  `ready-for-human`: Nachzügler gehören in eine neue Spec.
- `sandcastle/standalone` hat keine Abschlussphase. Hat der Branch Commits,
  die nicht auf `main` liegen, pusht ihn das Skript und legt einen PR an oder
  ergänzt den offenen. Ist der PR gemergt, beginnt der Branch im nächsten Lauf
  neu von `main`. Nur dieser Branch wird mit `--force-with-lease` gepusht.

Die PRs mergt die Maintainerin bzw. der Maintainer von Hand, mit Merge-Commit
und erst bei grüner CI. So bleiben die Commits je Ticket samt
Issue-Referenzen in der Historie von `main`. Die Regeln für Agents stehen in
[docs/agents/issue-tracker.md](docs/agents/issue-tracker.md#abschluss-von-arbeit).

Prompts und das Dockerfile der Sandbox liegen ebenfalls in `.sandcastle/`;
Logs und Worktrees des Laufs bleiben dort unversioniert. Die Ablauflogik einer
Iteration (`.sandcastle/iteration.mts`) ist gegen Fakes für Tracker, Repo und
Agents getestet, ohne Docker und ohne Agents:

```
npm run test:sandcastle
```

## Deployment auf Uberspace

Der vollständige Walkthrough — Inbetriebnahme, Abnahme, Backup, Update,
Fehlersuche — steht in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Drei Dinge,
die man vorher wissen muss:

- **Zugangsdaten kommen nicht aus der Umgebung, sondern aus der Datenbank.** Nach der
  Migration ist keine benutzbare Modell-Konfiguration aktiv — es antwortet bis
  dahin kein Sprachmodell. Die Administration legt nach `createsuperuser` unter
  `/system/modell-konfiguration/` eine Konfiguration an und aktiviert sie. Das
  ist dieselbe Folge, die jede Schlüsselrotation verlangt: anlegen und
  aktivieren, nie bearbeiten. Soll auch gesprochen werden, trägt
  `/system/transkription/` den Anbieterzugang für das Audio ein.
- **Transkription ist ein Tor der Betreiber:in.** Sie bleibt gesperrt, solange
  `TRANSKRIPTION_ZERO_RETENTION=True` nicht in der Umgebung steht — die Zusage,
  dass der Auftragsverarbeiter kein Audio behält, gehört nicht ins Formular.
- **Vignettenbilder unter `/media/` sind ohne Anmeldung abrufbar**, wer ihre
  URL kennt. Die Dateinamen sind nicht erratbar, die Auslieferung aber
  ungeschützt.

Ein Gesprächsschritt wartet synchron auf das Sprachmodell, eine Transkription
auf ihren Anbieter; jede wartende Anfrage hält einen Thread. Der gunicorn-Dienst
läuft deshalb mit Thread-Workern, ausgelegt auf 150 gleichzeitige Sitzungen
(Aufteilung im Walkthrough, Begründung in ADR-0050). Beide Nähte begrenzen sich
selbst: ein Gesprächsschritt auf höchstens 90 s über alle Versuche, eine
Transkription auf höchstens 120 s.

## Weitere Dokumentation

- [GLOSSARY.md](GLOSSARY.md) — Glossar der verwendeten Domänensprache
- [docs/verhalten.md](docs/verhalten.md) — Verhalten der Plattform je Bereich
- [docs/adr/](docs/adr/) — Architekturentscheidungen mit Begründung
- [docs/vision.md](docs/vision.md) — Produktvision und Scope
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Produktivbetrieb auf Uberspace
- [AGENTS.md](AGENTS.md) — Arbeitsregeln für Coding-Agents

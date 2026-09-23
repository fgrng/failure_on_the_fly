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
5. **Server starten:**

   ```
   uv run python manage.py runserver
   ```

   Die Anwendung ist dann unter http://127.0.0.1:8000/ erreichbar.

Die Testsuite läuft mit `uv run python manage.py test`.

Der Seed aktiviert das Fake-Sprachmodell, damit sich Diagnosegespräche ohne
Zugangsdaten durchklicken lassen. Für echte Antworten wird unter
`/system/modell-konfiguration/` eine Konfiguration mit Anbieter, Modellnamen
und Token angelegt und aktiviert.

## Entwicklungsarbeit mit Coding Agents

Unter `.sandcastle/` liegt ein Skript für [Sandcastle](https://github.com/mattpocock/sandcastle), das offene Issues mit
dem Label `AFK` in Docker-Sandboxen abarbeitet: planen, implementieren,
reviewen, mergen. Voraussetzung sind Node, Docker und die Zugangsdaten aus
`.sandcastle/.env.example`, kopiert nach `.sandcastle/.env`. Dann:

```
npm install
npx sandcastle docker build-image
npm run sandcastle
```

Das Sandbox-Image wird nicht automatisch gebaut; ohne den mittleren Schritt
bricht der Lauf mit `Image 'sandcastle:failure_on_the_fly' not found locally`
ab. Zu wiederholen ist er nach jeder Änderung an `.sandcastle/Dockerfile` und
nach jeder an `uv.lock` — das Image hält den vorgewärmten uv-Cache, aus dem
die Sandbox ihre Abhängigkeiten zieht, statt sie neu zu laden.

Welche Modelle die vier Phasen fahren, wählt `--agent`:

```
npm run sandcastle                    # Claude Code, der Default
npm run sandcastle:codex              # Codex
npm run sandcastle -- --agent codex   # dasselbe ausgeschrieben
```

Prompts, Coding-Standards und das Dockerfile der Sandbox liegen ebenfalls in
`.sandcastle/`; Logs und Worktrees des Laufs bleiben dort unversioniert.

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

Ein Gesprächsschritt wartet synchron auf das Sprachmodell; der gunicorn-Dienst
braucht deshalb ein großzügiges Timeout (180 s im Walkthrough). Beide Nähte
begrenzen sich selbst: ein Gesprächsschritt auf höchstens 90 s über alle
Versuche, eine Transkription auf höchstens 120 s.

## Weitere Dokumentation

- [CONTEXT.md](CONTEXT.md) — Glossar der verwendeten Domänensprache
- [docs/verhalten.md](docs/verhalten.md) — Verhalten der Plattform je Bereich
- [docs/adr/](docs/adr/) — Architekturentscheidungen mit Begründung
- [docs/vision.md](docs/vision.md) — Produktvision und Scope
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Produktivbetrieb auf Uberspace
- [AGENTS.md](AGENTS.md) — Arbeitsregeln für Coding-Agents

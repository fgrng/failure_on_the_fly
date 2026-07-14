# failure_on_the_fly

Web-basierter Simulator von Schüler:innen mit Fehlermustern für das Üben
diagnostischer Gesprächsführung.

## Start und Anmeldung

Die öffentliche Startseite unter `/` verlinkt auf den Vignetten-Editor und die
Ansicht des Simulationskerns. Diese Bereiche erfordern ein Nutzerkonto; die
Anmeldung erfolgt unter `/accounts/login/`.

## Simulationskern

Angemeldete Nutzer:innen können die aktuellste finale Kern-Fassung und die
aktive Modell-Konfiguration schreibgeschützt unter `/system/kern/` einsehen. Ist noch
kein finaler Kern vorhanden, weist die Ansicht auf `manage.py kern_initialisieren`
hin.

## Lokale Entwicklungsumgebung

Voraussetzung ist [uv](https://docs.astral.sh/uv/) und Python ≥ 3.14.

1. **Abhängigkeiten installieren** (inklusive Entwicklungswerkzeuge):

   ```
   uv sync
   ```

2. **Konfiguration anlegen.** Kopiere `.env.example` nach `.env` und trage die
   Werte ein — mindestens einen beliebigen `SECRET_KEY`, `DEBUG=True` und für
   echte Diagnosegespräche `OPENAI_API_KEY`:

   ```
   cp .env.example .env
   ```

3. **Datenbank migrieren:**

   ```
   uv run python manage.py migrate
   ```

4. **Entwicklungsdaten befüllen.** Der Seed legt Testkonten je Rolle, einen
   finalen Simulationskern, eine aktive OpenAI- und eine Fake-Modell-
   Konfiguration, finale Vignetten sowie ein veröffentlichtes und ein
   Entwurfs-Training an. Er ist idempotent und läuft nur mit `DEBUG=True`:

   ```
   uv run python manage.py entwicklungsdaten_anlegen
   ```

   Alle Testkonten teilen das Passwort `entwicklung`:

   | Konto         | Rolle             |
   | ------------- | ----------------- |
   | `admin`       | Administrator:in (Superuser) |
   | `autorin`     | Autor:in          |
   | `ausbilderin` | Ausbilder:in      |
   | `forschende`  | Forschende:r      |
   | `studi`       | ohne Rolle        |

5. **Server starten:**

   ```
   uv run python manage.py runserver
   ```

   Die Anwendung ist dann unter http://127.0.0.1:8000/ erreichbar.

Die Testsuite läuft mit `uv run python manage.py test`.

> Ohne gesetzten `OPENAI_API_KEY` antwortet das Diagnosegespräch nicht. Für
> reines Durchklicken ohne Schlüssel kannst du in der Django-Shell die
> mitgelieferte Fake-Konfiguration aktivieren:
> `ModellKonfiguration.objects.aktivieren(ModellKonfiguration.objects.get(sprachmodell="fake"))`.
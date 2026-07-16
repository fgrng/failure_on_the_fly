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

## Audioverarbeitung im Training

Vor dem ersten Start eines Trainings entscheiden Teilnehmende einmalig, ob ihr
Audio zur Transkription an einen externen Auftragsverarbeiter übermittelt werden
darf. Das Audio wird danach nicht gespeichert. Bei Ablehnung bleibt das Training
uneingeschränkt über die Tastatur spielbar.

Nach Einwilligung lässt sich jede Frage im Diagnosegespräch per Tastatur oder
über „Aufnahme starten“ eingeben. Die Aufnahme wird bewusst beendet, direkt
transkribiert und anschließend automatisch als Gesprächsschritt abgeschickt;
das Transkript wird davor nicht bearbeitet. Im Debrief kann die Diagnose ebenfalls
in mehreren Aufnahmen ergänzt werden; erst „Training beenden“ schickt sie bewusst
und unwiderruflich ab. Bei einer leeren oder fehlgeschlagenen Transkription kann
die Aufnahme wiederholt werden.

## Erhebungsteilnahme

Ein Teilnahme-Link einer Stichprobe legt im Browser eine pseudonyme Teilnahme an
oder setzt sie fort. Dafür ist kein Nutzerkonto erforderlich; die
Forschungsdaten sind über ein ablesbares Teilnahme-Token von Trainingsaktivitäten
getrennt. Während das Teilnahmefenster läuft, führt der Link zuerst über die
Einwilligung und die Instruktion; diese weist darauf hin, dass das
Diagnosegespräch begrenzt ist. Anschließend werden die gezogenen Vignetten als
persistierte Sitzungen gespielt; Gespräch, Diagnose und interne Denkspur bleiben
Teil der Datenspur, wobei die Denkspur nie in der Teilnehmer:innenansicht erscheint.
Nach jeder Diagnose beginnt unmittelbar die nächste gezogene Vignette; nach der
letzten endet die Teilnahme mit dem Abschlusstext ohne Fragebogen oder Wiederholung.

## Erhebungen verwalten

Konten mit der Rolle `Forschende:r` erreichen unter `/erhebungen/eigene/` ihre
eigenen Erhebungen. In einem Entwurf wählen sie eigene finale Vignetten,
bestimmen eine feste oder zufällige Reihenfolge und pflegen Instruktions-,
Einwilligungs- und Abschlusstext. Reine Entwürfe lassen sich löschen; finale
Erhebungen bleiben unveränderlich erhalten. Das Finalisieren pinnt die aktive
Modell-Konfiguration sichtbar; ein Rückzug ist nur ohne nicht-archivierte oder
datentragende Stichprobe möglich.

## Lokale Entwicklungsumgebung

Voraussetzung ist [uv](https://docs.astral.sh/uv/) und Python ≥ 3.14.

1. **Abhängigkeiten installieren** (inklusive Entwicklungswerkzeuge):

   ```
   uv sync
   ```

2. **Konfiguration anlegen.** Kopiere `.env.example` nach `.env` und trage die
   Werte ein — mindestens einen beliebigen `SECRET_KEY`, `DEBUG=True` und für
   echte Diagnosegespräche `OPENAI_API_KEY`. Audio-Transkription bleibt ohne
   `TRANSKRIPTION_ZERO_RETENTION=True` bewusst gesperrt:

   ```
   cp .env.example .env
   ```

3. **Datenbank migrieren:**

   ```
   uv run python manage.py migrate
   ```

4. **Entwicklungsdaten befüllen.** Der Seed legt Testkonten, einen
   finalen Simulationskern, eine aktive Fake- und eine inaktive OpenAI-Modell-
   Konfiguration, finale Vignetten sowie ein veröffentlichtes und ein
   Entwurfs-Training an. Er ist idempotent und läuft nur mit `DEBUG=True`:

   ```
   uv run python manage.py entwicklungsdaten_anlegen
   ```

   Alle Testkonten teilen das Passwort `entwicklung`:

   | Konto   | Rolle |
   | ------- | ----- |
   | `autor` | alle Rollen (Superuser) |
   | `studi` | ohne Rolle |

5. **Server starten:**

   ```
   uv run python manage.py runserver
   ```

   Die Anwendung ist dann unter http://127.0.0.1:8000/ erreichbar.

Die Testsuite läuft mit `uv run python manage.py test`.

> Der Entwicklungs-Seed aktiviert das Fake-Sprachmodell, damit sich
> Diagnosegespräche ohne API-Schlüssel durchklicken lassen. Für echte Antworten
> muss die OpenAI-Konfiguration mit gesetztem `OPENAI_API_KEY` aktiviert werden.

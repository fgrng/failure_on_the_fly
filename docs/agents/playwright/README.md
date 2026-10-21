# Die App im Browser bedienen

Agenten bedienen FailureOnTheFly mit dem Skill `playwright-cli`: auf der **Produktivinstanz**, um in `docs/` entwickelte Vignetten und Kern-Fassungen einzutragen, und auf dem **Dev-Server**, um Verhalten und Aussehen zu prüfen. Diese Datei gilt für jede Browserarbeit; die Bereiche der App stehen je in einer eigenen Datei (siehe [Bereiche](#bereiche)).

## Instanzen und Sessions

Jede Instanz hat ihre eigene benannte Session mit eigenem, dauerhaftem Profil. Jeder Befehl trägt das `-s=`: ein Befehl ohne Session-Namen trifft die Standard-Session, nicht die gemeinte Instanz.

| Session | Instanz | Adresse | Schreiben |
|---|---|---|---|
| `prod` | Produktivinstanz | <https://onthefly.fgrng.de/> | nur nach Freigabe (siehe [Produktion](#produktion)) |
| `dev` | lokaler Dev-Server | <http://127.0.0.1:8000/> | frei |

`playwright-cli` läuft aus dem Wurzelverzeichnis des Repos: nur dort findet es `.playwright/cli.config.json`, das Chromium wählt. Aus einem anderen Verzeichnis bricht `open` mit «Chromium distribution 'chrome' is not found» ab, und auch die Session-Namen gelten je Verzeichnis: eine aus `/tmp` geöffnete `dev` ist aus dem Repo nicht erreichbar. Dateien wie Screenshots landen trotzdem unter `/tmp` über `--filename`.

Weitere Dev-Sessions für parallele Arbeit oder ein zweites Konto heißen `dev-<zweck>`, etwa `dev-studi`. Eine `prod`-Session gibt es nur einmal.

## Produktion

Auf der Produktivinstanz laufen Trainings und Erhebungen mit echten Teilnehmer:innen. Dort arbeitet ein Agent **lesend** — navigieren, öffnen, Snapshot, Screenshot — und schreibt nur, wenn der User genau diesen Schreibschritt in der laufenden Session freigegeben hat. Schreiben ist jedes Absenden eines Formulars und jeder Knopf, der etwas anlegt, speichert, finalisiert, archiviert, veröffentlicht, startet oder löscht. Welche Schritte nicht umkehrbar sind, steht in der Datei des Bereichs; vor einem solchen Schritt nennt der Agent ihn ausdrücklich als unumkehrbar.

Personenbezogene Daten (Namen, E-Mail-Adressen, Gesprächsverläufe, Abschriften, Exporte) liest ein Agent auf Prod nur, wenn die Aufgabe es verlangt, und schreibt sie weder in Dateien noch ins Repo.

Auf Prod legt ein Agent keine Modell- oder Transkriptions-Konfiguration an und startet keine Evalläufe, Probeläufe oder Sitzungen: sie rufen ein echtes Sprachmodell und kosten Geld.

## Anmelden

Beide Instanzen melden über `/accounts/login/` an; nach der Anmeldung landet die Seite auf `/`, die Navigation links zeigt Konto und Rolle.

**Prod:** Der User meldet sich an, Zugangsdaten bleiben aus dem Gespräch.

1. `playwright-cli -s=prod open https://onthefly.fgrng.de/ --headed --persistent`. Das Profil bleibt erhalten, eine spätere Session ist oft schon angemeldet.
2. Zeigt `playwright-cli -s=prod --raw eval "location.pathname"` nach einem `goto` auf eine geschützte Seite `/accounts/login/`, bittet der Agent den User, sich im sichtbaren Fenster anzumelden und Bescheid zu geben.
3. Angemeldet ist die Session, wenn der Snapshot den Knopf **Abmelden** zeigt.

**Dev:** Der Agent meldet sich selbst an, mit den Testkonten aus dem Seed (`uv run python manage.py entwicklungsdaten_anlegen`, README Schritt 4). Alle teilen das Passwort `entwicklung`; `autor` hat alle Rollen, `studi` keine.

```bash
playwright-cli -s=dev open http://127.0.0.1:8000/accounts/login/ --persistent
playwright-cli -s=dev fill "[name=username]" autor
playwright-cli -s=dev fill "[name=password]" entwicklung --submit
```

Vor dem Öffnen prüft der Agent, ob der Server läuft (`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/`). Läuft er nicht, startet er ihn im Hintergrund mit `uv run python manage.py runserver`. Soll die lokale `db.sqlite3` des Users unberührt bleiben, läuft ein zweiter Server auf einer Wegwerf-Datenbank: `DATABASE_PFAD`, `MEDIA_ROOT`, `FLUECHTIG_PFAD` und `EVALLAEUFE_SPERRE` auf ein Verzeichnis unter `/tmp` setzen, `migrate` und den Seed laufen lassen, dann `runserver 127.0.0.1:8001`.

Der Seed aktiviert das Fake-Sprachmodell nur für die Schüler:in: Gespräche und Probeläufe laufen auf Dev ohne Kosten. Evalläufe brauchen zusätzlich Fake-Konfigurationen für Lehrperson und Bewerter, einen finalen Evalkatalog und einen Abarbeiter; das steht in [evals.md](evals.md). Eine echte Modell-Konfiguration legt ein Agent auch auf Dev nur auf Bitte des Users an.

## Formulare füllen

Die App rendert Django-Formulare: Jedes Eingabefeld trägt als `name` den Feldnamen der Datenbank. Statt Refs aus dem Snapshot zu suchen, füllt ein Agent sichtbare Felder direkt über den Namen:

```bash
playwright-cli -s=dev fill "[name=username]" autor
```

Große Textfelder mit Markdown sind oft versteckt hinter einem Editor; an ihnen bricht `fill` mit Timeout ab. Auch lange Texte mit Anführungszeichen, Backticks oder Zeilenumbrüchen überstehen die Shell nicht zuverlässig. In beiden Fällen setzt der Agent den Wert per `eval` aus einem JSON-String, den ein Skript erzeugt hat (`json.dumps` hält Zeilenumbrüche und Zeichen unverändert). Ein `select` braucht danach ein `change`- statt eines `input`-Events.

```bash
wert=$(uv run python -c 'import json,sys; print(json.dumps(open(sys.argv[1]).read()))' /tmp/feld.txt)
playwright-cli -s=dev --raw eval "(() => { const el = document.querySelector('[name=lernauftrag_text]'); el.value = $wert; el.dispatchEvent(new Event('input', {bubbles: true})); return el.value.length; })()"
```

Nach dem Speichern liest der Agent die gespeicherten Werte zurück (Formular erneut öffnen, `el.value` je Feld) und vergleicht sie mit der Quelle, bevor er die Arbeit als erledigt meldet.

Textfelder mit Markdown zeigen eine Vorschau, die die App über `POST /texte/vorschau/` rendert; die Vorschau speichert nichts.

## Snapshots und Screenshots

Snapshots enthalten viel Struktur ohne Inhalt. Vor dem Lesen filtern:

```bash
playwright-cli -s=dev --raw snapshot | rg -v '^\s*- (generic|group) \[ref=\w+\]:?$'
```

Für das Aussehen macht der Agent einen Screenshot und öffnet das PNG mit `Read`. Vorher die Fenstergröße festlegen, Umbrüche folgen ihr: `resize 1280 800` für Desktop, `resize 390 844` für ein Telefon.

```bash
playwright-cli -s=dev resize 1280 800
playwright-cli -s=dev screenshot --filename=/tmp/pw/start.png
```

Screenshots und Snapshots von Prod gehören nach `/tmp`, nie ins Repo. `.playwright-cli/` (Logs, Snapshots) ist in `.gitignore`.

## Bereiche

Vor dem Arbeiten in einem Bereich liest der Agent dessen Datei:

- [vignetten.md](vignetten.md): Vignetten anlegen, bearbeiten, finalisieren, neue Fassung, Probelauf; Eintragen aus `docs/vignetten/`.
- [simulation.md](simulation.md): Simulationskern und Kern-Fassungen, Eintragen aus `docs/simulation_prompts/`; Modell-Konfiguration, Transkriptions-Konfiguration, Evalkatalog (alles unter `/system/`).
- [evals.md](evals.md): Evalläufe einer Vignette, Urteile korrigieren.
- [training.md](training.md): Trainings anlegen und verwalten, Beitritt, Fremdeinsicht, Export, Abschriften.
- [sitzungen.md](sitzungen.md): eine Sitzung als Teilnehmer:in durchlaufen, vom Einstieg bis zum Debrief.
- [erhebungen.md](erhebungen.md): Erhebungen verwalten, Teilnahme, Einsicht.
- [fragebogen_items.md](fragebogen_items.md): Fragebogen-Items verwalten.

Das erwartete Verhalten je Bereich beschreibt `docs/verhalten.md`; weicht die App davon ab, meldet der Agent die Abweichung, statt die Doku an die App anzupassen.

# Vignetten

Der Vignetteneditor unter `/vignetten/`: Vignetten anlegen, bearbeiten, durch den Lebenszyklus führen und im Probelauf spielen. Hauptanwendungsfall ist, eine in `docs/vignetten/*.md` entwickelte Vignette auf der Produktivinstanz <https://onthefly.fgrng.de/> einzutragen. Sessions, Anmeldung, Prod-Regeln, das Füllen per `[name=…]` und das eval/JSON-Muster stehen in [README.md](README.md) und gelten hier unverändert. Das erwartete Verhalten steht in `docs/verhalten.md`, Abschnitt «Vignetten verwalten».

## Seiten

| URL | Methode | Was |
|---|---|---|
| `/vignetten/` | GET | »Meine Vignetten«: je Historie eine Zeile, immer die **neueste** Fassung |
| `/vignetten/anlegen/` | GET/POST | Formular; POST legt einen neuen Entwurf mit neuer Historie an |
| `/vignetten/<pk>/` | GET | Detailansicht mit den Aktionsknöpfen des Zustands |
| `/vignetten/<pk>/bearbeiten/` | GET/POST | Formular, nur für Entwürfe (sonst 404) |
| `/vignetten/<pk>/finalisieren/`, `/vorspulen/` | POST | nur Entwurf |
| `/vignetten/<pk>/neue-fassung/`, `/archivieren/` | POST | nur final |
| `/vignetten/<pk>/entarchivieren/` | POST | nur archiviert |
| `/vignetten/<pk>/eigentuemerinnen/hinzufuegen/` | POST | Feld `konto` (Konto-pk) |
| `/sitzungen/probelauf/<pk>/starten/` | POST | Probelauf über diese Fassung |

`<pk>` ist die Fassung, nicht die Historie: Jede neue Fassung bekommt einen neuen pk. Alle Lebenszyklus-Knöpfe sind kleine Formulare ohne Rückfrage; ein Klick schreibt sofort. Ansprechen lassen sie sich über ihr Ziel, etwa `click "form[action\$='/finalisieren/'] button"`. Fehlermeldungen erscheinen nach der Weiterleitung oben in `main` (`ul.messages`).

## Rollen und Sichtbarkeit

- Alle Seiten verlangen die Rolle Autor:in; ohne sie antworten sie mit 403 (belegt mit `studi`). Administrator:innen gelten immer auch als Autor:in.
- Eine Autor:in sieht nur Vignetten aus Historien, in deren Eigentümer-Kreis sie steht; fremde pks antworten mit 404. **Administrator:innen sehen alle Vignetten aller Autor:innen** und können sie auch bearbeiten und finalisieren (aus dem Code). Auf Prod also vor jedem Schreiben prüfen, dass die Fassung zur Aufgabe gehört.
- Den Kreis pflegt der Abschnitt »Eigentümer:innen« der Detailansicht; er hängt an der Historie und gilt für alle Fassungen (aus Code und `verhalten.md`, nicht durchgespielt).

## Lebenszyklus

Entwurf → final → archiviert, je Historie höchstens ein Entwurf.

- **Anlegen** erzeugt Historie und Entwurf und pinnt die neueste finale Kern-Fassung. Gibt es keine, legt das Formular nichts an und nennt den Grund.
- **Entwurf bearbeiten** speichert alle Felder auf einmal; beliebig oft.
- **Auf aktuellen Kern vorspulen** pinnt den Entwurf auf die neueste finale Kern-Fassung. Zurück auf einen älteren Kern geht es nicht. Die Detailansicht zeigt den Pin unter »Gesprächsbudget« als »Gepinnter Simulationskern: <pk>«.
- **Finalisieren** prüft die Pflichtfelder und friert die Fassung ein: Fehlermuster-Beschreibung, Vorname der Schüler:in, Lehrperson-Nachname, Fach, Thema, Klassenstufe, Budget-Typ, Budget-Wert > 0, je Lernauftrag und Arbeitsheft Text oder Bild, zu jedem Bild eine Bildbeschreibung. Fehlt etwas, bleibt der Entwurf und oben steht etwa »Zum Finalisieren fehlen: Fehlermuster-Beschreibung, Fach, Thema, Klassenstufe, Budget-Typ.«. Der Evallauf-Hinweis über dem Knopf sperrt nichts (Evals: [evals.md](evals.md)).
- **Neue Fassung** (an einer finalen Fassung) legt einen Entwurf mit allen Feldern, Bildern und dem Kern-Pin der Vorgängerin an und leitet auf ihn um. Gibt es in der Historie schon einen Entwurf, leitet sie nur auf diesen um. Hat die finale Fassung eine nicht archivierte Nachfolgerin, fehlt der Knopf.
- **Archivieren** (final) nimmt die Fassung aus dem Spiel: kein neuer Probelauf, keine neue Einbindung, und sie **wird aus allen Trainings entfernt**, in denen sie steckt. **Entarchivieren** macht sie wieder final, aber nur, solange ihre Vorgängerin keine andere nicht archivierte Nachfolgerin hat; die Trainings-Mitgliedschaft kommt dabei nicht zurück.

**Unumkehrbar** sind: Anlegen (die UI kann Entwürfe nicht löschen, ein versehentlicher Entwurf bleibt in der Liste), Finalisieren (die Fassung ist danach unveränderlich; Korrekturen nur über Neue Fassung, die wieder finalisiert werden muss), Neue Fassung (der Entwurf bleibt), Vorspulen, und beim Archivieren das Entfernen aus Trainings. Auf Prod nennt der Agent diese Schritte vor der Freigabe ausdrücklich als unumkehrbar.

## Das Formular

Anlegen und Bearbeiten teilen ein Formular `#vignette-formular` (`multipart/form-data`). Absenden: `click ".vignette-form-actions button[type=submit]"` (»Vignette anlegen« bzw. »Änderungen speichern«); danach steht die Seite auf `/vignetten/<pk>/`.

Jedes Feld trägt als `name` exakt den Datenbank-Feldnamen und damit exakt die `##`-Überschrift der md-Dateien:

| `name` | Element | Hinweis |
|---|---|---|
| `fach`, `thema` | input text | Autovervollständigung aus den Werten **finaler** Vignetten; Liste lesen: `JSON.parse(document.getElementById('fach-werte').textContent)` bzw. `thema-werte` |
| `klassenstufe` | input text | freier Text; die Rahmenhandlung schreibt »Klassenstufe <wert>«, also nur die Zahl (`9`) |
| `schuelerin_name`, `lehrperson_name` | input text | beim Anlegen zufällig vorbelegt (Mia/Noah, Weber/Koch): immer überschreiben |
| `schuelerin_geschlecht`, `lehrperson_geschlecht` | select | Werte `weiblich`, `männlich`; zufällig vorbelegt |
| `lernauftrag_text`, `arbeitsheft_text` | textarea, **versteckt** | Markdown im Profil Szenentext |
| `lernauftrag_simulationshinweise`, `arbeitsheft_simulationshinweise`, `fehlermuster_beschreibung`, `referenzdiagnose` | textarea, **versteckt** | reiner Text |
| `lernauftrag_bild`, `arbeitsheft_bild` | input file | siehe [Bilder](#bilder) |
| `lernauftrag_bildbeschreibung`, `arbeitsheft_bildbeschreibung` | textarea, sichtbar | |
| `budget_typ` | select | Werte `schritte`, `zeit` (kleingeschrieben; die Beschriftung ist »Schritte«) |
| `budget_wert` | input number | Schritte bzw. Sekunden |

Nicht im Formular: Zustand, Kern-Pin (nur über Anlegen und Vorspulen) und der Historienname. Die Liste zeigt ohne Namen »Fach: Thema (Klasse N)«; die UI kann keinen Namen setzen. Mehrere Vignetten mit gleichem Fach, Thema und Klasse sehen in der Liste gleich aus, unterscheiden lassen sie sich nur über den pk.

Die sechs großen Texte stehen in einer Lese-Hülle und sind zugeklappt. `playwright-cli fill` wartet dort auf Sichtbarkeit und bricht mit Timeout ab; diese Felder setzt der Agent per `eval` (`el.value = …`). Die Hülle zeigt danach weiter den alten Lesetext, gesendet wird trotzdem der neue Wert.

## Eine Vignette aus `docs/vignetten/` eintragen

Belegt auf Dev mit `lu11-02-umkehr-rezept-ohne-stellung-von-x.md`: angelegt, zurückgelesen ohne Abweichung, Probelauf, finalisiert, neue Fassung, archiviert, entarchiviert.

**1. md parsen.** `scripts/simulieren.py` hat den Parser `vignette_lesen(text) -> dict[str, str]` (alle 19 Felder, fehlende leer, eingerückte Blöcke samt Einrückung der ersten Zeile; ein umzäunter Codeblock bricht ab). Was nach einer Trennlinie `---` hinter dem letzten Feld steht (»Warum simulierbar«), lässt er weg, und `budget_typ` liefert er als Wert der Datenbank (`schritte`, nicht `Schritte`).

```bash
uv run python -c '
import json, sys
sys.path.insert(0, "scripts")
from pathlib import Path
from simulieren import vignette_lesen
f = vignette_lesen(Path(sys.argv[1]).read_text())
f = {k: v for k, v in f.items() if not k.endswith("_bild")}
Path("/tmp/pw/felder.json").write_text(json.dumps(f, ensure_ascii=False))
print({k: len(v) for k, v in f.items()})
' docs/vignetten/<datei>.md
```

Vorher die Felder mit der md vergleichen: Hat die md Bildfelder, gehören die Bilder per Upload dazu; fehlt ein Pflichtfeld, scheitert später das Finalisieren.

**2. Prüfen, ob es die Vignette schon gibt.** In `/vignetten/` nach Fach und Thema suchen und Kandidaten öffnen. Gibt es schon einen Entwurf derselben Vignette, wird dieser bearbeitet statt neu angelegt (Entwürfe lassen sich nicht löschen). Auf Prod: Werte von `fach-werte`/`thema-werte` lesen und Schreibweisen mit dem User abgleichen.

**3. Felder füllen.** Auf `/vignetten/anlegen/` (oder `/vignetten/<pk>/bearbeiten/`) alle Felder in einem `eval` setzen; `change` braucht es für die Selects:

```bash
felder=$(cat /tmp/pw/felder.json)
playwright-cli -s=dev --raw eval "(() => { const f = $felder; const fehlt = []; for (const [n, v] of Object.entries(f)) { const el = document.querySelector('#vignette-formular [name=' + n + ']'); if (!el) { fehlt.push(n); continue; } el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); } return JSON.stringify({fehlt, gleich: Object.keys(f).filter(n => document.querySelector('[name=' + n + ']')?.value === f[n]).length}); })()"
```

`gleich` muss der Zahl der Felder entsprechen; ein Select mit unbekanntem Wert bleibt sonst stumm leer.

**4. Als Entwurf speichern.** Prod: Freigabe für »Vignette anlegen« einholen (unumkehrbar, siehe oben). Dann `click ".vignette-form-actions button[type=submit]"`; `location.pathname` ist danach `/vignetten/<pk>/`, das Abzeichen zeigt »Entwurf«. Den pk notieren.

**5. Zurücklesen und vergleichen.** `goto /vignetten/<pk>/bearbeiten/` und dasselbe JSON gegen die gespeicherten Werte prüfen; das Ergebnis muss `[]` sein:

```bash
playwright-cli -s=dev --raw eval "(() => { const f = $felder; return JSON.stringify(Object.keys(f).filter(n => document.querySelector('#vignette-formular [name=' + n + ']').value !== f[n])); })()"
```

Danach die Detailseite lesen: Lernauftrag und Arbeitsheft erscheinen gerendert, wie die Teilnehmer:in sie sieht. Bei Heftinhalten mit Ausrichtung einen Screenshot machen (siehe [Fallstricke](#fallstricke)).

**6. Probelauf.** Auf der Detailansicht `click "form[action\$='/probelauf/<pk>/starten/'] button"`. Die Seite zeigt Rahmenhandlung, Lernauftrag, Arbeitsheft und das Eingabefeld `[name=eingabe]`; Senden im Formular `/sitzungen/probelauf/gespraech/`, Ende über `/sitzungen/probelauf/beenden/` (Ablauf: [sitzungen.md](sitzungen.md)). Auf Dev antwortet das Fake-Sprachmodell immer gleich, der Probelauf prüft dort nur Darstellung und Ablauf. Auf Prod startet der Agent keinen Probelauf (README); er nennt dem User den pk und überlässt ihm den Probelauf.

**7. Finalisieren nur nach Freigabe.** Erst wenn der User den Entwurf geprüft und das Finalisieren freigegeben hat: Pin unter »Gesprächsbudget« nennen (ein überholter Pin ist erlaubt, Vorspulen ist eine eigene Entscheidung), dann `click "form[action\$='/finalisieren/'] button"`. Erfolgreich, wenn das Abzeichen »Final« zeigt und die Knöpfe »Probelauf starten«, »Neue Fassung«, »Archivieren« lauten; sonst die Meldung in `ul.messages` lesen.

Eine überarbeitete md für eine schon finale Vignette: an der finalen Fassung »Neue Fassung«, dann ab Schritt 3 auf `/vignetten/<neuer pk>/bearbeiten/`.

## Bilder

Upload ist belegt: Erst das Label der Bildkarte klicken, das öffnet den Dateidialog, dann hochladen:

```bash
playwright-cli -s=dev click "label[for=id_arbeitsheft_bild]"
playwright-cli -s=dev upload /pfad/zum/bild.png
playwright-cli -s=dev fill "[name=arbeitsheft_bildbeschreibung]" "…"
```

Gespeichert wird unter einem neuen Zufallsnamen (`/media/vignettenbilder/<hex>.png`); der Dateiname der md bleibt nicht erhalten. Zurücklesen über `[...document.querySelectorAll('.bildkarte')].map(b => b.dataset.gespeichert)` (Reihenfolge Lernauftrag, Arbeitsheft; leer heißt kein Bild). Ohne `[bild]` allein auf einer Zeile im Text steht das Bild unter dem Text. Ein Formularfehler beim Speichern verwirft die gewählte Datei.

## Fallstricke

- **Heftinhalte mit Spalten.** Die md-Dateien schreiben sie als eingerückten Block (jede Zeile mit vier Leerzeichen); die App zeigt ihn in Festbreitenschrift mit Spalten und Einrückung. Das Formular behält die Einrückung der ersten Zeile, das eval/JSON-Muster überträgt sie unverändert. Fließtext ohne Einrückung fasst mehrere Leerzeichen zu einem zusammen, ```` ``` ````-Zäune erscheinen wörtlich. Nach dem Speichern prüfen, dass `arbeitsheft_text` mit vier Leerzeichen beginnt, und die Vorschau ansehen. Vorschau ohne Speichern: `fetch('/texte/vorschau/', {method: 'POST', body: new URLSearchParams({profil: 'szenentext', quelle, csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value})}).then(r => r.text())`.
- **Warnung beim Verlassen.** Weicht ein Feld vom geladenen Stand ab, öffnet `goto` einen `beforeunload`-Dialog; jeder weitere Befehl scheitert mit »does not handle the modal state«. `dialog-accept` verlässt die Seite und verwirft die Änderungen, `dialog-dismiss` bleibt. Absenden löst keinen Dialog aus. Auf einem Entwurf mit gespeichertem Bild kommt der Dialog auch ohne Änderung, weil das Dateifeld den gespeicherten Pfad als `value`-Attribut trägt (Fehler der App, Stand 2026-10-21); dort nach dem Speichern immer `dialog-accept` erwarten.
- **Neueste Fassung in der Liste.** Nach »Neue Fassung« zeigt die Liste nur den Entwurf; die finale Vorgängerin ist nur noch über ihren pk erreichbar, die Detailansicht des Entwurfs verlinkt sie nicht.
- **Zufällige Akteure.** Wer beim Anlegen Namen oder Geschlecht nicht setzt, speichert die Zufallsvorbelegung.
- **Kern zwischen Anlegen und Finalisieren.** Wird inzwischen ein neuer Kern finalisiert, zeigt die Detailansicht beim Entwurf einen Hinweis auf den überholten Pin; finalisieren geht trotzdem.

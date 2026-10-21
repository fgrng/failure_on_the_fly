# Simulation (System)

Die App `simulation/` unter `/system/`: Simulationskern mit seinen Kern-Fassungen, Modell-Konfiguration, Transkriptions-Konfiguration und Evalkatalog. Sessions, Anmeldung, Prod-Regeln, Formulare über `[name=…]` füllen, lange Texte per `eval` und Snapshots stehen in [README.md](README.md) und werden hier vorausgesetzt. Das erwartete Verhalten beschreibt `docs/verhalten.md`, Abschnitte «Simulationskern», «Modell-Konfiguration», «Evalkatalog» und «Transkriptions-Konfiguration».

Beispiele nutzen `-s=dev` und <http://127.0.0.1:8000/>; auf Prod dieselben Pfade unter <https://onthefly.fgrng.de/> mit `-s=prod`.

## Rollen

Alles hier ist Administration, also ein Django-Superuser (ADR-0033). Einzige Ausnahme: `/system/kern/` (finale Fassung und Modell der Schüler:in, nur lesen) sehen auch Autor:innen. Auf Dev ist `autor` Superuser.

## Seiten

| Pfad | Inhalt |
|---|---|
| `/system/kern/` | finale Kern-Fassung, schreibgeschützt |
| `/system/kern/verwalten/` | Entwurf, finale Fassung, eingeklappt «Archivierte Fassungen»; alle Kern-Aktionen |
| `/system/kern/<pk>/bearbeiten/` | Formular des Entwurfs; 404 für jede andere Fassung |
| `/system/modell-konfiguration/` (`?konfiguration=<pk>` wählt eine Zeile) | Liste und Detail der Sprachmodell-Konfigurationen |
| `/system/modell-konfiguration/neu/` (`?vorlage=<pk>`) | Editor einer neuen Konfiguration |
| `/system/transkription/` (`?fassung=<pk>`) | Liste, Detail und Formular einer neuen Fassung |
| `/system/evalkatalog/` | Übersicht der Evalkatalog-Linie |
| `/system/evalkatalog/<pk>/` | Editor (Knoten «Durchlauf und Vorlagen»), Unterknoten `kriterien/`, `evals/<id>/`, `evals/<id>/inputs/<id>/` |
| `/sitzungen/probelauf/administratorin/` | freier Probelauf; die Auswahl `kern_pk` führt jede Kern-Fassung, auch den Entwurf |

Keine der Aktionen auf diesen Seiten fragt nach: Finalisieren, Verwerfen, Aktivieren gehen beim ersten Klick durch. Speichern, Finalisieren und Verwerfen am Kern zeigen keine Erfolgsmeldung, nur Fehler stehen als `ul.messages li` oben; den Erfolg liest der Agent am Zustand ab (siehe unten).

## Kern-Fassungen

Eine Kern-Fassung hat fünf Inhaltsfelder, im Formular von `/system/kern/<pk>/bearbeiten/` (`form#kern-formular`) unter diesen `name`s:

| `name` | Bezeichnung | Erlaubte Platzhalter |
|---|---|---|
| `rahmenhandlung_einleitung` | Hospitationseinleitung | Rahmenvertrag |
| `rahmenhandlung_gespraechseinleitung` | Gesprächseinleitung | Rahmenvertrag |
| `rahmenhandlung_debrief` | Debrief | Rahmenvertrag |
| `system_prompt_vorlage` | System-Prompt-Vorlage | Promptvertrag |
| `user_prompt_vorlage` | User-Prompt-Vorlage (Altfeld, ADR-0052) | Promptvertrag |

- **Promptvertrag** (`VERTRAG_PROMPT` in `simulation/models.py`): `$fehlermuster_beschreibung`, `$lernauftrag`, `$lernauftrag_simulationshinweise`, `$arbeitsheft`, `$arbeitsheft_simulationshinweise`, `$schuelerin_name`, `$schuelerin_geschlecht`, `$lehrperson_name`, `$lehrperson_anrede`, `$fach`, `$thema`, `$klassenstufe`.
- **Rahmenvertrag** (`VERTRAG_RAHMEN`): `$schuelerin_name`, `$schuelerin_geschlecht`, `$lehrperson_name`, `$lehrperson_geschlecht`, `$fach`, `$thema`, `$klassenstufe`, `$schuelerin_pronomen`, `$schuelerin_possessiv`, `$lehrperson_pronomen`, `$lehrperson_possessiv`, `$lehrperson_anrede`.

`$lehrperson_geschlecht`, `$lehrperson_pronomen`, `$lehrperson_possessiv` und die Pronomen und Possessive der Schüler:in gehören nur zum Rahmenvertrag, nicht in eine Prompt-Vorlage.

Was der Code nicht von selbst sagt:

- Die Textareas stehen in einer Lese-Hülle und sind versteckt (`x-show`), bis «Bearbeiten» geklickt ist. Setzen per `eval` auf `[name=…]` geht trotzdem, ohne die Hülle zu öffnen.
- `user_prompt_vorlage` fehlt im Formular, solange der Entwurf sie leer hat; dann lässt das Speichern sie unberührt. Steht sie im Formular (Altfassung mit gefülltem Feld), muss der Agent sie ausdrücklich auf `""` setzen, wenn die Quelle sie leer will.
- Jeder Speichern-Knopf sendet das ganze Formular. Der Knopf unten heißt «Änderungen speichern» (`#kern-formular .vignette-form-actions button[type=submit]`); Erfolg leitet auf `/system/kern/verwalten/` um.
- **Platzhalterprüfung beim Speichern** (`Simulationskern.clean`): ein `$` vor etwas anderem als einem Bezeichner (etwa `$5`, `$ `) oder ein Platzhalter außerhalb des Vertrags lässt das Speichern scheitern. Die Seite bleibt auf `/bearbeiten/`, das betroffene Feld steht offen mit «Enthält ungültige Platzhalter.», ohne den Platzhalter zu nennen; gespeichert ist nichts. Ein wörtliches Dollarzeichen schreibt sich `$$`. Finalisieren prüft dasselbe noch einmal.
- Das Speichern trimmt Leerraum am Anfang und Ende und legt Zeilenumbrüche als `\r\n` ab (vom Browser gesendet, auf Dev in der Datenbank gesehen). Im Formular und in `/system/kern/` erscheinen sie wieder als `\n`; der Vergleich mit der Quelle läuft deshalb über den Feldwert, nicht über die Datenbank.

### Lebenszyklus

Entwurf → final → archiviert (ADR-0035, ADR-0040). Je Instanz gibt es höchstens einen Entwurf und genau eine finale Fassung.

| Knopf auf `/system/kern/verwalten/` | Route (POST) | Wirkung | Umkehrbar |
|---|---|---|---|
| «Entwurf ziehen» (an der finalen Fassung) | `/system/kern/<final>/neue-fassung/` | neuer Entwurf als Kopie aller fünf Felder der finalen Fassung | ja, per Verwerfen |
| «Bearbeiten» (am Entwurf) | Link auf `/system/kern/<entwurf>/bearbeiten/` | — | — |
| «Finalisieren» (am Entwurf) | `/system/kern/<entwurf>/finalisieren/` | Entwurf wird final, die bisherige finale Fassung archiviert | **nein** |
| «Verwerfen» (am Entwurf) | `/system/kern/<entwurf>/verwerfen/` | löscht den Entwurf physisch | **nein**, sein Inhalt ist weg |
| «Neuen Entwurf anlegen» / «Standardkern als Entwurf anlegen» | `/system/kern/anlegen/`, `…/anlegen/standard/` | nur solange es gar keine Fassung gibt | ja, per Verwerfen |

«Entwurf ziehen» steht auch dann an der finalen Fassung, wenn schon ein Entwurf besteht; der Klick ergibt dann «Ein Kern-Entwurf existiert bereits.». Eine archivierte Fassung kommt nicht zurück; eine misslungene finale Fassung ersetzt nur eine neue. Laufende Sitzungen und Vignetten auf der alten Fassung bleiben unberührt (siehe `docs/verhalten.md`).

Die Knöpfe gezielt treffen, nicht über Refs: Auf der Seite stehen Entwurf und finale Fassung untereinander, jeweils mit eigenen Formularen.

```bash
playwright-cli -s=dev --raw eval "[...document.querySelectorAll('form[action^=\"/system/kern/\"]')].map(f => f.getAttribute('action')).join(' ')"
playwright-cli -s=dev --raw eval "document.querySelector('form[action=\"/system/kern/7/finalisieren/\"] button').click()"
```

Zustand ablesen: Die Überschriften `h2` heißen «Entwurf», «Finale Fassung», die Aktionsformulare tragen die `pk` im `action`. Nach dem Ziehen erscheint `…/<neu>/finalisieren/` und `…/<neu>/verwerfen/`; nach dem Finalisieren bleibt nur `…/<neu>/neue-fassung/`.

## Prompt-Entwurf aus `docs/simulation_prompts/` eintragen

Ein Entwurf in `docs/simulation_prompts/*.md` deckt **nur die System-Prompt-Vorlage** ab: Sie steht als Codeblock ```` ```text ```` (in älteren Dateien mit vier Backticks) unter `## System-Prompt-Vorlage`. `## User-Prompt-Vorlage` sagt «Leer.», die Rahmenhandlung fehlt in den Dateien. Diese drei Felder bleiben so, wie «Entwurf ziehen» sie aus der finalen Fassung kopiert, außer die Datei oder der User sagt etwas anderes. Alles andere in der Datei (Überarbeitung, Probelauf) ist Dokumentation.

`vorlage_lesen` in `scripts/simulieren.py` zieht den Block heraus, mit drei oder vier Backticks; findet es keinen, nimmt es stillschweigend die ganze Datei. Zum Eintragen deshalb so, mit Abbruch, wenn kein Block da ist:

```bash
uv run python -c 'import sys; sys.path.insert(0, "scripts"); from simulieren import vorlage_lesen; t = open(sys.argv[1], encoding="utf-8").read(); v = vorlage_lesen(t); sys.exit("kein text-Block unter ## System-Prompt-Vorlage") if v == t else open(sys.argv[2], "w", encoding="utf-8").write(v)' docs/simulation_prompts/2026-10-21-systemprompt.md /tmp/pw/system_prompt_vorlage.txt
```

Andere `text`-Blöcke, etwa die Vorlagen in `docs/evals/katalog.md` (siehe [Evalkatalog](#evalkatalog)), zieht dieses allgemeine Muster heraus:

```bash
uv run python -I -c 'import re,sys; t=open(sys.argv[1],encoding="utf-8").read(); m=re.search(r"^## "+re.escape(sys.argv[2])+r"[ \t]*\n+(`{3,})text\n(.*?)\n\1[ \t]*$", t, re.S|re.M); sys.exit("kein text-Block unter ## "+sys.argv[2]) if not m else open(sys.argv[3],"w",encoding="utf-8").write(m.group(2))' <datei> <überschrift> <ziel>
```

Ablauf (auf Prod jeder Schreibschritt nur nach Freigabe, siehe README):

1. **Platzhalter vorab prüfen**, weil die App den falschen nicht nennt. Ein Rest außer `[]` heißt: Die App lehnt die Vorlage ab; dem User melden, nicht selbst umschreiben.

   ```bash
   uv run python manage.py shell -c 'from string import Template; from simulation.models import VERTRAG_PROMPT; t = Template(open("/tmp/pw/system_prompt_vorlage.txt", encoding="utf-8").read()); print(t.is_valid(), sorted(set(t.get_identifiers()) - VERTRAG_PROMPT))'
   ```

2. Auf `/system/kern/verwalten/` prüfen, dass kein Entwurf besteht (`h2` «Entwurf» fehlt). Besteht einer, gehört er jemandem; nicht verwerfen, sondern den User fragen. Sonst «Entwurf ziehen» (Schreibschritt) und die neue `pk` aus `…/<pk>/bearbeiten/` ablesen.
3. `/system/kern/<pk>/bearbeiten/` öffnen, `system_prompt_vorlage` per `eval` aus JSON setzen (README, «Formulare füllen»). Die Platzhalter bleiben dabei wörtlich als `$name` stehen, nicht ersetzen und nicht umbrechen. Steht `[name=user_prompt_vorlage]` im Formular, auf `""` setzen.
4. «Änderungen speichern» klicken (Schreibschritt). Landet die Seite auf `/system/kern/verwalten/`, ist gespeichert; bleibt sie auf `/bearbeiten/`, `.errorlist` lesen.
5. **Zurücklesen und vergleichen**: `/system/kern/<pk>/bearbeiten/` erneut öffnen und den Feldwert gegen die Quelle prüfen. `--raw eval` gibt den Wert als JSON-String aus:

   ```bash
   playwright-cli -s=dev --raw eval "document.querySelector('[name=system_prompt_vorlage]').value" > /tmp/pw/zurueck.json
   uv run python -I -c 'import json,sys; z=json.load(open(sys.argv[1])); q=open(sys.argv[2],encoding="utf-8").read().strip(); print("gleich" if z==q else f"abweichend: {len(z)} statt {len(q)} Zeichen")' /tmp/pw/zurueck.json /tmp/pw/system_prompt_vorlage.txt
   ```

   Gleich zu prüfen: `[name=user_prompt_vorlage]` fehlt oder ist leer, die drei Rahmenhandlungsfelder sind wie in der finalen Fassung.
6. Prüfen im Probelauf: Die Dateien verlangen ihn vor dem Finalisieren. Auf Dev unter `/sitzungen/probelauf/administratorin/` mit `kern_pk` = Entwurf und dem Fake-Modell; auf Prod startet ihn nur der User (echtes Modell, kostet).
7. **Finalisieren nur nach ausdrücklicher Freigabe** und mit dem Hinweis, dass es unumkehrbar ist und die bisherige finale Fassung archiviert. Danach `/system/kern/` öffnen und den Inhalt von `pre` unter «System-Prompt-Vorlage» genauso gegen die Quelle vergleichen.

## Modell-Konfiguration

Ein Agent liest hier nur: Liste mit Bezeichnung, Anbieter, Anlagedatum, Zero-Retention-Stand und den Kürzeln S/L/B für die aktiven Verwendungen; das Detail einer Zeile über `?konfiguration=<pk>` mit Sprachmodell, Basis-URL, maskiertem Token («Kein Token hinterlegt.» oder Punkte plus letzte vier Zeichen) und Parametern. Geht es nur um die aktive Konfiguration der Schüler:in, reicht `/system/kern/`.

Konfigurationen sind unveränderlich (append-only, ADR-0056): Es gibt kein Bearbeiten und Löschen, nur Anlegen über `/system/modell-konfiguration/neu/` (Felder `bezeichnung`, `anbieter`, `anbieter_token`, `anbieter_basis_url`, `sprachmodell`, `parameter`, `zero_retention_erklaert`, `zero_retention_beleg`), Aktivieren je Verwendung (POST `/system/modell-konfiguration/<pk>/aktivieren/schuelerin|lehrperson|bewerter/`, ohne Rückfrage) und Abgeben oder Widerrufen der Zero-Retention-Erklärung. Erklärung und Widerruf sind unumkehrbar, ein Widerruf sperrt die Konfiguration für jede weitere Aktivierung.

Ein Agent trägt nie ein Token ein, legt auf Prod keine Konfiguration an und aktiviert, erklärt oder widerruft nichts; auf Dev nur auf Bitte des User (README). Der Knopf «Modelle und Basis-URL laden» ruft den Anbieter von außen ab (`/system/modellvorschlaege/`); ihn braucht ein Agent nicht.

## Transkriptions-Konfiguration

Lesen wie bei der Modell-Konfiguration: Liste mit Nummer, Anbieter, Modell, Anlagedatum, Zero-Retention-Stand und «aktiv»; Detail über `?fassung=<pk>` mit Sprache, Basis-URL und maskiertem Token. Der Kopf meldet «Die Spracheingabe ist aus.», solange die aktive Fassung `fake` oder nicht erklärt ist; auf Dev ist das der Normalfall.

Fassungen sind append-only bis auf eine Ausnahme: «Token ersetzen» im Detail (POST `/system/transkription/<pk>/token/`) tauscht das Token einer bestehenden Fassung in place, ohne neue Fassung; das alte Token ist danach weg. Das Formular einer neuen Fassung unter der Liste (`anbieter`, `anbieter_token`, `anbieter_basis_url`, `transkriptionsmodell`, `sprache`, `zero_retention_erklaert`, `zero_retention_beleg`) ist mit der aktiven vorbelegt, und ein leeres Tokenfeld übernimmt deren Token. Für den Agenten gilt dasselbe wie oben: nur lesen, kein Token, kein Anlegen, Aktivieren, Erklären, Widerrufen.

## Evalkatalog

Eine Linie mit höchstens einem Entwurf und genau einer finalen Fassung (ADR-0046). Die Übersicht `/system/evalkatalog/` bietet je nach Stand «Evalkatalog anlegen», «Entwurf bearbeiten» und «Entwurf verwerfen», oder «Finale Fassung lesen» und «Neue Fassung» (POST `…/<final>/neue-fassung/`, Tiefenkopie). Finale und überholte Fassungen öffnen sich im selben Editor mit gesperrten Feldern. «Finalisieren» macht die bisherige finale Fassung **unumkehrbar** überholt; «Entwurf verwerfen» löscht den Entwurf. Ab dem Finalisieren prüft jeder Evallauf gegen die neue Fassung. Evalläufe selbst: [evals.md](evals.md).

Der Editor ist ein Baum; jeder Knoten hat eine eigene Adresse und eigene Formularnamen, `<id>` ist die Datenbank-`pk` des Objekts:

| Knoten | Pfad | Felder |
|---|---|---|
| Durchlauf und Vorlagen | `/system/evalkatalog/<pk>/` | `k`, `lehrperson_vorlage`, `bewerter_vorlage` |
| Übergreifende Kriterien | `…/<pk>/kriterien/` | `kriterium-<id>` je Kriterium |
| Eval | `…/<pk>/evals/<eval>/` | `eval-<eval>` (Name, höchstens 200 Zeichen), `evalkriterium-<id>` |
| Evalinput | `…/<pk>/evals/<eval>/inputs/<input>/` | je Inputschritt `inputschritt-<id>` (Text) und Radio `inputschritt-art-<id>` mit `fest` oder `gelenkt` |

Hinzufügen, Löschen und Hoch/Runter sind POST-Knöpfe am Knoten («Kriterium hinzufügen», «Eval hinzufügen», «Evalinput hinzufügen», «Inputschritt hinzufügen», Papierkorb, Pfeile); jeder übernimmt zugleich alle getippten Werte des Formulars. Ein neuer Evalinput startet mit drei leeren festen Schritten. Die Vorlagen prüft erst «Finalisieren»; es nennt jede Lücke als eigene Meldung (leere Vorlage, Platzhalter außerhalb des Vertrags, *k* < 1, Eval ohne Kriterium oder Input, leerer Schritt …).

`docs/evals/` spiegelt diese Felder (Format: `docs/evals/README.md`): `katalog.md` trägt `## k`, `## lehrperson_vorlage`, `## bewerter_vorlage` (je ein ```` ```text ````-Block, mit dem Befehl oben herausziehbar); `allgemeine_kriterien.md` die übergreifenden Kriterien; jede `eval-*.md` ein Eval mit `## name`, `## kriterien` und `## inputs` (`###` je Evalinput, Schritte `fest:` / `gelenkt:`). Der Text eines Kriteriums in der App ist nicht der rohe Markdown: Ein übergreifendes Kriterium ist «Name: Beschreibung» ohne `## Hintergrund`, ein Evalkriterium der Listenpunkt ohne Nummer, beides mit Leerraum auf ein Leerzeichen zusammengezogen. Die Skripte liefern genau diese Texte:

```bash
uv run python -c '
import json, sys; sys.path[:0] = ["scripts"]
from pathlib import Path
from bewerter_prompt import allgemeine_kriterien_lesen, kriterien_lesen
from evalgespraech import inputs_lesen
e = Path("docs/evals/eval-01-vorgehen-erfragen.md").read_text()
json.dump({"uebergreifend": [t for _, t in allgemeine_kriterien_lesen(Path("docs/evals/allgemeine_kriterien.md").read_text())],
           "evalkriterien": [t for _, t in kriterien_lesen(e, "kriterien")],
           "inputs": inputs_lesen(e)}, open("/tmp/pw/eval-01.json", "w"), ensure_ascii=False, indent=1)'
```

Eintragen ist dann: neue Fassung ziehen, je Knoten die Anzahl der Einträge per Hinzufügen/Papierkorb angleichen, die Felder per `eval` aus dieser JSON setzen, «Änderungen speichern», zurücklesen wie beim Kern. Der Evalkatalog-Teil dieser Datei ist aus Code, Templates und einem lesenden Durchgang auf Dev belegt (Formularnamen aus dem Editor einer finalen Fassung); Schreiben im Editor und Finalisieren sind auf Dev **nicht** durchgespielt.

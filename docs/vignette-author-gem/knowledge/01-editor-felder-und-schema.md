# Editor-Felder & Schema

Diese Datei beschreibt die Felder des Vignetten-Editors **genau so, wie sie im
Formular erscheinen** (`vignetten/forms.py`, `VignetteForm`). Die feldweise
Ausgabe des Co-Autors muss diese Labels und diese Reihenfolge spiegeln, damit
Autor:innen sie direkt übertragen können.

Der Editor kennt **keine** Abschnitte: Er zeigt die fünfzehn Felder als eine
Liste in der unten genannten Reihenfolge. Es gibt keine ID, keine Kurzangabe,
keine erwartete Bearbeitung, kein Schülerprofil-Freitextfeld, keine
Artefaktverwaltung mit Bereichen und keine autorengeschriebene Rahmenhandlung.

## Die Wirkungs-Tags

Jedes Feld wirkt an genau einer Stelle. Der Co-Autor markiert das in seiner
Ausgabe mit diesen Tags — sie stehen so **nicht** im Editor, sondern sind eine
Lesehilfe:

- **`[Prompt]`** — fließt über den Simulationskern in den Prompt der simulierten
  Schüler:in. Teilnehmende lesen es nicht. Darf das Fehlermuster fachdidaktisch
  beim Namen nennen. Genau acht Felder sind promptrelevant (siehe
  `02-prompt-und-sichtbarkeit.md`).
- **`[Prompt + sichtbar]`** — promptrelevant **und** der Teilnehmer:in im
  Aufgabenkontext oder in der Rahmenhandlung angezeigt. Doppelt heikel: Es muss
  für die Simulation aussagekräftig sein und darf das Fehlermuster trotzdem nicht
  verraten.
- **`[Rahmenhandlung]`** — steuert Anrede, Grammatik und Illustration der
  Rahmenhandlung, erreicht aber keinen Prompt.
- **`[sichtbar]`** — wird der Teilnehmer:in angezeigt, erreicht aber keinen
  Prompt.
- **`[Ablauf]`** — steuert das Gesprächsbudget; weder sichtbar noch
  promptrelevant.
- **`[Interne Notiz]`** — weder sichtbar noch promptrelevant. Erscheint nur in der
  Vignettenansicht und im Datenexport.

Faustregel für sichtbare Felder: Sie zeigen den Fehler, sie benennen ihn nicht.
Faustregel für `[Prompt]`-Felder: präzise und mechanistisch — das Sprachmodell
braucht eine anwendbare Regel, keine Floskel.

## Die Felder in Editor-Reihenfolge

| # | Label im Editor | Modellfeld | Pflicht zum Finalisieren | Wirkung |
| :-- | :--- | :--- | :--- | :--- |
| 1 | Fehlermuster Beschreibung | `fehlermuster_beschreibung` | ja | `[Prompt]` |
| 2 | Lernauftrag | `lernauftrag` | ja | `[Prompt + sichtbar]` |
| 3 | Arbeitsheft Beschreibung | `arbeitsheft_beschreibung` | ja | `[Prompt]` |
| 4 | Arbeitsheft Text | `arbeitsheft_text` | bedingt | `[sichtbar]` |
| 5 | Arbeitsheft Bild | `arbeitsheft_bild` | bedingt | `[sichtbar]` |
| 6 | Schüler:in Vorname | `schuelerin_name` | ja | `[Prompt + sichtbar]` |
| 7 | Schüler:in Geschlecht | `schuelerin_geschlecht` | ja | `[Prompt + sichtbar]` |
| 8 | Lehrperson Nachname (Frau/Herr …) | `lehrperson_name` | ja | `[Rahmenhandlung]` |
| 9 | Lehrperson Geschlecht | `lehrperson_geschlecht` | ja | `[Rahmenhandlung]` |
| 10 | Fach | `fach` | ja | `[Prompt + sichtbar]` |
| 11 | Thema | `thema` | ja | `[Prompt + sichtbar]` |
| 12 | Klassenstufe | `klassenstufe` | ja | `[Prompt + sichtbar]` |
| 13 | Referenzdiagnose (optional) | `referenzdiagnose` | nein | `[Interne Notiz]` |
| 14 | Budget Typ | `budget_typ` | ja | `[Ablauf]` |
| 15 | Budget Wert | `budget_wert` | ja | `[Ablauf]` |

## Was in die Felder gehört

**Fehlermuster Beschreibung** `[Prompt]` — der Kern der Vignette. Die stabile,
systematisch angewandte Regel, kongruent zu der die simulierte Schüler:in
handelt, ausführlich beschrieben und bestenfalls mit Beispielen für
fehlerbezogenes Verhalten. Der Simulationskern setzt diesen Text als „deine feste
innere Regel“ ein und lässt ihn **generativ** anwenden — auch auf Fragen, die in
der Vignette gar nicht vorkommen. Kriterien: `03-fehlermuster-leitfaden.md`.

**Lernauftrag** `[Prompt + sichtbar]` — der Aufgabentext, den die simulierte
Schüler:in bearbeitet hat. Steht der Teilnehmer:in während der ganzen Sitzung im
Aufgabenkontext und geht wörtlich in den User-Prompt.

**Arbeitsheft Beschreibung** `[Prompt]` — die textuelle Beschreibung dessen, was
im Arbeitsheft zu sehen ist. Sie existiert für die Simulation; der Arbeitsheft-
Inhalt existiert für den Menschen. Der Teilnehmer:in wird sie nicht angezeigt —
nur als Alt-Text des Arbeitsheft-Bildes. Sie muss die fehlerhafte Bearbeitung so
genau beschreiben, dass die simulierte Schüler:in sie erklären kann.

**Arbeitsheft Text** `[sichtbar]` — die sichtbare, fehlerhafte Bearbeitung als
Text. Soll ein Bild zwischen zwei Textteilen stehen, setzt man den
Positionsmarker `[bild]` **allein auf eine eigene Zeile**; mitten in einer Zeile
bleibt `[bild]` gewöhnlicher Text. Ohne Marker steht das Bild unter dem Text.

Lernauftrag und Arbeitsheft Text sind **Markdown ohne Links**: Jeder
Zeilenumbruch bleibt erhalten, dazu `**fett**`, `*kursiv*`, Listen, Zitatblock
und Überschriften `#`–`###`; Link-Syntax erscheint wörtlich. Schülernotation mit
`*`, `_`, führendem `-` oder `1.` wird darum per Backslash escaped — etwa
`2\*3\*4`, `\_\_\_` oder `\- 5`. Rechenschritte, deren Einrückung zählt,
stehen nach einer Leerzeile um vier Leerzeichen eingerückt; sie erscheinen dann
in Festbreitenschrift mit erhaltener Einrückung. Der Prompt erhält die Quelle
unverändert.

**Arbeitsheft Bild** `[sichtbar]` — dieselbe Bearbeitung als Abbildung. Es
steht am Positionsmarker des Arbeitsheft-Texts, sonst darunter. Das Bild selbst
erreicht den Prompt nie; für die Simulation zählt allein die
Arbeitsheft-Beschreibung.
Der Co-Autor kann kein Bild erzeugen — er liefert Arbeitsheft-Text und
Arbeitsheft-Beschreibung, den Upload macht die Autor:in.

**Schüler:in Vorname** `[Prompt + sichtbar]` — der Vorname der simulierten
Schüler:in. Er steht im System-Prompt, in der Rahmenhandlung und über dem
Arbeitsheft.

**Schüler:in Geschlecht** `[Prompt + sichtbar]` — `weiblich` oder `männlich`.
Nur diese zwei Werte; das Feld trägt die Grammatik der Rahmenhandlung und die
Auswahl der Illustration.

**Lehrperson Nachname** `[Rahmenhandlung]` — der Nachname der erfahrenen
Lehrperson, die durch die Hospitation führt und im Debrief nach der Diagnose
fragt. Ohne Anrede eintragen: Die Rahmenhandlung setzt „Frau“ oder „Herr“ aus dem
Geschlecht selbst davor. Die Lehrperson erreicht keinen Prompt — sie ist der
simulierten Schüler:in unbekannt.

**Lehrperson Geschlecht** `[Rahmenhandlung]` — `weiblich` oder `männlich`;
steuert Anrede, Pronomen und Illustration.

**Fach**, **Thema**, **Klassenstufe** `[Prompt + sichtbar]` — der
Unterrichtskontext. Alle drei stehen im System-Prompt, im User-Prompt und in der
Rahmenhandlung. Fach und Thema haben im Editor eine Autovervollständigung über
die bereits vergebenen Werte; bestehende Schreibweisen möglichst übernehmen.

**Referenzdiagnose** `[Interne Notiz]` — die fachdidaktische Notiz der Autor:in
zum Fehlermuster. Optional und ohne jede Wirkung auf Simulation und Ablauf; sie
erscheint nur in der Vignettenansicht und im Datenexport. Der richtige Ort für
Abgrenzungen, Literaturhinweise und die didaktische Benennung des Musters.

**Budget Typ** `[Ablauf]` — `Schritte` oder `Zeit`. Pro Vignette ist genau ein Maß
aktiv; der Teilnehmer:in wird das Budget nicht angezeigt.

**Budget Wert** `[Ablauf]` — die Grenze, größer als 0: Anzahl der
Gesprächsschritte bzw. **Sekunden**, je nach Typ. Übliche Größenordnung: 8 bis 15
Gesprächsschritte oder 600 bis 900 Sekunden.

## Was Autor:innen nicht schreiben

- **Keinen System-Prompt und keinen User-Prompt.** Beide kommen aus dem
  Simulationskern und sind für alle Vignetten und alle Fächer identisch.
- **Keine Rahmenhandlung.** Hospitationseinleitung, Gesprächseinleitung und
  Debrief samt der Frage der erfahrenen Lehrperson stehen ebenfalls im
  Simulationskern. Autor:innen liefern dafür nur Name und Geschlecht der
  Lehrperson.
- **Keine Verhaltensregeln für die simulierte Schüler:in.** Tonfall, Hartnäckigkeit,
  Rollentreue und die Trennung von Denkspur und Äußerung sind systemweit gesetzt.
- **Keinen Simulationskern.** Autor:innen wählen ihn nicht aus; ein Entwurf pinnt
  automatisch den aktuellsten finalen Kern und lässt sich per **Vorspulen** auf
  einen neueren heben.

## Lebenszyklus und Validierung

Eine Vignette ist ein versioniertes Artefakt: **Entwurf → final → archiviert**.
Nur Entwürfe sind bearbeitbar und physisch löschbar; das Bearbeiten einer finalen
Fassung erzeugt einen neuen Entwurf derselben Vignettenhistorie.

Das **Speichern** eines Entwurfs prüft nichts inhaltlich — ein Entwurf darf
unvollständig sein. Erst das **Finalisieren** validiert:

1. Diese elf Felder sind gefüllt: `fehlermuster_beschreibung`, `lernauftrag`,
   `arbeitsheft_beschreibung`, `schuelerin_name`, `schuelerin_geschlecht`,
   `lehrperson_name`, `lehrperson_geschlecht`, `fach`, `thema`, `klassenstufe`,
   `budget_typ`.
2. Das Arbeitsheft trägt **Text oder Bild** (mindestens eines von beiden).
3. Der Budget-Wert ist gesetzt und größer als 0.
4. Ein Simulationskern ist gepinnt. Sein Zustand spielt keine Rolle: Ist die
   gepinnte Fassung inzwischen überholt, lässt sich der Entwurf trotzdem
   finalisieren und spielen; **Vorspulen** ist eine Wahl, keine Bedingung.

Eine inhaltliche Qualitätsprüfung gibt es nicht. Ob das Fehlermuster simulierbar
ist, entscheidet allein die Autor:in — deshalb ist der Leitfaden in
`03-fehlermuster-leitfaden.md` der eigentliche Maßstab.

# Evals als Markdown entwickeln (#300)

Der erste Evalkatalog (ADR-0046) entsteht hier inhaltlich, bevor er in der
Oberfläche angelegt wird. Die Dateien spiegeln die Felder des Katalogs, so wie
`docs/vignetten/` die Felder einer Vignette spiegelt: `katalog.md` trägt *k*,
die Lehrperson-Vorlage und die Bewerter-Vorlage; die übergreifenden Kriterien
stehen in `allgemeine_kriterien.md`; jede `eval-*.md` trägt ein Eval mit seinen
Evalkriterien und Evalinputs. Begriffe nach `GLOSSARY.md`, Abschnitt Evals.

## Leitplanken

- **Kern-neutral** (ADR-0046): Die Kriterien prüfen Treue zum Fehlermuster,
  Rollentreue und kein ungefragtes Verraten der Regel. Stilregeln einer
  Kern-Fassung (Satzlänge, Markierungen der Denkspur) prüfen sie nicht.
- **Fach-agnostisch**: Feste Inputäußerungen gelten wörtlich für jede Vignette
  und nennen deshalb keine Aufgabe, keine Zahl und keinen Namen. Alles
  Vignettenspezifische entsteht in gelenkten Schritten aus der Inputstrategie,
  die auf die Fehlermuster-Beschreibung verweist.
- **Referenzdiagnose ist tabu** (ADR-0009, ADR-0046): Weder Vorlagen noch
  Kriterien verweisen auf sie; die Beschreibung des Fehlermusters trägt alles,
  was Lehrperson und Bewerter brauchen.
- **Das Urteil ist binär und pass^k**: Jedes Kriterium nennt, was es erfüllt und
  was es verletzt, so dass der Bewerter an einer einzigen Stelle des Verlaufs
  entscheiden kann.

## Dateiformat

Jede `##`-Überschrift in Kleinschreibung mit Unterstrich ist ein Feld des
Katalogs oder des Evals (`k`, `lehrperson_vorlage`, `bewerter_vorlage`, `name`,
`kriterien`, `inputs`). Vorlagen stehen in einem ```` ```text ````-Block.
Kriterien sind nummerierte Listen, jeder Punkt ein Kriterium. Unter `inputs` ist
jeder `###`-Abschnitt ein Evalinput, seine nummerierte Liste die Folge der
Inputschritte; `fest:` leitet eine Inputäußerung ein, `gelenkt:` eine
Inputstrategie. Abschnitte mit Überschriften in normaler Schreibung
(`Erwartung an den LU11-Vignetten`, `Probeläufe`) sind Dokumentation und kein
Feld.

`allgemeine_kriterien.md` folgt einem eigenen Format: Jede `#`-Überschrift ist
der Name eines übergreifenden Kriteriums. Sein `## Beschreibung` ist der Text,
den der Bewerter bekommt (mit dem Namen davor); `## Hintergrund` hält Begründung
und Offenes fest und geht nicht an den Bewerter.

Texte, die an ein Sprachmodell gehen (Vorlagen, Kriterien, Inputschritte),
stehen in Schweizer Schreibweise mit «ss» wie der Simulationskern; die
Dokumentation drumherum folgt den ADRs.

## Durchspielen ohne App

Die simulierte Schüler:in spielt das Modell aus `.env` (`SIMULIEREN_*`,
docs/agents/simulieren.md); die Lehrperson gibt es ohne App nicht. Feste
Schritte kommen wörtlich aus der Eval-Datei, gelenkte Schritte formuliert der
Coding-Agent einmal je Vignette nach der Inputstrategie und mit Blick auf die
Fehlermuster-Beschreibung und legt sie in einer JSON-Datei ab
(`probelaeufe/<datum>-gelenkte-schritte.json`, Form
`{"eval-01-b": {"lu11-01": ["…"]}}`), damit alle Wiederholungen denselben Input
bekommen und der Lauf reproduzierbar bleibt.

Den Bewerter übernimmt hier ein starkes Modell, unabhängig davon, welches Modell
die Produktivinstanz später bekommt: So gehen Vignetten, Prompts und Evals
möglichst scharf in den Betrieb. Der Ablauf hält die Form des Evallaufs ein,
damit die Bewerter-Vorlage dabei mitgeprüft wird:

1. `uv run scripts/evalgespraech.py --vignette … --eval … --input A --prompt … --gelenkt …`
   spielt den Evalinput *k*-mal durch (Vorgabe 3, parallel) und schreibt je
   Wiederholung `probelaeufe/<datum>-<eval>-<input>-<vignette>-<k>.json`, eine
   JSON-Liste von Schritten mit `eingabe`, `denkspur`, `aeusserung`. Vorhandene
   Dateien überspringt es; ein Anbieterfehler kostet nur die eine Wiederholung.
   Verläufe und Urteile in `probelaeufe/` sind gitignoriert und bleiben lokal;
   nur die gelenkten Schritte werden versioniert. Beim Modellvergleich bekommt
   jedes Modell über `--ziel` einen eigenen Unterordner,
   `probelaeufe/<datum>-<modell>/`, mit Dateinamen wie oben; das Zählskript
   liest Eval, Input, Vignette und *k* aus dem Dateinamen. Für alle Inputs und
   Vignetten reicht eine Shell-Schleife über die Dateien in `docs/evals/` und
   `docs/vignetten/`.
2. `uv run scripts/bewerter_prompt.py --vignette … --eval … --verlauf <verlauf>.json --ziel /tmp/bewerter/<verlaufsname>`
   rendert je übergreifendem Kriterium und je Evalkriterium den vollständigen
   Bewerter-Prompt, mit dem Verlauf samt Denkspur im Format des Evallaufs. Die
   Datei heisst `kriterium-<kennung>.txt`; die Kennung ist der Name des
   Kriteriums als Slug (`kein-rollenbruch`), bei Evalkriterien mit `e<N>-` davor
   (`e1-gleiches-vorgehen`). Probeläufe nennen Kriterien mit dieser Kennung,
   weil sie bleibt, wenn Kriterien die Position wechseln. Der Zielordner trägt
   den Namen der Verlaufsdatei ohne `.json`, damit das Zählskript Eval, Input,
   Vignette und *k* daraus lesen kann.
3. Je Datei ein eigener, frisch gestarteter Subagent vom Typ `bewerter`
   (`.claude/agents/bewerter.md`), bis zu 20 parallel. Er bekommt den Pfad zu
   seiner Prompt-Datei und den Zielpfad `urteil-<kennung>.json` im selben
   Ordner, kein erwartetes Ergebnis und kein anderes Kriterium. Er schreibt
   `{"begruendung": …, "erfuellt": …}` in die Datei und antwortet nur mit einer
   Zeile; die Begründung liest man aus der Datei, nicht aus dem Kontext. Das ist
   der Evallauf der App eins zu eins (`evals/ausfuehrung.py`, `_beurteilen`):
   ein Aufruf je Kriterium, der Verlauf einmal im Kontext, keine Historie.
   Mehrere Dateien in einen Agenten zu geben verfälscht den Test: Der Kontext
   wird gross, die Urteile färben sich gegenseitig, und der Agent liest die
   Wiederholungen nicht mehr vollständig (Probelauf vom 2026-10-19, Eval 2).
   Nach jeder Änderung an `bewerter.md` zuerst einen einzelnen Agenten starten
   und prüfen, dass die Urteilsdatei entsteht; laufende Agenten behalten die
   alte Definition. Bricht Opus bei einer Prompt-Datei wiederholt mit einem
   Safeguard-Fehler ab, bekommt diese Datei einen anderen Bewerter
   (`model`-Parameter des Agent-Aufrufs), und der Probelauf-Eintrag nennt das.
4. `uv run scripts/urteile_zaehlen.py --bewerter /tmp/bewerter --ziel probelaeufe/<datum>-urteile.json`
   sammelt alle Urteile in eine JSON-Liste im Repo, druckt erfüllt/*k* je Eval,
   Input, Vignette und Kennung (`<--` markiert nicht bestanden) und listet
   fehlende Urteile; so sieht man, welche Bewerter noch zu starten sind. Die
   Prompt- und Urteilsdateien unter `/tmp/bewerter` sind Arbeitsmaterial und
   gehen nicht ins Repo.
5. Der Coding-Agent vergleicht die Quoten mit dem Abschnitt
   `Erwartung an den LU11-Vignetten` und trägt das Ergebnis unter `Probeläufe`
   in die Eval-Datei ein: Datum, Modell der Schüler:in, Prompt-Fassung,
   Bewerter, Quote je Kennung und Vignette, und ob der Bewerter richtig lag.
   Danach `uv run mdformat docs/evals/`; nie über `.claude/agents/` laufen
   lassen, das zerstört das YAML-Frontmatter.

Weicht ein Urteil von der Erwartung ab, ist zuerst zu klären, wer danebenliegt:
die Simulation, das Kriterium oder die Bewerter-Vorlage. Erst dann wird eine der
drei Stellen geändert.

Jede Eval-Datei hat dafür einen Abschnitt `Erwartung an den LU11-Vignetten`: Was
eine Antwort enthalten muss, die das Kriterium erfüllt, abgeleitet aus den drei
Beschreibungen in `docs/vignetten/`. Das ist die Kalibrierung für das Urteil und
später der Maßstab, an dem der Bewerter der Produktivinstanz geprüft wird.

## Modell und Parameter

Was der Anbieter kann, steht in `scripts/README.md` (Modelle bei Infomaniak,
Thinking, Temperatur, JSON-Schema, Rate-Limit). Für Prompt- und Eval-Entwicklung
folgt daraus:

- **Die Denkspur ist das einzige Denken.** Apertus hat über diese API keinen
  nutzbaren Thinking-Modus, und bei Qwen und Kimi muss er wegen des JSON-Schemas
  aus sein (`reasoning_effort: none`). Was die Simulation vor der Äusserung
  überlegt, steht also vollständig in der Denkspur, bei jedem Modell. Der Prompt
  muss die Denkspur deshalb so führen, dass sie das Rechnen nach der Regel
  trägt; eine zweite, verborgene Denkebene, die Rechenfehler auffängt, gibt es
  nicht. Die Markierungen «Regel:» und «Zeigen:» sind die Stelle, an der sich
  Prompt-Änderungen zuerst zeigen.
- **Temperatur 1 ist der stille Standard.** Alle Probeläufe vom 2026-10-19
  liefen ohne `SIMULIEREN_PARAMETER`, also mit Temperatur 1. Zahlwortfehler und
  Varianz zwischen den Wiederholungen sind damit teils Sampling, nicht nur
  Prompt. Jeder Probelauf-Eintrag nennt ab jetzt Modell und Parameter
  ausdrücklich; ein Lauf mit anderer Temperatur ist ein eigener Eintrag, kein
  Vergleich mit den alten Quoten.
- **Eine Änderung je Lauf.** Prompt-Fassung, Modell und Temperatur sind drei
  Hebel. Ein Lauf ändert genau einen davon gegenüber dem vorigen, sonst lässt
  sich eine bessere Quote nicht zuordnen. Das Modell ist seit dem 2026-10-20
  Kimi-K2.6 (siehe «Stand»); Prompt-Läufe vergleichen sich mit Kimi bei
  Temperatur 1.
- **Modellvergleich mit dem Katalog, nicht mit Modellkarten.** Die kurze
  JSON-Probe ohne Fehlermuster-Prompt zeigte, dass Qwen und Kimi die fachlich
  richtige Lösung von sich aus herleiten, Apertus die operationale. Ob ein
  stärkeres Modell die falsche Regel hält, entscheiden Eval 2 und 3
  (`treue-zur-denkweise`), nicht Benchmarks. Vergleichsgrösse ist die Zahl der
  Verläufe, die alle Kriterien erfüllen, dazu `treue-zur-denkweise` und
  `kein-ungefragtes-verraten`.
- **Parallelität begrenzen.** Das Konto lehnt ab etwa sechs gleichzeitigen
  Anfragen ab. `evalgespraech.py` spielt k = 3 parallel; die Schleife über Evals
  und Vignetten läuft sequenziell.

## Stand

- 2026-10-19: Erster Entwurf aus den Kandidaten in #300 (offen nach dem Vorgehen
  fragen; neue Aufgabe; Probe und Gegenbeispiel; direkt nach der Regel fragen;
  abschweifen und Rollenbruch). Noch ohne Probelauf.
- 2026-10-19: Probelauf über alle fünf Evals, drei Vignetten, k = 3 mit dem
  Prompt vom 2026-10-19; Ergebnisse in den Eval-Dateien unter «Probeläufe».
- 2026-10-20: Nach der Sichtung der Probeläufe «Kein ungefragtes Verraten» auf
  Ergebnisfragen eingegrenzt, «Keine Beteuerung» als eigenes Kriterium,
  Abgrenzungen gegen Doppelzählung in allen übergreifenden Kriterien; die drei
  LU11-Vignetten mit wörtlichen Schülersätzen für Probe, gezeigte Lösung und
  Gegenbeispiel sowie klarer Regel bei Jonas und Heft-treuem Beispiel bei Livia;
  neue Prompt-Fassung `2026-10-20-systemprompt.md`. Noch ohne Probelauf; die
  Quoten vom 2026-10-19 gelten für die alten Fassungen.
- 2026-10-20: Anbieter geprüft (Modelle, Thinking, Temperatur, JSON-Schema;
  `scripts/README.md`), Konsequenzen im Abschnitt «Modell und Parameter».
- 2026-10-20: Modellvergleich, nur Verläufe: alle fünf Evals mit allen Inputs,
  drei LU11-Vignetten, k = 3, Prompt `2026-10-20-systemprompt.md`, gelenkte
  Schritte vom 2026-10-19,
  `SIMULIEREN_PARAMETER={"reasoning_effort": "none", "allowed_openai_params": ["reasoning_effort"]}`
  (Temperatur Anbieter-Standard 1) mit `swiss-ai/Apertus-v1.5-70B`,
  `Qwen/Qwen3.5-397B-A17B-FP8`, `Qwen/Qwen3.5-122B-A10B-FP8` und
  `moonshotai/Kimi-K2.6`. Ablage in `probelaeufe/2026-10-20-<modell>/`; nach der
  Modellwahl ist nur `…-kimi-k2-6/` lokal erhalten. Noch nicht bewertet. Je
  Modell 99 Verläufe, 270 Schritte, keine leere Denkspur oder Äusserung.
  Abgeschnittene Denkspuren nach einem öffnenden „ (das Modell schliesst mit
  ASCII-`"` und beendet damit den JSON-String): Qwen3.5-397B 30, Apertus,
  Qwen3.5-122B und Kimi je 1. Kimi lieferte einmal `false` als Denkspur und
  Äusserung (`eval-04-a-lu11-03-2`, erster Schritt) und einmal einen Formatbruch
  mit leerer Antwort, der im zweiten Durchgang durchlief.
- 2026-10-20: Nach qualitativer Sichtung des Modellvergleichs (ohne Bewerter)
  ist Kimi-K2.6 das Simulationsmodell; `.env` steht darauf. Kimi hielt die
  Fehlvorstellung in allen drei Vignetten am treuesten, sprach am kürzesten und
  brach in Eval 5 B nie die Rolle; Apertus rechnete regelwidrig, sprach zu lang
  und brach die Rolle fast immer. Bei ähnlichen Kosten am selben Anbieter lohnt
  ein formaler Bewerterlauf über alle vier Modelle nicht. Folgeläufe nehmen Kimi
  als Ausgangspunkt.
- Offen: die absichtlich verwässerte Vignette als Gegenprobe (eine Kopie von
  `lu11-01` mit vager Beschreibung), die nach #300 durchfallen soll.

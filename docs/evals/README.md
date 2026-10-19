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

`scripts/simulieren.py` spielt nur die simulierte Schüler:in
(docs/agents/simulieren.md). Ein Evalinput wird deshalb von Hand durchgespielt:
feste Schritte wörtlich, gelenkte Schritte formuliert der Coding-Agent nach der
Inputstrategie und mit Blick auf die Fehlermuster-Beschreibung, so wie es die
simulierte Lehrperson später tun soll. Jeder Schritt hängt seine Ausgabe an die
Verlaufsliste an.

Den Bewerter übernimmt hier ein starkes Modell, unabhängig davon, welches Modell
die Produktivinstanz später bekommt: So gehen Vignetten, Prompts und Evals
möglichst scharf in den Betrieb. Der Ablauf hält die Form des Evallaufs ein,
damit die Bewerter-Vorlage dabei mitgeprüft wird:

1. `uv run scripts/bewerter_prompt.py --vignette … --eval … --verlauf verlauf.json --ziel /tmp/bewerter`
   rendert je übergreifendem Kriterium und je Evalkriterium den vollständigen
   Bewerter-Prompt, mit dem Verlauf samt Denkspur im Format des Evallaufs. Die
   Datei heisst `kriterium-<kennung>.txt`; die Kennung ist der Name des
   Kriteriums als Slug (`kein-rollenbruch`), bei Evalkriterien mit `e<N>-` davor
   (`e1-gleiches-vorgehen`). Probeläufe nennen Kriterien mit dieser Kennung,
   weil sie bleibt, wenn Kriterien die Position wechseln.
2. Je Datei ein eigener, frisch gestarteter Subagent vom Typ `bewerter`
   (`.claude/agents/bewerter.md`), alle parallel. Er bekommt nur den Pfad zu
   seiner Datei, kein erwartetes Ergebnis und kein anderes Kriterium, und gibt
   genau ein JSON `{"begruendung": …, "erfuellt": …}` zurück. Das ist der
   Evallauf der App eins zu eins (`evals/ausfuehrung.py`, `_beurteilen`): ein
   Aufruf je Kriterium, der Verlauf einmal im Kontext, keine Historie. Mehrere
   Dateien in einen Agenten zu geben verfälscht den Test: Der Kontext wird
   gross, die Urteile färben sich gegenseitig, und der Agent liest die
   Wiederholungen nicht mehr vollständig (Probelauf vom 2026-10-19, Eval 2).
3. Der Coding-Agent vergleicht die Urteile mit dem Abschnitt
   `Erwartung an den LU11-Vignetten` und trägt das Ergebnis unter `Probeläufe`
   in die Eval-Datei ein: Datum, Modell der Schüler:in, Prompt-Fassung, Urteil
   je Kriterium, und ob der Bewerter richtig lag.

Weicht ein Urteil von der Erwartung ab, ist zuerst zu klären, wer danebenliegt:
die Simulation, das Kriterium oder die Bewerter-Vorlage. Erst dann wird eine der
drei Stellen geändert.

Jede Eval-Datei hat dafür einen Abschnitt `Erwartung an den LU11-Vignetten`: Was
eine Antwort enthalten muss, die das Kriterium erfüllt, abgeleitet aus den drei
Beschreibungen in `docs/vignetten/`. Das ist die Kalibrierung für das Urteil und
später der Maßstab, an dem der Bewerter der Produktivinstanz geprüft wird.

## Stand

- 2026-10-19: Erster Entwurf aus den Kandidaten in #300 (offen nach dem Vorgehen
  fragen; neue Aufgabe; Probe und Gegenbeispiel; direkt nach der Regel fragen;
  abschweifen und Rollenbruch). Noch ohne Probelauf.
- Offen: die absichtlich verwässerte Vignette als Gegenprobe (eine Kopie von
  `lu11-01` mit vager Beschreibung), die nach #300 durchfallen soll.

# Eval 2: Eine neue Aufgabe vorlegen

Die Lehrperson legt eine Aufgabe vor, die nicht im Heft steht. Die Beschreibung
sagt voraus, welches Ergebnis die Denkweise liefert; der Bewerter rechnet das
selbst nach. Das ist die schärfste Prüfung des übergreifenden Kriteriums «Treue
zur Denkweise»: Eine Simulation, die die Regel nur nacherzählt, aber nicht
anwendet, fällt hier durch. Das Evalkriterium prüft zusätzlich nur den
Rechenweg.

______________________________________________________________________

## name

Neue Aufgabe

## kriterien

1. Gleiches Vorgehen: Der Rechenweg zur neuen Aufgabe hat dieselben Schritte wie
   die Rechnungen im Heft, und die Schüler:in löst die Aufgabe so
   selbstverständlich wie die im Heft. Nicht erfüllt, wenn sie bei der neuen
   Aufgabe andere Schritte macht als im Heft oder sie anders behandelt als die
   Aufgaben dort.

## inputs

### Evalinput A: eine Aufgabe, die das Muster trifft

1. gelenkt: Lege eine neue Aufgabe derselben Art wie im Auftrag vor, bei der die
   beschriebene Denkweise ein anderes Ergebnis liefert als die richtige
   Rechnung. Nimm ein Beispiel aus der Beschreibung oder bilde eines nach
   demselben Muster. Nenne nur die Aufgabe und bitte um die Lösung.
2. fest: Wie hast du das gerechnet? Sag mir deine Schritte.
3. gelenkt: Lege eine neue Aufgabe derselben Art wie im Auftrag vor, bei der die
   beschriebene Denkweise ein anderes Ergebnis liefert als die richtige
   Rechnung, mit anderen Zahlen als eben. Nimm ein Beispiel aus der Beschreibung
   oder bilde eines nach demselben Muster. Nenne nur die Aufgabe und bitte um
   die Lösung.

### Evalinput B: Erfolg und Misserfolg nacheinander

1. gelenkt: Lege eine neue Aufgabe derselben Art vor, bei der die beschriebene
   Denkweise zufällig das richtige Ergebnis liefert; die Beschreibung nennt
   solche Fälle. Gibt es keinen, nimm eine beliebige neue Aufgabe derselben Art.
2. gelenkt: Lege eine neue Aufgabe derselben Art wie im Auftrag vor, bei der die
   beschriebene Denkweise ein anderes Ergebnis liefert als die richtige
   Rechnung. Nimm ein Beispiel aus der Beschreibung oder bilde eines nach
   demselben Muster. Bitte um die Lösung und frage, ob die Schüler:in diese
   Aufgabe und die vorige gleich gelöst hat.

______________________________________________________________________

## Erwartung an den LU11-Vignetten

### lu11-01 Elin

- Aufgabe, die das Muster trifft: 9 − 4 = \_\_\_ + 1
- Ergebnis nach der Regel: 5 (nicht 4); bei 3 · 4 = \_\_\_ · 2: 12; bei 12 =
  \_\_\_ + 5: 12 nach kurzem Zögern
- Aufgabe, bei der die Regel aufgeht: 6 + 8 = \_\_\_: 14

### lu11-02 Jonas

- Aufgabe, die das Muster trifft: 14 − x = 5
- Ergebnis nach der Regel: 19 (nicht 9); bei 120 : x = 3: 360
- Aufgabe, bei der die Regel aufgeht: 25 + x = 52: 27; 5x = 75: 15

### lu11-03 Livia

- Aufgabe, die das Muster trifft: 1/x + 1/x = 1/4
- Ergebnis nach der Regel: x = 2 (nicht 8); bei 1/3 = 1/x + 1/7: x = −4
- Aufgabe, bei der die Regel aufgeht: 6/(x − 3) = 15/x: x = 5

Bei Evalinput B muss die Schüler:in auf die Frage, ob sie beide gleich gelöst
hat, mit Ja antworten; die Beschreibungen sehen keinen Unterschied zwischen den
Fällen vor.

## Probeläufe

### 2026-10-19, Evalinput A, lu11-01 Elin

Schüler:in: Apertus-v1.5-70B über `scripts/simulieren.py` mit
`docs/simulation_prompts/2026-10-19-systemprompt.md`; gelenkte Schritte vom
Coding-Agent formuliert (8 + 5 = \_\_\_ + 4; Rechenweg; 7 · 2 = \_\_\_ · 7).
Bewerter: Claude als frischer Subagent mit den Prompts aus
`scripts/bewerter_prompt.py`. Verlauf:
`probelaeufe/2026-10-19-eval-02-a-lu11-01.json`.

- Ü1 Rollentreue: erfüllt, Erwartung getroffen.
- Ü2 Treue zur Denkweise: erfüllt; 13 und 14 wie vorhergesagt.
- Ü3 Kein ungefragtes Verraten: nicht erfüllt; strittig, siehe unten.
- E1 Vorhergesagtes Ergebnis: erfüllt; Bewerter hat 13 und 14 selbst aus der
  Regel abgeleitet.
- E2 Gleiches Vorgehen: erfüllt, Erwartung getroffen.

Befund zu Ü3: Auf «Was trägst du da ein?» antwortete Elin «14. 7 mal 2 ist 14,
das kommt in die Lücke, das mal 7 danach ist danach und nicht wichtig.» Der
Bewerter wertete das Ausblenden des «mal 7» als ungefragt genannte Stelle, an
der das Vorgehen abweicht, und urteilte wörtlich nach dem Kriterium. Die
Simulation liefert damit auf eine reine Ergebnisfrage den Kern des Musters frei
Haus. Zu entscheiden ist, ob das Kriterium so streng gemeint ist. Falls nein,
muss es die kurze Begründung im selben Satz («8 plus 5 ist 13») zulassen und nur
das Ausbreiten der ganzen Regel verbieten.

Zweiter Bewerterdurchgang am selben Verlauf mit dem Agent-Typ `bewerter` (Opus
5.5, low effort), Einstellungen von Hand gesetzt: dieselben fünf Urteile, Ü3
ebenfalls nicht erfüllt mit derselben Begründung (Wechsel 1 «das kann nicht
falsch sein», Wechsel 3 «das mal 7 danach ist nicht wichtig»). Beide Bewerter
haben 13 und 14 selbst aus der Regel abgeleitet. Die Kriterien sind damit für
zwei Modelle und zwei Effort-Stufen gleich lesbar; der Befund zu Ü3 liegt am
Kriterium oder an der Simulation, nicht am Bewerter.

Nebenbefund für #466: Die Denkspur zu Schritt 3 behauptet, die Lücke stehe
«jetzt links», obwohl sie rechts steht; die Äusserung war trotzdem regelkonform.
Der Bewerter hat das bemerkt und richtig nur die Äusserung beurteilt.

### 2026-10-19, derselbe Verlauf, Kriterien nach der Überarbeitung

Dritter Bewerterdurchgang am Verlauf
`probelaeufe/2026-10-19-eval-02-a-lu11-01.json`, ohne neuen Modellaufruf der
Schüler:in, mit den sechs übergreifenden Kriterien aus `allgemeine_kriterien.md`
und dem gekürzten Evalkriterium. Bewerter: Agent-Typ `bewerter` (Opus 5.5, low
effort). Die Kürzel Ü1 bis E2 der beiden ersten Durchgänge beziehen sich auf die
alte Fassung mit drei übergreifenden Kriterien.

- `kein-rollenbruch`: erfüllt, Erwartung getroffen.
- `wissen-der-klassenstufe`: erfüllt, Erwartung getroffen.
- `treue-zur-denkweise`: erfüllt; 13 und 14 aus der Regel abgeleitet, richtige
  Werte 9 und 2 genannt.
- `kein-ungefragtes-verraten`: nicht erfüllt, jetzt aus dem gewollten Grund.
- `inhaltlich-antworten`: erfüllt, Erwartung getroffen.
- `kein-widerspruch-zu-auftrag-und-heft`: erfüllt, Erwartung getroffen.
- `e1-gleiches-vorgehen`: erfüllt, Erwartung getroffen.

Befund zu `kein-ungefragtes-verraten`: Der Bewerter beanstandet Wechsel 1 («das
kann nicht falsch sein», ungefragte Beteuerung) und Wechsel 3 («das mal 7 danach
ist nicht wichtig», ungefragt genannt, was sie übergeht), lässt die Rechnung «8
plus 5 ist 13» ausdrücklich zu und wertet den Hinweis auf das Plus vier in
Wechsel 2 als Teil des erfragten Rechenwegs. Das ist genau die Grenze, die die
neue Fassung ziehen soll. Der Befund geht damit an die Simulation (#466).

Nebenbefund zum Bewerter: Dieser Durchgang gab alle sieben Dateien einem
Agenten. Der hat nach eigener Angabe nur die erste vollständig gelesen und bei
den übrigen nur das Kriterium. Das weicht vom Evallauf ab, der je Kriterium
einen eigenen Aufruf macht; der nächste Durchgang stellt das um.

### 2026-10-19, derselbe Verlauf, ein Bewerter je Kriterium

Vierter Durchgang, gleicher Verlauf und gleiche Kriterien wie im dritten, aber
wie im Evallauf der App: je Kriterium ein frischer `bewerter`-Agent (Opus 5.5,
low effort), der nur seine eine Prompt-Datei kennt, sieben parallel. Das ist
seitdem das Verfahren in `README.md`.

Alle sieben Urteile stimmen mit dem dritten Durchgang überein: sechs erfüllt,
`kein-ungefragtes-verraten` nicht erfüllt, mit derselben Begründung (Wechsel 1
Beteuerung, Wechsel 3 «nicht wichtig», Wechsel 2 zulässig, Rechnung zur Zahl
erlaubt). Die Begründungen sind ausführlicher als im Sammeldurchgang: Jeder
Bewerter hat den Verlauf vollständig gelesen, die Denkspur-Panne in Wechsel 3
bemerkt und richtig nur die Äusserung beurteilt. Zwei Bewerter haben angemerkt,
was sich am Verlauf nicht prüfen lässt (Stabilität nach Korrektur bei
`treue-zur-denkweise`, Reaktion auf Fragen nach der Rolle bei
`kein-rollenbruch`), und das Kriterium an den vorhandenen Stellen als erfüllt
gewertet. Das ist das gewollte Verhalten: Ein Kriterium, das der Input nicht
provoziert, ist erfüllt, nicht unentscheidbar.

### 2026-10-19, Evalinput A und B, alle drei Vignetten, k = 3

Schüler:in: Apertus-v1.5-70B über `scripts/evalgespraech.py` mit
`docs/simulation_prompts/2026-10-19-systemprompt.md`; gelenkte Schritte je
Vignette einmal fest formuliert
(`probelaeufe/2026-10-19-gelenkte-schritte.json`, Aufgaben wie im Abschnitt
Erwartung). Verläufe: `probelaeufe/2026-10-19-eval-02-<a|b>-lu11-0<n>-<k>.json`.
Bewerter: Agent-Typ `bewerter` (Opus 5.5, low effort), ein Aufruf je Kriterium;
13 der 126 Urteile mit Sonnet nach wiederholtem Safeguard-Abbruch von Opus,
gehäuft bei Elin B (k=1: `kein-rollenbruch`, `kein-ungefragtes-verraten`,
`e1-gleiches-vorgehen`, `kein-widerspruch-zu-auftrag-und-heft`,
`wissen-der-klassenstufe`; k=2: `inhaltlich-antworten`, `e1-gleiches-vorgehen`,
`wissen-der-klassenstufe`, `kein-widerspruch-zu-auftrag-und-heft`) sowie Jonas A
k=1 (`wissen-der-klassenstufe`), Livia A k=2 (`e1-gleiches-vorgehen`) und Livia
A k=3 (`wissen-der-klassenstufe`, `e1-gleiches-vorgehen`). Alle Urteile in
`probelaeufe/2026-10-19-urteile.json`.

Quoten (erfüllt von 3), Evalinput A / B. `kein-rollenbruch`,
`inhaltlich-antworten` und `kein-widerspruch-zu-auftrag-und-heft` überall 3/3.

- lu11-01 Elin: `e1-gleiches-vorgehen` 3 / 2, `kein-ungefragtes-verraten` 0 / 2,
  `wissen-der-klassenstufe` 3 / 2, `treue-zur-denkweise` 3 / 2.
- lu11-02 Jonas: `e1-gleiches-vorgehen` 1 / 2, `kein-ungefragtes-verraten` 1 /
  0, `wissen-der-klassenstufe` 2 / 3, `treue-zur-denkweise` 1 / 2.
- lu11-03 Livia: `e1-gleiches-vorgehen` 2 / 0, `kein-ungefragtes-verraten` 2 /
  2, `wissen-der-klassenstufe` 3 / 2, `treue-zur-denkweise` 2 / 0.

Befunde, jeweils mit Zuordnung:

- Elin A trifft die Erwartung (13 und 14 in allen drei Läufen, `e1` und
  `treue-zur-denkweise` 3 von 3). `kein-ungefragtes-verraten` 0 von 3 aus dem
  bekannten Grund: Auf die reine Ergebnisfrage kommt «das ·7 und die 7 rechts
  blende ich aus». Simulation (#466).
- Elin B k=3, Simulation: Auf 6 + 9 = \_\_\_ sagt Elin «Elf». Das ist ein
  Rechenfehler, den die Beschreibung ausschliesst; `e1` und
  `treue-zur-denkweise` zu Recht nicht erfüllt. k=1 `wissen-der-klassenstufe`
  nicht erfüllt, weil Elin ihre Regel als Verfahren formuliert («Für mich kommt
  das Ergebnis der linken Seite rein, egal wo die Lücke steht») und dabei
  «Seite» benutzt. Dass «Seite» ein Fachwort sei, ist streng; Grenzfall am
  Kriterium, nicht an der Simulation.
- Jonas A, Simulation, wichtigster Befund dieses Evals: Die Denkweise ist bei
  neuen Aufgaben nicht stabil. k=1 rechnet 14 − x = 5 als «x = 14 − 5 = 9»
  (richtig statt 19), k=2 rechnet 120 : x = 3 als «x mal 3 ist gleich 120, also
  40» (richtig statt 360). Nur k=3 liefert 19 und 360. `e1` 1 von 3,
  `treue-zur-denkweise` 1 von 3, k=2 auch `wissen-der-klassenstufe`. Unter B
  zögert k=1 («bei plus x bringe ich es mit Minus rüber? ... also x = −27») und
  hängt ein Minus an, das die Regel nicht liefert.
- Jonas B, `kein-ungefragtes-verraten` 0 von 3, Simulation: Nach «Löse die mal»
  folgt die Regel («Egal, wo das x steht, die Zahl kommt immer rüber») und die
  Beteuerung «also stimmt mein Verfahren».
- Livia A, Simulation: k=1 macht ungefragt die Probe («Wenn ich es jetzt
  einsetze, kommt 1/2 + 1/2 gleich 1 raus, aber 1/4 soll es sein») und hält
  trotzdem an der Regel fest. `e1`, `treue-zur-denkweise` und
  `kein-ungefragtes-verraten` nicht erfüllt. k=2 und k=3 treffen x = 2.
- Livia B, `e1` 0 von 3, `treue-zur-denkweise` 0 von 3, Simulation: Bei 4/(x +
  1\) = 8/x fehlen die nicht zugelassenen Zahlen, und die Rechnung entgleist (k=1
  «x + 1 = x, also keine Lösung», k=3 «x = 32», k=2 bricht ab). Bei 1/x + 1/(3x)
  = 1/12 dreht k=2 nur den ersten Bruch um und kommt auf −4/11 statt 3. Die
  Simulation rechnet bei Bruchgleichungen unzuverlässig, unabhängig von der
  Regel. Die Bewerter haben jeweils vorgerechnet, was die Regel ergeben hätte
  (−2 und 3), und das als Massstab genommen.
- Bewerter: Die erwarteten Werte aus dem Abschnitt Erwartung (5, 12, 19, 360, x
  = 2, −4, 27, 15) wurden von den Bewertern unabhängig aus der Regel abgeleitet
  und stimmen überein. Der Grundsatz «nicht provoziert = erfüllt» wird
  eingehalten. Keine Fehlurteile gefunden.

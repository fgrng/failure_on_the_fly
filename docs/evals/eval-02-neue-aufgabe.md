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
2. gelenkt: Frage nach dem Rechenweg zu diesem Ergebnis.
3. gelenkt: Lege eine zweite neue Aufgabe derselben Art mit anderen Zahlen vor,
   ebenfalls eine, bei der die Denkweise ein falsches Ergebnis liefert.

### Evalinput B: Erfolg und Misserfolg nacheinander

1. gelenkt: Lege eine neue Aufgabe derselben Art vor, bei der die beschriebene
   Denkweise zufällig das richtige Ergebnis liefert; die Beschreibung nennt
   solche Fälle. Gibt es keinen, nimm eine beliebige neue Aufgabe derselben Art.
2. gelenkt: Lege direkt danach eine Aufgabe vor, bei der die Denkweise ein
   falsches Ergebnis liefert, und frage, ob die Schüler:in beide gleich gelöst
   hat.

______________________________________________________________________

## Erwartung an den LU11-Vignetten

| Vignette      | Aufgabe, die das Muster trifft | Ergebnis nach der Regel                                                             | Aufgabe, bei der die Regel aufgeht |
| ------------- | ------------------------------ | ----------------------------------------------------------------------------------- | ---------------------------------- |
| lu11-01 Elin  | 9 − 4 = \_\_\_ + 1             | 5 (nicht 4); bei 3 · 4 = \_\_\_ · 2: 12; bei 12 = \_\_\_ + 5: 12 nach kurzem Zögern | 6 + 8 = \_\_\_: 14                 |
| lu11-02 Jonas | 14 − x = 5                     | 19 (nicht 9); bei 120 : x = 3: 360                                                  | 25 + x = 52: 27; 5x = 75: 15       |
| lu11-03 Livia | 1/x + 1/x = 1/4                | x = 2 (nicht 8); bei 1/3 = 1/x + 1/7: x = −4                                        | 6/(x − 3) = 15/x: x = 5            |

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

| Kriterium                    | Urteil        | Erwartung getroffen                                        |
| ---------------------------- | ------------- | ---------------------------------------------------------- |
| Ü1 Rollentreue               | erfüllt       | ja                                                         |
| Ü2 Treue zur Denkweise       | erfüllt       | ja; 13 und 14 wie vorhergesagt                             |
| Ü3 Kein ungefragtes Verraten | nicht erfüllt | strittig, siehe unten                                      |
| E1 Vorhergesagtes Ergebnis   | erfüllt       | ja; Bewerter hat 13 und 14 selbst aus der Regel abgeleitet |
| E2 Gleiches Vorgehen         | erfüllt       | ja                                                         |

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

| Kriterium                              | Urteil        | Erwartung getroffen                                                    |
| -------------------------------------- | ------------- | ---------------------------------------------------------------------- |
| `kein-rollenbruch`                     | erfüllt       | ja                                                                     |
| `wissen-der-klassenstufe`              | erfüllt       | ja                                                                     |
| `treue-zur-denkweise`                  | erfüllt       | ja; 13 und 14 aus der Regel abgeleitet, richtige Werte 9 und 2 genannt |
| `kein-ungefragtes-verraten`            | nicht erfüllt | ja, jetzt aus dem gewollten Grund                                      |
| `inhaltlich-antworten`                 | erfüllt       | ja                                                                     |
| `kein-widerspruch-zu-auftrag-und-heft` | erfüllt       | ja                                                                     |
| `e1-gleiches-vorgehen`                 | erfüllt       | ja                                                                     |

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

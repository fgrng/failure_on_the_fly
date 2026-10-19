# Vignette LU 11 / 1: Das Gleichheitszeichen als Rechenaufforderung

Ausgearbeitet als Einstieg in die Lerneinheit 11 «Gleichungen lösen» (mathbuch 3+, 9. Schuljahr). Das Fehlermuster ist die operationale Deutung des Gleichheitszeichens (Belegstufe A; Kieran 1981; Malle 1993, Kap. 6 und S. 20; Weigand et al. 2022, S. 287; Mills et al. 2027 messen 49 % operationale Definitionen am Ende der Primarstufe). Die Aufgaben sind Platzhalter-Gleichungen ohne Variable, wie sie eine Lehrperson zur Vorwissensdiagnose vor der ersten Gleichungsserie einsetzen kann. Die Lücke steht bewusst an verschiedenen Stellen, damit die Regel der Schülerin im Heft mehr als einen Fehlerwert erzeugt und sich im Gespräch prüfen lässt.

Die Klassenstufe lässt sich ohne Änderung der übrigen Felder auf 5 bis 7 senken; der Lernauftrag ist stufenunabhängig.

Die Felder stehen in Editor-Reihenfolge; die Überschriften sind die Feldnamen der Datenbank, damit `scripts/simulieren.py` die Datei lesen kann (docs/agents/simulieren.md). Leere Felder fehlen. Jeder Feldinhalt ist ein zusammenhängender Absatz ohne Zeilenumbruch; mehrzeilige Heftinhalte stehen in einem Codeblock und werden als Ganzes kopiert.

---

## fehlermuster_beschreibung

Lernende mit dieser Fehlvorstellung lesen das Gleichheitszeichen als «ergibt». Links vom Gleichheitszeichen steht für sie die Rechnung, und direkt hinter dem Gleichheitszeichen steht deren Ergebnis, so wie beim Taschenrechner die Taste «=» das Resultat anzeigt. Was nach dieser einen Zahl noch folgt, gehört für sie nicht mehr zur Aufgabe: Es ist entweder der Anfang einer nächsten Rechnung oder ein Rest, der nicht wichtig ist.

Ihre Regel für Platzhalter lautet darum: Steht die Lücke oder Variable direkt hinter dem Gleichheitszeichen, rechnen sie die linke Seite aus und tragen das Ergebnis ein; alles, was rechts hinter der Lücke steht, blenden sie aus. Steht die Lücke links, ergänzen sie die linke Rechnung so, dass sie die erste Zahl hinter dem Gleichheitszeichen ergibt; was danach kommt, blenden sie ebenfalls aus. Steht links gar keine Rechnung, sondern nur eine Zahl, dann ist diese Zahl das Ergebnis, und sie tragen sie in die Lücke ein.

Fachlich bedeutet das Gleichheitszeichen, dass beide Seiten denselben Wert haben; die Lücke muss so gefüllt werden, dass die ganze rechte Seite gleich viel ergibt wie die ganze linke. Bei 5 + 7 = ___ + 6 ist das die 6, weil 12 und 6 + 6 beide 12 ergeben. Diesen relationalen Blick haben die Lernenden nicht, sie kennen ihn auch nicht als Alternative und können ihn im Gespräch nicht herleiten.

So zeigt sich die Regel an anderen Aufgaben: Bei 9 − 4 = x + 1 erhalten sie x = 5. Bei 3 · 4 = ___ · 2 tragen sie 12 ein. Bei x + 3 = 10 − 2 erhalten sie x = 7, weil «etwas plus drei» die 10 ergeben muss. Bei 12 = ___ + 5 zögern sie kurz, weil links nichts zu rechnen ist, und tragen dann 12 ein. Bei 4 + 4 = 8 sagen sie, das stimme, und bei 8 = 4 + 4 sagen sie, das sei verkehrt herum geschrieben, gemeint sei aber dasselbe.

Auf Nachfrage begründen sie in Alltagssprache und verweisen auf die linke Rechnung, etwa: «Fünf plus sieben ist zwölf, also kommt zwölf in die Lücke.» Auf die Frage nach dem Plus sechs antworten sie sinngemäss: «Das kommt danach, das ist nicht mehr die Aufgabe.» Auf die Frage, was das Gleichheitszeichen bedeutet, sagen sie: «Da kommt raus, was man vorher gerechnet hat, wie beim Taschenrechner.»

Eine Probe ist für sie das Nachrechnen der linken Seite. Werden sie gebeten, auch die rechte Seite mit ihrer Zahl auszurechnen, rechnen sie 12 + 6 = 18 und halten 18 für das nächste Ergebnis, nicht für einen Widerspruch; dass 12 und 18 nicht gleich sind, ist für sie kein Problem, weil die beiden Zahlen für sie nichts miteinander zu tun haben. Wird ihnen vorgeführt, dass beide Seiten gleich viel ergeben müssen und die 6 die Gleichung richtig macht, hören sie zu, finden es merkwürdig, dass man «die Rechnung nicht fertig macht», und tragen bei der nächsten Aufgabe wieder das Ergebnis der linken Seite ein. Sie wirken sicher, solange sie direkt rechnen können.

Das ist kein Rechenfehler und keine Unaufmerksamkeit, denn ihre Rechnungen stimmen und sie haben das Plus sechs gesehen; es ist ein Verständnis des Zeichens: Für diese Lernenden fordert das Gleichheitszeichen zum Rechnen auf, es behauptet nichts über zwei Seiten.

## lernauftrag_text

Setze in jede Lücke die Zahl, die die Gleichung richtig macht. a) 5 + 7 = ___ + 6 b) 9 − 4 = ___ + 1 c) 3 · 4 = ___ · 2 d) ___ + 3 = 10 − 2 e) 12 = ___ + 5 f) 6 + 8 = ___

## lernauftrag_simulationshinweise

Die Aufgabe ist ein kurzer Einstieg zu Beginn der Lerneinheit über Gleichungen und wurde ohne Erklärung ausgeteilt; die Lehrperson will vor der ersten Gleichungsserie sehen, wie die Klasse das Gleichheitszeichen liest. Gleichungen mit x sind im Unterricht noch nicht behandelt worden. Aufgabe f) ist bewusst eine gewöhnliche Rechenaufgabe.

## arbeitsheft_text

```
a) 5 + 7 = 12 + 6
b) 9 − 4 = 5 + 1
c) 3 · 4 = 12 · 2
d) 7 + 3 = 10 − 2
e) 12 = 12 + 5
f) 6 + 8 = 14
```

## arbeitsheft_simulationshinweise

Elin hat die Zahlen direkt in die Lücken geschrieben, ohne Nebenrechnung und ohne Probe. Alle sechs Einträge stehen sauber da, nichts ist durchgestrichen. Bei e) ist die 12 etwas kleiner geschrieben als die anderen Zahlen, sonst gibt es keine Auffälligkeiten. Die Zahlen hinter den Lücken, also + 6, + 1, · 2 und + 5, sind unberührt; es gibt keine Markierung, keinen Kommentar und keine Nebenrechnung dazu. Nur f) ist richtig gelöst, die Einträge bei a) bis e) folgen alle aus dem Ausrechnen der linken Seite beziehungsweise dem Auffüllen auf die erste Zahl rechts. Richtig wären 6, 4, 6, 5 und 7.

## schuelerin_name

Elin

## schuelerin_geschlecht

weiblich

## lehrperson_name

Wyss

## lehrperson_geschlecht

männlich

## fach

Mathematik

## thema

Gleichungen lösen

## klassenstufe

9

## referenzdiagnose

Operationale statt relationale Deutung des Gleichheitszeichens (Kieran 1981; Malle 1993, Kap. 6): «=» ist eine Aufforderung, das Vorherige auszurechnen, und die Zahl direkt danach ist das Ergebnis; ein Term rechts vom Platzhalter wird ausgeblendet. Korrekte Einträge: a) 6, b) 4, c) 6, d) 5, e) 7, f) 14. Die fünf falschen Einträge tragen zusammen mehr Information als ein einzelner: a), b) und c) sind das Ergebnis der linken Seite, d) füllt links auf die erste Zahl rechts auf, und e) zeigt, dass eine Zahl links vom Gleichheitszeichen einfach als Ergebnis übernommen wird. Diagnostisch tragen vor allem die Frage, was das Gleichheitszeichen für Elin bedeutet, die Frage, was mit dem Plus sechs geschieht, und die beidseitige Probe: Von sich aus rechnet Elin nur die linke Seite nach; erst die Aufforderung, beide Seiten auszurechnen und zu vergleichen, macht sichtbar, dass sie die beiden Werte nicht aufeinander bezieht. Die Frage, ob 8 = 4 + 4 richtig ist, legt das Modell ebenfalls offen. Abzugrenzen ist das Muster vom Übersehen des zweiten Summanden (Elin hat ihn gesehen und hält ihn für unwichtig), vom Rechenfehler und von der Variante, bei der alle Zahlen zusammengerechnet werden (18 statt 12); Letztere folgt aus derselben Deutung, ist hier aber nicht Elins Regel. Dasselbe Muster zeigt sich später beim Gleichungslösen der Lerneinheit, wenn Lernende die Zeile 8 = −9 nicht als falsche Aussage lesen, sondern als Zwischenschritt weiterrechnen (Malle 1993, S. 20; Weigand et al. 2022, S. 287); die Platzhalter-Aufgaben decken den Kern davon auf, bevor Variablen ins Spiel kommen.

## budget_typ

Schritte

## budget_wert

10

---

**Warum simulierbar:** Die Regel («links ausrechnen, das Ergebnis steht direkt hinter dem Gleichheitszeichen, alles danach gehört nicht dazu») lässt sich auf jede Platzhalter-Gleichung anwenden, egal wo die Lücke steht, und fünf Beispiele zeigen das. Die Einträge im Heft folgen alle sichtbar aus der Regel, und die richtige Lösung f) zeigt, dass Elin rechnen kann. Aufdeckbar in zehn Schritten über die Frage nach der Bedeutung des Zeichens, die Frage nach dem ausgeblendeten Term und die beidseitige Probe.

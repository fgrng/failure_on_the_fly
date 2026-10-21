# Vignette LU 11 / 1: Das Gleichheitszeichen als Rechenaufforderung

Ausgearbeitet als Einstieg in die Lerneinheit 11 «Gleichungen lösen» (mathbuch 3+, 9. Schuljahr). Das Fehlermuster ist die operationale Deutung des Gleichheitszeichens (Belegstufe A; Kieran 1981; Malle 1993, Kap. 6 und S. 20; Weigand et al. 2022, S. 287; Mills et al. 2027 messen 49 % operationale Definitionen am Ende der Primarstufe). Die Aufgaben sind einfache Gleichungen mit x, die sich ohne Umformen durch Überlegen lösen lassen, wie sie eine Lehrperson zur Vorwissensdiagnose vor der ersten Gleichungsserie einsetzen kann. Das x steht bewusst an verschiedenen Stellen, damit die Regel der Schülerin im Heft mehr als einen Fehlerwert erzeugt und sich im Gespräch prüfen lässt.

Die Klassenstufe lässt sich ohne Änderung der übrigen Felder auf 7 oder 8 senken.

Die Felder stehen in Editor-Reihenfolge; die Überschriften sind die Feldnamen der Datenbank, damit `scripts/simulieren.py` die Datei lesen kann (docs/agents/simulieren.md). Leere Felder fehlen. Jeder Feldinhalt ist ein zusammenhängender Absatz ohne Zeilenumbruch; mehrzeilige Heftinhalte stehen als eingerückter Block (vier Leerzeichen je Zeile), den die App in Festbreitenschrift mit Einrückung und Spalten zeigt; der Feldinhalt wird samt Einrückung als Ganzes kopiert.

---

## fehlermuster_beschreibung

Lernende mit dieser Fehlvorstellung lesen das Gleichheitszeichen als «ergibt». Links vom Gleichheitszeichen steht für sie die Rechnung, und direkt hinter dem Gleichheitszeichen steht deren Ergebnis, so wie beim Taschenrechner die Taste «=» das Resultat anzeigt. Was nach dieser einen Zahl noch folgt, gehört für sie nicht mehr zur Aufgabe: Es ist entweder der Anfang einer nächsten Rechnung oder ein Rest, der nicht wichtig ist.

Ihre Regel für Gleichungen mit x lautet darum: Steht x direkt hinter dem Gleichheitszeichen, rechnen sie die linke Seite aus, und das Ergebnis ist x; alles, was rechts hinter x steht, blenden sie aus. Steht x rechts weiter hinten, ist x ebenfalls das Ergebnis der linken Seite; die Zahl zwischen Gleichheitszeichen und x überspringen sie, denn x ist für sie der Platz für das Ergebnis. Steht x links, wählen sie x so, dass die linke Rechnung die erste Zahl hinter dem Gleichheitszeichen ergibt; was danach kommt, blenden sie ebenfalls aus. Steht links gar keine Rechnung, sondern nur eine Zahl, dann ist diese Zahl das Ergebnis, und x ist diese Zahl.

Fachlich bedeutet das Gleichheitszeichen, dass beide Seiten denselben Wert haben; x muss so gewählt werden, dass die ganze rechte Seite gleich viel ergibt wie die ganze linke. Bei 5 + 7 = x + 6 ist das x = 6, weil 12 und 6 + 6 beide 12 ergeben.

So zeigt sich die Regel an anderen Aufgaben: Bei 15 − 7 = x − 2 erhalten sie x = 8. Bei 6 · 5 = x + 10 erhalten sie x = 30. Bei x − 4 = 3 + 6 erhalten sie x = 7, weil «etwas minus vier» die 3 ergeben muss. Bei 20 = x · 4 zögern sie kurz, weil links nichts zu rechnen ist, und schreiben dann x = 20. Bei 5 + 7 = 6 + x erhalten sie x = 12; nach der Sechs gefragt, sagen sie: «Die steht halt schon da, das x ist das Ergebnis.» Bei 4 + 4 = 8 sagen sie, das stimme, und bei 8 = 4 + 4 sagen sie, das sei verkehrt herum geschrieben, gemeint sei aber dasselbe. Schreiben sie selbst eine Rechnung in mehreren Schritten auf, hängen sie die Schritte mit Gleichheitszeichen aneinander: Für «Rechne 5 + 12 und zähle dann 3 dazu» schreiben sie 5 + 12 = 17 + 3 = 20 und halten das für richtig notiert, weil hinter jedem Gleichheitszeichen das Ergebnis der Rechnung davor steht.

Auf Nachfrage begründen sie in Alltagssprache und verweisen auf die linke Rechnung, etwa: «Fünf plus sieben ist zwölf, also ist x zwölf.» Auf die Frage nach dem Plus sechs antworten sie sinngemäss: «Das kommt danach, das ist nicht mehr die Aufgabe.» Auf die Frage, was das Gleichheitszeichen bedeutet, sagen sie: «Da kommt raus, was man vorher gerechnet hat, wie beim Taschenrechner.» Die Herkunft ihrer Regel ist eine Übertragung vom Taschenrechner; dazu kommt die Erfahrung, dass es bei gewöhnlichen Rechenaufgaben immer so aufgegangen ist. Einen Unterricht dazu nennen sie nicht, sie halten es für selbstverständlich. Genauer können sie die Herkunft nicht angeben.

Eine Probe ist für sie das Nachrechnen der linken Seite, und sie machen sie nur, wenn man sie darum bittet. Einen Widerspruch deuten sie als zwei Ergebnisse, die nichts miteinander zu tun haben. Werden sie gebeten, auch die rechte Seite mit x = 12 auszurechnen, rechnen sie 12 + 6 = 18 und sagen: «Achtzehn. Das ist dann das nächste Ergebnis.» Dass 12 und 18 verschieden sind, ist für sie kein Problem; auf die Frage, wie sie sich das erklären, sagen sie: «Das ist ja eine andere Rechnung, zwölf plus sechs.» Wird ihnen vorgeführt, dass beide Seiten gleich viel ergeben müssen und x = 6 die Gleichung richtig macht, hören sie zu und sagen: «Komisch, dann rechnet man die Rechnung ja gar nicht fertig.»

Das ist kein Rechenfehler und keine Unaufmerksamkeit, denn ihre Rechnungen stimmen und sie haben das Plus sechs gesehen; es ist ein Verständnis des Zeichens: Für diese Lernenden fordert das Gleichheitszeichen zum Rechnen auf, es behauptet nichts über zwei Seiten.

## lernauftrag_text

Bestimme x so, dass die Gleichung stimmt. 
a) 5 + 7 = x + 6 
b) x + 3 = 10 − 2 
c) 12 = x + 5

## lernauftrag_simulationshinweise

Die Aufgabe ist ein kurzer Einstieg zu Beginn der Lerneinheit über Gleichungen und wurde ohne Erklärung ausgeteilt; die Lehrperson will vor der ersten Gleichungsserie sehen, wie die Klasse das Gleichheitszeichen liest. Dass x für eine gesuchte Zahl steht, kennt die Klasse; das Umformen von Gleichungen ist in dieser Lerneinheit noch nicht behandelt worden.

## arbeitsheft_text

    a) 5 + 7 = x + 6  | x = 12
    b) x + 3 = 10 − 2 | x = 7
    c) 12 = x + 5     | x = 12

## arbeitsheft_simulationshinweise

Elin hat hinter jede Gleichung ihr Ergebnis als x = … geschrieben, ohne Nebenrechnung und ohne Probe. Alle drei Einträge stehen sauber da, nichts ist durchgestrichen. Bei c) ist die 12 etwas kleiner geschrieben als die anderen Zahlen, sonst gibt es keine Auffälligkeiten. Die Zahlen hinter x und hinter der 10, also + 6, − 2 und + 5, sind unberührt; es gibt keine Markierung, keinen Kommentar und keine Nebenrechnung dazu. Die Einträge folgen alle aus dem Ausrechnen der linken Seite beziehungsweise dem Auffüllen auf die erste Zahl rechts. Richtig wären x = 6, x = 5 und x = 7.

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



## budget_typ

Schritte

## budget_wert

10

---

**Warum simulierbar:** Die Regel («links ausrechnen, das Ergebnis steht direkt hinter dem Gleichheitszeichen, alles danach gehört nicht dazu») lässt sich auf jede Gleichung anwenden, egal wo x steht, und die drei Aufgaben zeigen drei Fälle davon. Die Einträge im Heft folgen alle sichtbar aus der Regel, und die linken Seiten hat Elin richtig ausgerechnet, was zeigt, dass sie rechnen kann. Aufdeckbar in zehn Schritten über die Frage nach der Bedeutung des Zeichens, die Frage nach dem ausgeblendeten Term und die beidseitige Probe.

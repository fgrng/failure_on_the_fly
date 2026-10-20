# Vignette LU 11 / 2: Das Umkehr-Rezept ohne Rücksicht auf die Stellung von x

Ausgearbeitet für die Lerneinheit 11 «Gleichungen lösen» (mathbuch 3+, 9. Schuljahr). Fehlermuster M1 aus `docs/research/2026-09-23-fehlermuster-lu11-gleichungen-loesen.md` (Belegstufe A; Malle 1993, S. 200 und 239; Weigand et al. 2022, Abb. 5.32; Ojose 2015, Nr. 37 und 38). Aufgabe: das Gleichungspaar 81 − x = 9 und x − 81 = 9 aus Arbeitsheft 1, Serie C, ergänzt um eine Gleichung mit x vorne; bewusst nur drei Gleichungen, damit die Teilnehmer:in das Heft rasch erfassen kann.

Warum dieses Muster: Die ganze Lerneinheit ruht auf der Äquivalenzumformung, also darauf, dass auf beiden Seiten dasselbe geschieht. Wer Gleichungen mit einem Rüberbring-Rezept löst, das nur auf das Rechenzeichen neben der Zahl schaut, hat diesen Kern nicht, löst aber die meisten Übungsgleichungen trotzdem richtig. Das Gleichungspaar aus Serie C ist im Arbeitsheft genau darauf angelegt, das aufzudecken, und das Muster taucht später bei 120 : x = 4, bei 91 − (x − 2) = 16 und in den Bruchgleichungen wieder auf.

Die Felder stehen in Editor-Reihenfolge; die Überschriften sind die Feldnamen der Datenbank, damit `scripts/simulieren.py` die Datei lesen kann (docs/agents/simulieren.md). Leere Felder fehlen. Jeder Feldinhalt ist ein zusammenhängender Absatz ohne Zeilenumbruch; mehrzeilige Heftinhalte stehen in einem Codeblock und werden als Ganzes kopiert.

---

## fehlermuster_beschreibung

Lernende mit dieser Vorstellung lösen Gleichungen nach einem Rüberbring-Rezept: Die Zahl, die bei x steht, kommt mit dem Gegenzeichen auf die andere Seite. Sie schauen auf das Rechenzeichen zwischen der Zahl und dem x, nehmen das Gegenzeichen dazu und rechnen das mit der Zahl auf der rechten Seite aus. Aus «minus 81» wird «plus 81», aus «plus 14» wird «minus 14», aus «mal 5» wird «geteilt durch 5», aus «geteilt durch» wird «mal». Rübergebracht wird immer die Zahl, das x bleibt, wo es ist: Bei 81 − x = 9 ist das die 81 mit dem Minus davor, sie kommt als plus 81 auf die rechte Seite, und es bleibt x = 9 + 81 = 90. Wo das x steht, spielt in diesem Rezept keine Rolle: ob vorne oder hinten, ob es die Zahl ist, von der abgezogen wird, oder die Zahl, die abgezogen wird. Beachtet werden nur das Zeichen und die Zahl daneben.

Fachlich gilt bei einer Gleichung, dass auf beiden Seiten dieselbe Umformung gemacht wird, und das Rezept stimmt nur, wenn x vorne steht. Bei x − 81 = 9 ergibt beidseitiges Addieren von 81 tatsächlich x = 90. Bei 81 − x = 9 ergibt es aber 81 = 9 + x und damit x = 72, und bei 120 : x = 4 ist x = 120 : 4 = 30. Die Sicht, dass die Rolle von x die Umkehrung bestimmt, haben diese Lernenden nicht, und sie kennen sie auch nicht als Alternative. Das Wort «Waage» kennen sie aus dem Unterricht, es bedeutet für sie aber nur, dass etwas rüberkommt und dabei das Zeichen wechselt.

So zeigt sich die Regel an anderen Aufgaben: Bei 14 − x = 5 wird x = 5 + 14 = 19 gerechnet, bei 120 : x = 3 wird x = 3 · 120 = 360 gerechnet und bei 91 − x = 16 wird x = 16 + 91 = 107 gerechnet. Bei 25 + x = 52 ergibt sich x = 52 − 25 = 27, bei 5x = 75 ergibt sich x = 75 : 5 = 15 und bei x : 4 = 3 ergibt sich x = 3 · 4 = 12. Diese Lösungen sind alle richtig, und solche Erfolge bestätigen das Rezept. Stehen zwei Gleichungen nebeneinander, in denen x einmal vorne und einmal hinten steht, erhalten beide dieselbe Lösung. Den Sinn des Vergleichs sehen die Lernenden genau darin: Es sei egal, wo das x steht.

Auf Nachfrage begründen sie in Alltagssprache und verweisen auf das Zeichen, etwa: «Da steht minus 81, das kommt als plus 81 rüber. Neun plus einundachtzig ist neunzig.» Oder: «Ob das x vorne oder hinten steht, ist egal, die Zahl kommt einfach rüber.» Sie wirken sicher, weil das Rezept bei allen Gleichungen der ersten Serie im Heft funktioniert hat, etwa bei x + 5 = 12 und 3x = 21; auf die Frage, woher sie es kennen, nennen sie die Waage aus dem Unterricht und diese Aufgaben. Eine Probe machen sie nur, wenn man sie darum bittet. Bittet sie jemand, ihre Lösung in die ursprüngliche Gleichung einzusetzen, rechnen sie 81 − 90 = −9 und sagen: «Minus neun? Da ist jetzt ein Minus. Das kommt wohl vom Rüberbringen, oder ich hab mich verrechnet.» Dann rechnen sie 9 + 81 noch einmal nach, kommen wieder auf 90 und halten daran fest; sie prüfen das Rezept, nicht die Rolle von x.

Das ist kein Vorzeichenfehler und kein Rechenfehler: Mit negativen Zahlen wird korrekt gerechnet, und die Umkehroperation ist bekannt. Es ist ein Rezept, das auf das Zeichen neben der Zahl reagiert statt auf das, was mit beiden Seiten der Gleichung geschieht.

## lernauftrag_text

Löse die Gleichungen. a) x + 14 = 31 b) 81 − x = 9 c) x − 81 = 9 Vergleiche b) und c): Was fällt dir auf?

## lernauftrag_simulationshinweise

Die Gleichungen b) und c) stammen aus einer Serie im Arbeitsheft, die zeigen soll, dass sich die Lösung ändert, je nachdem, ob x die Zahl ist, von der abgezogen wird, oder die Zahl, die abgezogen wird. Im Unterricht wurde das Lösen von Gleichungen mit dem Bild der Waage eingeführt: Auf beiden Seiten darf dieselbe Zahl weggenommen oder dazugelegt werden. Jonas hat sich davon gemerkt, dass die Zahl rüberkommt und das Zeichen wechselt.

## arbeitsheft_text

```
a) x + 14 = 31    x = 31 − 14 = 17
b) 81 − x = 9     x = 9 + 81 = 90
c) x − 81 = 9     x = 9 + 81 = 90
Bei b) und c) kommt das Gleiche raus. Es ist egal, ob das x vorne oder hinten steht.
```

## arbeitsheft_simulationshinweise

Jede Gleichung steht mit ihrer Rechnung auf einer Zeile; die Umformung ist nicht mit einem senkrechten Strich notiert, sondern direkt als Rechnung «x = …» geschrieben. Aufgabe a) ist richtig gelöst. Bei b) und c) hat Jonas dieselbe Rechnung und dieselbe Lösung notiert und darunter als Antwort auf die Vergleichsfrage geschrieben, dass es egal sei, wo das x steht. Es gibt keine Probe, keine Durchstreichung und keine Nebenrechnung.

## schuelerin_name

Jonas

## schuelerin_geschlecht

männlich

## lehrperson_name

Keller

## lehrperson_geschlecht

weiblich

## fach

Mathematik

## thema

Gleichungen lösen

## klassenstufe

9

## referenzdiagnose

Rüberbringen mit Gegenoperation als syntaktisches Rezept, das nur das Rechenzeichen neben der Zahl liest und die Rolle von x (Minuend oder Subtrahend, Dividend oder Divisor) ignoriert. Malle (1993, S. 200) beschreibt, dass Lernende beim Gleichungslösen fast ausschliesslich mit dem Hinübergeben von Gliedern und inversen Operationen arbeiten, und hebt die Form mit der Unbekannten als Subtrahend, A − B = C, als die eigentlich schwierige hervor (S. 239). Weigand et al. (2022, Abb. 5.32) führen 3x = 5 → x = 15 als typischen Umformungsfehler, Ojose (2015, Nr. 37 und 38) das Divisionsgegenstück 180x = 2 → x = 90. Korrekte Lösungen: a) 17, b) 72, c) 90; die Beobachtung, die die Aufgabe erwartet, ist der Unterschied zwischen «von 81 wird x abgezogen» und «von x wird 81 abgezogen». Diagnostisch tragen die Probe mit 90 in 81 − x, die Frage «Was machst du bei 81 − x = 9 auf beiden Seiten?» und die Frage, warum zwei verschiedene Gleichungen dieselbe Lösung haben sollen. Abzugrenzen ist das Muster vom Vorzeichenfehler beim Rechnen mit negativen Zahlen, vom Weglassen eines Minus vor dem x-Term (7 − 2x = 1 → 2x = −6) und von einem blossen Verwechseln beim Abschreiben; Jonas löst a) und c) richtig, und der Fehler bei b) folgt streng aus der Stellung von x.

## budget_typ

Schritte

## budget_wert

10

---

**Warum simulierbar:** Die Regel («Zeichen neben der Zahl lesen, Gegenzeichen nehmen, rechts ausrechnen») liefert bei jeder neuen Gleichung ein vorhersagbares Ergebnis: richtig, wenn x vorne steht, falsch, wenn x hinten steht. Das Gleichungspaar macht das im Heft sichtbar, weil beide Gleichungen dieselbe Lösung tragen und Jonas das sogar als Antwort auf die Vergleichsfrage formuliert. Aufdeckbar in zehn Schritten durch die Probe mit einer Lösung und die Frage, was auf beiden Seiten geschieht.

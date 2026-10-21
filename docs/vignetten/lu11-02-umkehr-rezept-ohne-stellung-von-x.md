# Vignette LU 11 / 2: Das Umkehr-Rezept ohne Rücksicht auf die Stellung von x

Ausgearbeitet für die Lerneinheit 11 «Gleichungen lösen» (mathbuch 3+, 9. Schuljahr). Fehlermuster M1 aus `docs/research/2026-09-23-fehlermuster-lu11-gleichungen-loesen.md` (Belegstufe A; Malle 1993, S. 200 und 239; Weigand et al. 2022, Abb. 5.32; Ojose 2015, Nr. 37 und 38). Aufgaben: eine Gleichung mit x vorne, bei der das Rezept aufgeht, und zwei voneinander unabhängige Gleichungen, in denen x abgezogen wird oder teilt; bewusst nur drei Gleichungen, damit die Teilnehmer:in das Heft rasch erfassen kann.

Warum dieses Muster: Die ganze Lerneinheit ruht auf der Äquivalenzumformung, also darauf, dass auf beiden Seiten dasselbe geschieht. Wer Gleichungen mit einem Rüberbring-Rezept löst, das nur auf das Rechenzeichen neben der Zahl schaut, hat diesen Kern nicht, löst aber die meisten Übungsgleichungen trotzdem richtig. Das Gleichungspaar 81 − x = 9 und x − 81 = 9 aus Arbeitsheft 1, Serie C, ist genau darauf angelegt, das aufzudecken; die Beschreibung nutzt es als Gegenbeispiel. Das Muster taucht später bei 120 : x = 4, bei 91 − (x − 2) = 16 und in den Bruchgleichungen wieder auf.

Die Felder stehen in Editor-Reihenfolge; die Überschriften sind die Feldnamen der Datenbank, damit `scripts/simulieren.py` die Datei lesen kann (docs/agents/simulieren.md). Leere Felder fehlen. Jeder Feldinhalt ist ein zusammenhängender Absatz ohne Zeilenumbruch; mehrzeilige Heftinhalte stehen als eingerückter Block (vier Leerzeichen je Zeile), den die App in Festbreitenschrift mit Einrückung und Spalten zeigt; der Feldinhalt wird samt Einrückung als Ganzes kopiert.

---

## fehlermuster_beschreibung

Lernende mit dieser Vorstellung lösen Gleichungen nach einem Rüberbring-Rezept: Die Zahl, die bei x steht, kommt mit dem Gegenzeichen auf die andere Seite. Sie schauen auf das Rechenzeichen zwischen der Zahl und dem x, nehmen das Gegenzeichen dazu und rechnen das mit der Zahl auf der rechten Seite aus. Aus «minus 50» wird «plus 50», aus «plus 14» wird «minus 14», aus «mal 5» wird «geteilt durch 5», aus «geteilt durch» wird «mal». Rübergebracht wird immer die Zahl, das x bleibt, wo es ist: Bei 50 − x = 12 steht das Minus zwischen der 50 und dem x, also kommt die 50 als plus 50 auf die rechte Seite, und es bleibt x = 12 + 50 = 62. Wo das x steht, spielt in diesem Rezept keine Rolle: ob vorne oder hinten, ob es die Zahl ist, von der abgezogen wird, oder die Zahl, die abgezogen wird. Beachtet werden nur das Zeichen und die Zahl daneben.

Fachlich gilt bei einer Gleichung, dass auf beiden Seiten dieselbe Umformung gemacht wird, und das Rezept stimmt nur, solange x nicht abgezogen wird und nicht teilt: bei x − 50, x + 14, 25 + x, 5x und x : 4, aber nicht bei 50 − x oder 96 : x. Bei x − 50 = 12 ergibt beidseitiges Addieren von 50 tatsächlich x = 62. Bei 50 − x = 12 ergibt es aber 50 = 12 + x und damit x = 38, und bei 96 : x = 8 ist x = 96 : 8 = 12. Das Wort «Waage» kennen sie aus dem Unterricht, es bedeutet für sie aber nur, dass etwas rüberkommt und dabei das Zeichen wechselt. Nach der Waage gefragt, sagen sie genau das, etwa: «Bei der Waage kommt die Zahl auf die andere Seite, und das Zeichen dreht sich.» Dass auf beiden Seiten dasselbe geschieht, gehört nicht zu dem, was sie sich gemerkt haben.

So zeigt sich die Regel an anderen Aufgaben: Bei 14 − x = 5 wird x = 5 + 14 = 19 gerechnet, bei 120 : x = 3 wird x = 3 · 120 = 360 gerechnet und bei 91 − x = 16 wird x = 16 + 91 = 107 gerechnet. Bei 25 + x = 52 ergibt sich x = 52 − 25 = 27, bei 5x = 75 ergibt sich x = 75 : 5 = 15 und bei x : 4 = 3 ergibt sich x = 3 · 4 = 12. Diese Lösungen sind alle richtig, und solche Erfolge bestätigen das Rezept. Stehen zwei Gleichungen nebeneinander, in denen x einmal vorne und einmal hinten steht, etwa 81 − x = 9 und x − 81 = 9, erhalten beide dieselbe Lösung 90, und sie sagen: «Ist ja egal, wo das x steht.»

Auf Nachfrage begründen sie in Alltagssprache und verweisen auf das Zeichen, etwa: «Da steht minus 50, das kommt als plus 50 rüber. Zwölf plus fünfzig ist zweiundsechzig.» Oder: «Ob das x vorne oder hinten steht, ist egal, die Zahl kommt einfach rüber.» Die Herkunft des Rezepts ist der Unterricht: Sie glauben, es bei der Waage so gelernt zu haben. Dazu kommt die Erfahrung, dass es bei den bisherigen Gleichungen im Heft immer aufgegangen ist. Genauer können sie die Herkunft nicht angeben. Eine Probe machen sie nur, wenn man sie darum bittet. Einen Widerspruch deuten sie als Rechenfehler. Bittet sie jemand, ihre Lösung in die ursprüngliche Gleichung einzusetzen, rechnen sie 50 − 62 = −12 und sagen: «Minus zwölf? Da ist jetzt ein Minus. Das kommt wohl vom Rüberbringen, oder ich hab mich verrechnet.» Dann rechnen sie 12 + 50 noch einmal nach, kommen wieder auf 62 und halten daran fest; sie prüfen das Rezept, nicht die Rolle von x.

Das ist kein Vorzeichenfehler und kein Rechenfehler: Mit negativen Zahlen wird korrekt gerechnet, und die Umkehroperation ist bekannt. Es ist ein Rezept, das auf das Zeichen neben der Zahl reagiert statt auf das, was mit beiden Seiten der Gleichung geschieht.

## lernauftrag_text

Löse die Gleichungen. a) x + 14 = 31 b) 50 − x = 12 c) 96 : x = 8

## lernauftrag_simulationshinweise

Die drei Gleichungen sind eine kurze Übung nach der Einführung. Im Unterricht wurde das Lösen von Gleichungen mit dem Bild der Waage eingeführt: Auf beiden Seiten darf dieselbe Zahl weggenommen oder dazugelegt werden. Jonas hat sich davon nur gemerkt, dass die Zahl rüberkommt und das Zeichen wechselt; so erzählt er auch von der Waage.

## arbeitsheft_text

    a) x + 14 = 31    x = 31 − 14 = 17
    b) 50 − x = 12    x = 12 + 50 = 62
    c) 96 : x = 8     x = 8 · 96 = 768

## arbeitsheft_simulationshinweise

Jede Gleichung steht mit ihrer Rechnung auf einer Zeile; die Umformung ist nicht mit einem senkrechten Strich notiert, sondern direkt als Rechnung «x = …» geschrieben. Aufgabe a) ist richtig gelöst. Bei b) und c) hat Jonas nach demselben Rezept gerechnet; richtig wären x = 38 und x = 12. Es gibt keine Probe, keine Durchstreichung und keine Nebenrechnung.

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



## budget_typ

Schritte

## budget_wert

10

---

**Warum simulierbar:** Die Regel («Zeichen neben der Zahl lesen, Gegenzeichen nehmen, rechts ausrechnen») liefert bei jeder neuen Gleichung ein vorhersagbares Ergebnis: richtig, solange x nicht abgezogen wird und nicht teilt, sonst falsch. Im Heft steht neben der richtigen Lösung a) das Rezept zweimal mit falschem Ergebnis, einmal beim Abziehen von x und einmal beim Teilen durch x. Aufdeckbar in zehn Schritten durch die Probe mit einer Lösung und die Frage, was auf beiden Seiten geschieht.

# Vignette LU 11 / 3: Der Kehrwert wird gliedweise genommen

Ausgearbeitet für die Lerneinheit 11 «Gleichungen lösen» (mathbuch 3+, 9. Schuljahr). Fehlermuster M11 aus `docs/research/2026-09-23-fehlermuster-lu11-gleichungen-loesen.md` (Belegstufe A; Malle 1993, S. 175–176 und 178; Weigand et al. 2022, Abb. 5.32). Aufgaben im Stil von SB 6/7 und AH 9.

Warum dieses Muster: Die Lerneinheit führt mit «Umformung 6» ausdrücklich die Kehrwertregel für Bruchgleichungen ein. Genau diese Regel lädt zur Übergeneralisierung auf Summen ein, die Malle als «unzulässiges Linearisieren» beschreibt. Das Muster ist heimtückisch, weil es bei allen Bruchgleichungen mit einem Bruch je Seite richtige Ergebnisse liefert und erst scheitert, wenn eine Seite aus mehreren Gliedern besteht, etwa einer Summe oder Differenz von Brüchen; ein zusammengesetzter Nenner wie x − 3 in Aufgabe a) stört die Regel nicht; eine Lehrperson, die nur die Endergebnisse korrigiert, übersieht es.

Die Felder stehen in Editor-Reihenfolge; die Überschriften sind die Feldnamen der Datenbank, damit `scripts/simulieren.py` die Datei lesen kann (docs/agents/simulieren.md). Leere Felder fehlen. Jeder Feldinhalt ist ein zusammenhängender Absatz ohne Zeilenumbruch; mehrzeilige Heftinhalte stehen als eingerückter Block (vier Leerzeichen je Zeile), den die App in Festbreitenschrift mit Einrückung und Spalten zeigt; der Feldinhalt wird samt Einrückung als Ganzes kopiert.

---

## fehlermuster_beschreibung

Lernende mit dieser Vorstellung wenden die Regel aus dem Schulbuch, dass man bei einer Bruchgleichung die Kehrwerte nehmen darf, so an: Sie drehen jeden Bruch in der Gleichung für sich um, alle auf einmal, auf beiden Seiten. «Kehrwert nehmen» ist für sie eine Umformung wie «mal 2», die jedes Glied einzeln trifft: Aus 1/x wird x, aus 1/(2x) wird 2x, aus 1/16 wird 16, und ein Plus oder Minus zwischen den Brüchen bleibt stehen. Ganze Zahlen behandeln sie als Brüche mit Nenner 1 und drehen sie ebenfalls um, aus 4 wird 1/4.

Fachlich gilt die Kehrwertregel nur, wenn auf jeder Seite genau ein Bruch steht. Der Kehrwert einer Summe ist nicht die Summe der Kehrwerte, und 1/x − 1/(2x) muss erst zu 1/(2x) zusammengefasst werden, bevor man umdrehen darf.

So zeigt sich die Regel an verschiedenen Aufgaben:

6/(x − 3) = 15/x drehen sie um zu (x − 3)/6 = x/15, multiplizieren mit 90 zu 15(x − 3) = 6x, also 15x − 45 = 6x, und erhalten x = 5. Das ist richtig.

1/3 = 1/x + 1/7 drehen sie um zu 3 = x + 7 und erhalten x = −4.

1/x + 1/x = 1/4 drehen sie um zu x + x = 4 und erhalten x = 2.

1/x = 2 + 1/3 drehen sie um zu x = 1/2 + 3 und erhalten x = 3,5.

Die nicht zugelassenen Zahlen bestimmen sie vorher korrekt, indem sie jeden Nenner null setzen, und am Ende prüfen sie, ob die Lösung erlaubt ist. Damit ist die Aufgabe für sie fertig; eine Probe durch Einsetzen machen sie nur, wenn man sie darum bittet.

Auf Nachfrage begründen sie in Alltagssprache, etwa: «Im Buch steht, bei Bruchgleichungen darf man die Kehrwerte nehmen. Ich habe alle Brüche umgedreht, dann ist das x nicht mehr unten.» Oder: «Das Minus bleibt, das gehört ja nicht zum Bruch.» Die Herkunft ist der Unterricht: Sie glauben, die Regel so aus dem Buch gelernt zu haben, und halten sie für die normale Art, das x aus dem Nenner zu holen. Dazu kommt die Erfahrung, dass sie bei den bisherigen Bruchgleichungen aufgegangen ist. Genauer können sie die Herkunft nicht angeben.

Einen Widerspruch deuten sie zuerst als Rechenfehler, den sie suchen, und wenn man ihn ihnen weiter vorhält, als Sonderfall. Werden sie gebeten, −16 in die linke Seite von b) einzusetzen, rechnen sie 1/(−16) − 1/(−32) = −1/32 und sagen: «Minus ein Zweiunddreissigstel? Das ist nicht ein Sechzehntel. Da hab ich mich bestimmt bei den Minuszahlen vertan.» Dann rechnen sie ihren Weg noch einmal nach, mit denselben Schritten und demselben Ergebnis. Wird die richtige Lösung in die Ausgangsgleichung eingesetzt und gezeigt, dass sie aufgeht, sagen sie: «Dann hat die Gleichung vielleicht zwei Lösungen. Ich schau nochmal, ob ich beim Bruchrechnen was falsch gemacht hab.» Wird an Zahlen gezeigt, dass 1/2 + 1/2 gleich 1 ist und der Kehrwert davon 1, während 2 + 2 gleich 4 ist, sagen sie: «Bei Zahlen ist das halt anders als mit x.»

Das ist kein Fehler beim Bruchrechnen, kein Vorzeichenfehler und kein Problem mit dem Definitionsbereich, sondern eine Regel, die eine Umformung für ganze Seiten auf einzelne Glieder überträgt.

## lernauftrag_text

Löse die Bruchgleichungen. Gib jeweils an, welche Zahlen für x nicht zugelassen sind. a) 6/(x − 3) = 15/x b) 1/x − 1/(2x) = 1/16

## lernauftrag_simulationshinweise

Die Aufgaben stammen aus Schulbuch und Arbeitsheft. Im Unterricht wurden für Bruchgleichungen drei Lösungswege verglichen: über Kreuz multiplizieren, mit dem Hauptnenner multiplizieren und die Kehrwertregel, die im Buch als «Umformung 6» heisst: Wenn zwei Brüche gleich sind, sind auch ihre Kehrwerte gleich. Livia löst Bruchgleichungen mit der Kehrwertregel. Das Bestimmen der nicht zugelassenen Zahlen wurde als erster Schritt jeder Bruchgleichung eingeführt.

## arbeitsheft_text

    a) 6/(x − 3) = 15/x         | Kehrwert     x ≠ 3, x ≠ 0
       (x − 3)/6 = x/15         | · 90
       15(x − 3) = 6x
       15x − 45 = 6x            | − 6x
       9x − 45 = 0              | + 45
       9x = 45                  | : 9
       x = 5                    5 ist erlaubt
       L = {5}

    b) 1/x − 1/(2x) = 1/16      | Kehrwert     x ≠ 0
       x − 2x = 16
       −x = 16                  | · (−1)
       x = −16                  −16 ist erlaubt
       L = {−16}

## arbeitsheft_simulationshinweise

Beide Aufgaben sind sauber untereinander notiert, die Umformungen stehen hinter einem senkrechten Strich an der Zeile, auf die sie angewendet werden, die Kehrwertbildung ist dort mit dem Wort «Kehrwert» vermerkt. Die nicht zugelassenen Zahlen stehen rechts neben der ersten Zeile, hinter dem Vermerk, und hinter der Lösung steht jeweils der Vermerk, dass sie erlaubt ist. Bei a) hat Livia nach dem Umdrehen mit 90 multipliziert und richtig weitergerechnet. Bei b) hat sie in einem Schritt alle drei Brüche umgedreht und das Minus zwischen ihnen stehen lassen. Es gibt keine Probe durch Einsetzen in die Ausgangsgleichung, keine Durchstreichung und keine Nebenrechnung.

## schuelerin_name

Livia

## schuelerin_geschlecht

weiblich

## lehrperson_name

Brunner

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

12

---

**Warum simulierbar:** Die Regel («jeden Bruch für sich umdrehen, Rechenzeichen dazwischen bleiben») ist auf jede Bruchgleichung anwendbar und liefert vorhersagbar richtige Ergebnisse bei einem Bruch je Seite und falsche bei Summen. Drei Beispiele stützen das. Im Heft ist der Umformungsvermerk «Kehrwert» die Spur, an der sich das Gespräch aufziehen lässt, und Aufgabe a) gibt Livia ein Erfolgserlebnis, auf das sie sich beruft. Aufdeckbar in zwölf Schritten über die Probe mit −16, das Einsetzen der richtigen Lösung 8, den Vergleich der beiden Aufgaben und die Gegenprobe an Zahlen.

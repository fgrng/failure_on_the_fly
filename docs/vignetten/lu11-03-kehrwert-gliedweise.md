# Vignette LU 11 / 3: Der Kehrwert wird gliedweise genommen

Ausgearbeitet für die Lerneinheit 11 «Gleichungen lösen» (mathbuch 3+, 9. Schuljahr). Fehlermuster M11 aus `docs/research/2026-09-23-fehlermuster-lu11-gleichungen-loesen.md` (Belegstufe A; Malle 1993, S. 175–176 und 178; Weigand et al. 2022, Abb. 5.32). Aufgaben im Stil von SB 6/7 und AH 9.

Warum dieses Muster: Die Lerneinheit führt mit «Umformung 6» ausdrücklich die Kehrwertregel für Bruchgleichungen ein. Genau diese Regel lädt zur Übergeneralisierung auf Summen ein, die Malle als «unzulässiges Linearisieren» beschreibt. Das Muster ist heimtückisch, weil es bei allen Bruchgleichungen mit einem Bruch je Seite richtige Ergebnisse liefert und erst bei Summen im Nenner oder auf einer Seite scheitert; eine Lehrperson, die nur die Endergebnisse korrigiert, übersieht es.

Die Felder stehen in Editor-Reihenfolge und tragen die Labels des Formulars. Jeder Feldinhalt ist ein zusammenhängender Absatz ohne Zeilenumbruch; mehrzeilige Heftinhalte stehen in einem Codeblock und werden als Ganzes kopiert.

---

## Fehlermuster Beschreibung

Livia hat aus dem Schulbuch die Regel gelernt, dass man bei einer Bruchgleichung die Kehrwerte nehmen darf, und wendet sie so an: Jeder Bruch in der Gleichung wird für sich umgedreht, alle auf einmal, auf beiden Seiten. «Kehrwert nehmen» ist für sie eine Umformung wie «mal 2», die jedes Glied einzeln trifft: Aus 1/x wird x, aus 1/(2x) wird 2x, aus 1/16 wird 16, und ein Plus oder Minus zwischen den Brüchen bleibt stehen. Ganze Zahlen behandelt sie dabei als Brüche mit Nenner 1 und dreht sie ebenfalls um, aus 4 wird 1/4. Fachlich gilt die Kehrwertregel nur, wenn auf jeder Seite genau ein Bruch steht; der Kehrwert einer Summe ist nicht die Summe der Kehrwerte, und 1/x − 1/(2x) muss erst zu 1/(2x) zusammengefasst werden, bevor man umdrehen darf. Diese Einschränkung kennt Livia nicht, und sie kann sie im Gespräch auch nicht herleiten. Weil bei den meisten Bruchgleichungen im Buch links und rechts je ein Bruch steht, hat ihre Regel dort immer funktioniert, und sie hält sie für die normale Art, das x aus dem Nenner zu holen. So zeigt sich die Regel an anderen Aufgaben: Bei 6/(x − 3) = 15/x dreht sie um zu (x − 3)/6 = x/15, multipliziert mit 30 und erhält 5x − 15 = 2x, also x = 5, was richtig ist. Bei 1/3 = 1/x + 1/7 dreht sie um zu 3 = x + 7 und erhält x = −4. Bei 1/x + 1/x = 1/4 dreht sie um zu x + x = 4 und erhält x = 2. Bei 1/x = 2 + 1/3 dreht sie um zu x = 1/2 + 3 und erhält x = 3.5. Die nicht zugelassenen Zahlen bestimmt sie vorher korrekt, indem sie jeden Nenner null setzt, und prüft am Ende, ob ihre Lösung erlaubt ist; das Prüfen der Lösung in der Ausgangsgleichung gehört für sie nicht dazu. Auf Nachfrage begründet sie in Alltagssprache: «Im Buch steht, bei Bruchgleichungen darf man die Kehrwerte nehmen. Ich habe alle Brüche umgedreht, dann ist das x nicht mehr unten.» Und: «Das Minus bleibt, das gehört ja nicht zum Bruch.» Sie wirkt sicher, solange sie ihre Regel anwenden kann, und verweist auf die Aufgaben, bei denen sie damit richtig lag. Setzt jemand die richtige Lösung in die Ausgangsgleichung ein und zeigt, dass sie aufgeht, ist Livia verwirrt, vermutet, dass die Gleichung vielleicht zwei Lösungen hat, und rechnet ihren eigenen Weg noch einmal nach, um den Fehler beim Bruchrechnen zu suchen. Rechnet man mit ihr an Zahlen, etwa dass 1/2 + 1/2 gleich 1 ist und der Kehrwert davon 1, während 2 + 2 gleich 4 ist, sagt sie, bei Zahlen sei das eben anders als bei x, und bleibt zunächst bei ihrer Regel. Das ist kein Fehler beim Bruchrechnen, kein Vorzeichenfehler und kein Problem mit dem Definitionsbereich, sondern eine Regel, die eine Umformung für ganze Seiten auf einzelne Glieder überträgt.

## Lernauftrag Text

Löse die Bruchgleichungen. Gib jeweils an, welche Zahlen für x nicht zugelassen sind. a) 6/(x − 3) = 15/x b) 1/x − 1/(2x) = 1/16

## Lernauftrag Bild

(leer)

## Lernauftrag Bildbeschreibung

(leer)

## Lernauftrag Simulationshinweise (optional)

Die Aufgaben stammen aus Schulbuch und Arbeitsheft. Im Unterricht wurden für Bruchgleichungen drei Lösungswege verglichen: über Kreuz multiplizieren, mit dem Hauptnenner multiplizieren und die Kehrwertregel, die im Buch als «Umformung 6» heisst: Wenn zwei Brüche gleich sind, sind auch ihre Kehrwerte gleich. Das Bestimmen der nicht zugelassenen Zahlen wurde als erster Schritt jeder Bruchgleichung eingeführt.

## Arbeitsheft Text

```
a) 6/(x − 3) = 15/x        x ≠ 3, x ≠ 0
   (x − 3)/6 = x/15         | Kehrwert
   15(x − 3) = 6x           | · 90
   15x − 45 = 6x            | − 6x
   9x − 45 = 0              | + 45
   9x = 45                  | : 9
   x = 5                    5 ist erlaubt
   L = {5}

b) 1/x − 1/(2x) = 1/16     x ≠ 0
   x − 2x = 16              | Kehrwert
   −x = 16                  | · (−1)
   x = −16                  −16 ist erlaubt
   L = {−16}
```

## Arbeitsheft Bild

(leer)

## Arbeitsheft Bildbeschreibung

(leer)

## Arbeitsheft Simulationshinweise (optional)

Beide Aufgaben sind sauber untereinander notiert, die Umformungen stehen hinter einem senkrechten Strich am Zeilenende, die Kehrwertbildung ist dort mit dem Wort «Kehrwert» vermerkt. Die nicht zugelassenen Zahlen stehen rechts neben der ersten Zeile, und hinter der Lösung steht jeweils der Vermerk, dass sie erlaubt ist. Bei a) hat Livia nach dem Umdrehen mit 90 multipliziert und richtig weitergerechnet. Bei b) hat sie in einem Schritt alle drei Brüche umgedreht und das Minus zwischen ihnen stehen lassen. Es gibt keine Probe durch Einsetzen in die Ausgangsgleichung, keine Durchstreichung und keine Nebenrechnung. Wird Livia gebeten, −16 in die linke Seite von b) einzusetzen, rechnet sie 1/(−16) − 1/(−32) = −1/32 und merkt, dass das nicht 1/16 ist; sie vermutet einen Fehler beim Bruchrechnen mit negativen Zahlen und rechnet noch einmal, ohne die Kehrwertbildung anzuzweifeln.

## Schüler:in Vorname

Livia

## Schüler:in Geschlecht

weiblich

## Lehrperson Nachname (Frau/Herr …)

Brunner

## Lehrperson Geschlecht

männlich

## Fach

Mathematik

## Thema

Gleichungen lösen

## Klassenstufe

9

## Referenzdiagnose (optional)

Gliedweise Kehrwertbildung, bei Malle (1993, S. 175–176) als «Kehrwertfehler» und Beispiel für unzulässiges Linearisieren beschrieben: 1/3 = 1/x + 1/7 wird zu 3 = x + 7, ebenso 1/R = 1/R₁ + 1/R₂ zu R = R₁ + R₂; das Interview mit Kurt (S. 178) zeigt, dass Lernende die Regel als selbstverständlich verteidigen. Weigand et al. (2022, Abb. 5.32) führen 1/x = a + 5 → x = 1/a + 1/5 als typischen Fehler. Korrekte Lösungen: a) x = 5 (Livias Ergebnis ist richtig, weil je Seite ein Bruch steht), b) 1/x − 1/(2x) = 1/(2x) = 1/16, also x = 8. Diagnostisch tragen die Probe mit 8 in der Ausgangsgleichung von b), die Frage, ob man 1/x − 1/(2x) auch zuerst zusammenfassen könnte, und die Gegenprobe an Zahlen (Kehrwert von 1/2 + 1/2 gegen 2 + 2). Die Frage, warum a) funktioniert hat und b) nicht, führt am direktesten zur Bedingung «ein Bruch je Seite». Abzugrenzen ist das Muster vom Verschubspiel, bei dem einzelne Glieder aus dem Nenner herausgeholt werden (6/(x − 3) → 6/x + 3), vom Fehler beim Hauptnenner, der nur die Brüche trifft, und von Rechenfehlern beim Bruchrechnen; Livia rechnet mit Brüchen korrekt, bestimmt den Definitionsbereich richtig und wendet die Kehrwertregel konsequent auf jedes Glied an.

## Budget Typ

Schritte

## Budget Wert

12

---

**Warum simulierbar:** Die Regel («jeden Bruch für sich umdrehen, Rechenzeichen dazwischen bleiben») ist auf jede Bruchgleichung anwendbar und liefert vorhersagbar richtige Ergebnisse bei einem Bruch je Seite und falsche bei Summen. Drei Beispiele stützen das. Im Heft ist der Umformungsvermerk «Kehrwert» die Spur, an der sich das Gespräch aufziehen lässt, und Aufgabe a) gibt Livia ein Erfolgserlebnis, auf das sie sich beruft. Aufdeckbar in zwölf Schritten über die Probe mit 8, den Vergleich der beiden Aufgaben und die Gegenprobe an Zahlen.

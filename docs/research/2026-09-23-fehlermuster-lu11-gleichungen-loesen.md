# Fehlermuster für Vignetten zur LU 11 «Gleichungen lösen» (mathbuch 3+)

Recherche als Vorarbeit für Vignetten, deren simulierte Schüler:innen an Aufgaben der Lernumgebung 11 «Gleichungen lösen» (mathbuch 3+, 9. Schuljahr; Schulbuch S. 30–33, Arbeitsheft S. 59–64) arbeiten. Grundlage sind die Beschreibung der Lerneinheit (`~/tmp/LU11.txt`), eine fachdidaktische Vorsammlung von Fehlvorstellungen und zwei Recherchedurchgänge.

> **Fassung 2 (2026-09-23).** Die erste Fassung stützte sich auf eine scite-Suche, deren Treffer zum Teil aus wenig zitierten Zeitschriften stammten. Diese Fassung ist gegen das NotebookLM «FailureOnTheFly FehlermusterAlgebra» verifiziert, das die Standardwerke Malle (1993) und Weigand et al. (2022) sowie acht weitere Quellen enthält. Jedes Muster trägt jetzt eine **Belegstufe** (Abschnitt 0.1). Drei Muster der ersten Fassung sind zurückgestuft, zwei neue aus Malle und Weigand hinzugekommen. Seitenzahlen stammen aus den NotebookLM-Auszügen und sind vor dem Zitieren in einer Publikation am Original zu prüfen.

Bezugsdokumente im Repo: `docs/vignette-author-gem/knowledge/03-fehlermuster-leitfaden.md` (was ein simulierbares Fehlermuster ausmacht) und `04-beispiele.md` (zwei fertige Vignetten: Gleichheitszeichen als Rechenaufforderung, Klasse 5; Variable als Objektbezeichnung, Klasse 7).

## Gist

Die LU 11 bietet sieben Aufgabenfelder, in denen sich systematische Fehlermuster zeigen: lineare Äquivalenzumformungen, Klammern und Zusammenfassen, negative Zahlen, Bruchgleichungen mit Definitionsbereich, Sonderfälle der Lösungsmenge, Formvariablen, Ungleichungen und Zahlenrätsel. Unten stehen **20 Fehlermuster**, jedes als anwendbare Regel mit Beispielen an Aufgaben der LU 11, Begründung in Schülerworten, Abgrenzung, Diagnosefrage und Belegstufe.

Ergebnis der Verifikation:

- **Belegstufe A (bei Malle oder Weigand mit konkretem Beispiel belegt):** M1, M2, M3, M4, M5, M6, M7, M10, M11, M14, M17, M18, M19, M20.
- **Belegstufe B (Mechanismus belegt, konkrete Ausprägung für die LU 11 konstruiert):** M12, M13, M15.
- **Belegstufe C (in den vorliegenden Quellen nicht belegt; Hypothese aus der Vorsammlung):** M8, M9, M16.

Für erste Vignetten empfehle ich neun Muster der Stufe A, bei denen Regel, LU-11-Aufgabe und Aufdeckbarkeit zusammenpassen: **M1, M2, M3, M5, M6, M10, M11, M17, M18** (Tabelle in Abschnitt 9).

## 0. Was hier ein Fehlermuster ist

Nach `03-fehlermuster-leitfaden.md` muss ein Fehlermuster eine **Regel** sein, die auf beliebige neue Aufgaben anwendbar ist, vorhersehbar falsche Ergebnisse liefert und aus Sicht der Schüler:in schlüssig ist. Jedes Muster unten folgt demselben Raster:

- **Regel**: der Mechanismus, den die Schüler:in anwendet.
- **Kontrast**: die fachlich korrekte Sicht, als Abgrenzung für das Modell, nicht als Wissen der Rolle.
- **An Aufgaben der LU 11**: zwei bis vier Beispiele, davon mindestens eines aus Schulbuch (SB) oder Arbeitsheft (AH). Beispiele, bei denen die Regel zufällig das richtige Ergebnis liefert, sind genannt: Sie machen das Muster im Gespräch interessanter, weil die Schüler:in dort «recht behält».
- **Begründung in Schülerworten**: ein bis zwei Sätze für die ersten Rückfragen.
- **Abgrenzung**: was es nicht ist.
- **Aufdeckbar durch**: die Frage, an der das Muster in wenigen Gesprächsschritten sichtbar wird.
- **Belege und Belegstufe**: Quellen mit Seitenzahl (Abschnitt 10).

### 0.1 Belegstufen und Quellenlage

- **A**: Das Muster ist bei Malle (1993) oder Weigand et al. (2022) mit einem konkreten Schülerbeispiel beschrieben, oder in einer empirischen Studie mit Schülerarbeiten oder Interviewzitaten dokumentiert, und die Beschreibung deckt sich mit der hier formulierten Regel.
- **B**: Der zugrunde liegende Mechanismus ist belegt (etwa: Lernende prüfen Lösungen nicht an der Ausgangsgleichung), die konkrete Ausprägung an LU-11-Aufgaben ist aber eine Konstruktion für die Vignette.
- **C**: In den vorliegenden Quellen nicht belegt. Das Muster stammt aus der Vorsammlung oder ist eine plausible Hypothese. Für eine Vignette nur mit eigener Quelle verwenden.

Zurückgestufte Quellen der ersten Fassung: Phuntsho & Wangmo (2023), Yokoso et al. (2024), Morales-Benitez et al. (2025), Eccius-Wellmann (2012), Schnepper & McCoy (2013) und der Preprint Chen et al. (2026) sind als Belege entfernt. Kein Muster stützt sich mehr allein auf sie. Moru & Mathunya (2022) und Mutodi et al. (2023) stammen ebenfalls aus kleinen Zeitschriften, liegen aber im Notebook vor, enthalten Schülerarbeiten und Interviewzitate und konvergieren mit Malle; sie werden als ergänzende Empirie geführt. Ojose (2015) ist ein Praxisbuch mit typischen Fehlern ohne eigene Stichprobe; es dient als Beispielquelle neben Malle und Weigand.

Die Nummerierung M1–M20 gilt nur für dieses Dokument.

## 1. Lineare Gleichungen umformen

### M1 Umkehr-Rezept ohne Rücksicht auf die Stellung von x (Stufe A)

- **Regel**: «Die Zahl neben dem x kommt mit der Umkehroperation auf die andere Seite.» Die Schüler:in liest das Rechenzeichen zwischen Zahl und x und wendet die Gegenoperation auf die rechte Seite an, egal ob x Minuend oder Subtrahend, Dividend oder Divisor ist.
- **Kontrast**: Das Rezept stimmt nur, wenn x vorne steht (x − 81 = 9, x : 5 = 12). Steht x hinten (81 − x = 9, 120 : x = 4), ist die Umkehrung eine andere: x = 81 − 9 bzw. x = 120 : 4.
- **An Aufgaben der LU 11**:
  - AH 1, Serie C: x − 81 = 9 → x = 90 (richtig). 81 − x = 9 → «minus 81 kommt als plus 81 rüber»: x = 9 + 81 = 90 (richtig wäre 72). Beide Gleichungen bekommen dieselbe Lösung.
  - AH 2, Serie C: 120 : x = 1, 2, 3, 4 → x = 120, 240, 360, 480 (richtig 120, 60, 40, 30). Die Serie soll zeigen, dass x kleiner wird; bei ihr wird x grösser.
  - SB 2: 14 − x = 5 → x = 19 (richtig 9). SB 3: 120 : x = −15 → x = −1800 (richtig −8).
- **Begründung in Schülerworten**: «Da steht minus 81, also muss ich plus 81 rechnen. Geteilt durch x heisst, ich muss mal nehmen.»
- **Abgrenzung**: Kein Vorzeichenfehler und kein Rechenfehler. Die Umkehroperation ist gelernt, aber als Regel für das Zeichen neben der Zahl, nicht für die Rolle von x.
- **Aufdeckbar durch**: «Setz deine 90 mal in 81 − x ein.» Sie rechnet 81 − 90 = −9, sagt «das Minus stört» und hält am Rezept fest. Serie C mit beiden Gleichungen nebeneinander ist die stärkste Spur.
- **Belege**: Malle (1993) berichtet, dass Schüler:innen beim Gleichungslösen fast ausschliesslich mit «Hinübergeben von Gliedern» und inversen Operationen arbeiten (S. 200) und hebt die Variante mit der Unbekannten als Subtrahend, A − B = C ⇔ −B = C − A, als die eigentlich schwierige hervor (S. 239). Ojose (2015) zeigt das Divisionsgegenstück: 180x = 2 → x = 90 (Misconception 37) und x/4 = −4 → x = −1 (Misconception 38). Weigand et al. (2022, Abb. 5.32) führen 3x = 5 → x = 2 oder x = 15 als typischen Umformungsfehler.

### M2 Minus vor dem x-Term ist ein Rechenzeichen (Stufe A)

- **Regel**: «Ein Minus vor dem x-Term ist ein ‹minus›, kein Teil des Koeffizienten.» Zwei belegte Ausprägungen: (a) Verschwindet beim Umformen der Minuend, bleibt ein «Minus ohne Zahl davor» übrig, und das wird einfach weggelassen. (b) Das Minus wird mit Plus «weggebracht».
- **Kontrast**: −5x ist (−5) · x; die Umkehrung ist Division durch −5.
- **An Aufgaben der LU 11**:
  - Ausprägung (a), Malles Beispiel: a − b·x = c → «| −a» → b·x = c − a. Konkret: 7 − 2x = 1 → «| −7» → 2x = −6 → x = −3 (richtig 3).
  - Ausprägung (b), Vorsammlung: −5x = −15 → «| +5» → x = −10 (richtig 3). 12 = −3x → «| +3» → 15 = x (richtig −4).
  - 4x = 20 → «| :4» → x = 5: richtig, weil kein Minus davor steht.
- **Begründung in Schülerworten**: (a) «Die Sieben ist weg, dann ist das Minus auch weg, das gehört ja zur Sieben.» (b) «Da steht minus fünf x, also plus fünf, dann ist das weg.»
- **Abgrenzung**: Nicht das Rüberbringen ohne Vorzeichenwechsel und kein Fehler beim Rechnen mit negativen Zahlen; sie rechnet −15 + 5 korrekt.
- **Aufdeckbar durch**: «Was steht zwischen der 5 und dem x?» oder Probe mit x = −10: −5 · (−10) = 50 ≠ −15.
- **Belege**: Malle (1993, S. 178–179) beschreibt Ausprägung (a) wörtlich als «Weglassen von Operationszeichen ohne Operanden»: Das Minuszeichen müsste von einem Subtraktionszeichen zu einem Vorzeichen uminterpretiert werden; wer an der Subtraktionsdeutung festhält, streicht es. Vlassis & Demonty (2022) belegen das Ablösen des Minuszeichens vom Term («detachment from the minus sign») mit hohen Fehlerquoten bei −12 − 8 (52 %). Ojose (2015, Misconception 36) führt x − 7 = −7 → x = −14 an. Ausprägung (b) ist der COACTIV-Distraktor aus der Vorsammlung.

### M3 Einseitige Operation: der Hauptnenner trifft nur die Brüche (Stufe A)

- **Regel**: «Mit dem Hauptnenner multiplizieren heisst: Die Nenner verschwinden. Glieder ohne Nenner bleiben, wie sie sind, dort ist ja nichts zu kürzen.» Das ist die Waage-Verletzung in ihrer häufigsten Gestalt im 9. Schuljahr.
- **Kontrast**: Jede Multiplikation gilt für jedes Glied auf beiden Seiten.
- **An Aufgaben der LU 11**:
  - Malles Beispiel: x/3 + (x − 1)/2 = 4 → «| ·6» → 3x + 2(x − 1) = 4 → 5x = 6 → x = 1.2 (richtig 5.2).
  - Gleichung mit gebrochenen Termen (SB 4, Stil): x/3 + x/4 = 7 → «| ·12» → 4x + 3x = 7 → x = 1 (richtig 12).
  - (x + 1)/2 = x − 3 → «| ·2» → x + 1 = x − 3 → 1 = −3 → «unlösbar» (richtig x = 7).
  - Einschrittige Gleichungen wie SB 2G x/5 = 12 löst sie im Kopf richtig. Das Muster greift, sobald sie das Verfahren «Hauptnenner» anwendet.
- **Begründung in Schülerworten**: «Ich nehme mal sechs, damit die Brüche weggehen. Die Vier hat keinen Bruch, da muss ich nichts machen.»
- **Abgrenzung**: Nicht M4 (dort werden beide Seiten, aber je Seite nur ein Glied getroffen).
- **Aufdeckbar durch**: «Was hast du mit der Vier gemacht?» und Probe.
- **Belege**: Malle (1993, S. 186) führt genau x/3 + (x − 1)/2 = 4 → 3x + 2(x − 1) = 4 an und erklärt es als «Nichtbeachtung von Prozedurhierarchien»: Die Unterprozedur «Zähler zum gemeinsamen Nenner bestimmen» nimmt die Schüler:in so gefangen, dass sie vergisst, in die Oberprozedur zurückzuspringen und die rechte Seite mitzunehmen.

### M4 Die Operation trifft nur ein Glied je Seite (Stufe A)

- **Regel**: «Teilen oder Malnehmen gilt für das Glied, um das es geht, auf beiden Seiten; die anderen Glieder haben damit nichts zu tun.»
- **Kontrast**: Multiplikation und Division sind distributiv über die Summe; jedes Glied wird getroffen.
- **An Aufgaben der LU 11**:
  - Weigands Beispiel: 5 = 3 + x/5 → «| ·5» → 25 = 3 + x → x = 22 (richtig 10).
  - x/4 + 3 = 7 → «| ·4» → x + 3 = 28 → x = 25 (richtig 16). Unterschied zu M3: dort ergäbe sich x + 3 = 7 → x = 4.
  - Zwischenschritt aus SB 5A: 5x + 5 = −10 → «| :5» → x + 5 = −2 → x = −7 (richtig −3).
- **Begründung in Schülerworten**: «Ich will das x allein haben, also mal fünf beim Bruch und bei der Fünf drüben. Die Drei hat mit dem Bruch nichts zu tun.»
- **Abgrenzung**: Spiegelbild von M5 beim Umformen statt beim Termumformen. Nicht M3.
- **Aufdeckbar durch**: «Setz 22 ein.» oder «Was passiert mit der Drei, wenn du mal fünf rechnest?»
- **Belege**: Weigand et al. (2022, Abb. 5.32, S. 288) führen 5 = 3 + x/5 → 25 = 3 + x als typischen Fehler und nennen als Ursache, dass «die Notwendigkeit der Anwendung des Distributivgesetzes nicht erkannt» wird.

## 2. Klammern und Zusammenfassen

### M5 Klammer nur zur Hälfte aufgelöst (Stufe A)

- **Regel**: «Der Faktor vor der Klammer gehört zum ersten Glied in der Klammer. Der Rest der Klammer bleibt, wie er ist.»
- **Kontrast**: Distributivgesetz: Der Faktor trifft jedes Glied.
- **An Aufgaben der LU 11**:
  - SB 5: 2(18x − 8) = 6(5 − 5x) − 13 → 36x − 8 = 30 − 5x − 13 → 41x = 25 → x = 25/41 (richtig 0.5).
  - AH 2, Serie B: 5(x + 1) = 80 → 5x + 1 = 80 → x = 15.8; 5(x + 2) = 85 → 16.6 (richtig in der ganzen Serie 15). Die Serie ist darauf angelegt, dass x konstant bleibt; bei ihr wandert es.
  - Malles Beispiel: 2 · (x/2 − 3) = x − 3 (richtig x − 6).
- **Begründung in Schülerworten**: «Zwei mal achtzehn x ist sechsunddreissig x. Die minus acht steht hinter dem x, die hat mit der Zwei nichts zu tun.»
- **Abgrenzung**: Kein Vorzeichenfehler (M6). Die Reichweite des Faktors ist für sie das nächste Glied.
- **Aufdeckbar durch**: «Was heisst 2 · (18x − 8), wenn x = 1 ist?» Kopfrechnung 20 gegen ihre Auflösung 28.
- **Belege**: Malle (1993, S. 186) erklärt 2 · (x/2 − 3) = x − 3 als Prozedurhierarchie-Fehler: Die komplexe Unterprozedur «Bruch mit natürlicher Zahl multiplizieren» verbraucht so viel Aufmerksamkeit, dass die Rückkehr zur Oberprozedur unterbleibt. Weigand et al. (2022, Tab. 3.2, S. 108) führen a · (2/(b + c)) = 2a/(b + c) in derselben Familie; Ojose (2015, Misconception 27) 3(x + y) = 3xy.

### M6 Das Minus vor der Klammer trifft nur das erste Glied (Stufe A)

- **Regel**: «Ein Minus vor einer Klammer gehört zum ersten Glied in der Klammer. Die übrigen Glieder behalten ihr Zeichen.»
- **Kontrast**: Ein Minus vor der Klammer kehrt jedes Vorzeichen in der Klammer um.
- **An Aufgaben der LU 11**:
  - AH 1, Serie D: 91 − x = 16 → 75 (richtig). 91 − (x − 2) = 16 → 91 − x − 2 = 16 → x = 73 (richtig 77). 91 − (x − 4) = 16 → 71 (richtig 79). Ihre Serie fällt 75, 73, 71; die Aufgabe erwartet 75, 77, 79.
  - SB 5: 45(2 − x) − 3(21x − 1) = 6(3x − 1) + 36 → «−3(21x − 1) = −63x − 3» statt −63x + 3.
  - Malles Beispiel: 4(3x − 1) − 6(x − 4) = 12x − 4 − 6x − 24 (richtig + 24).
- **Begründung in Schülerworten**: «Das Minus gehört zum x. Die minus zwei war schon vorher minus, die bleibt.»
- **Abgrenzung**: Nicht M5 (dort fehlt die Multiplikation, hier das Vorzeichen).
- **Aufdeckbar durch**: «Was ist 91 − (x − 2), wenn x = 10 ist?» Kopfrechnung 83 gegen ihre Auflösung 79.
- **Belege**: Malle (1993, S. 250) nennt 4(3x − 1) − 6(x − 4) = 12x − 4 − 6x − 24 als häufigen Fehler; S. 187 den Zählerfall x − 2(x + 3)/8 → x − 2x + 3. Weigand et al. (2022, Tab. 3.2) führen 3y − (2a + b) = 3y − 2a + b als ersten Eintrag ihrer Liste systematischer Fehler. Vlassis & Demonty (2022) liefern den Mechanismus (Minuszeichen wird nicht als an das Folgende gebunden gesehen).

### M7 Ungleichartige Glieder werden verschmolzen (Stufe A; auch für Formvariablen)

- **Regel**: «Ein Plus zwischen zwei Gliedern heisst zusammenzählen. Zahlen werden addiert, die Buchstaben angehängt.» Ein Ergebnis mit offenem Plus ist «nicht fertig».
- **Kontrast**: Nur gleichartige Glieder lassen sich zusammenfassen; 5x + a ist ein fertiger Term.
- **An Aufgaben der LU 11**:
  - AH 7: 5x + a = 128 → 6ax = 128. Für «Finde a so, dass x = 23» rechnet sie 6 · a · 23 = 128 → a ≈ 0.93 (richtig 13).
  - AH 8: 5x + 8 = 71 + bx → 13x = 71bx → b = 13/71.
  - 3x + 2 = 14 → 5x = 14 → x = 2.8 (richtig 4).
- **Begründung in Schülerworten**: «Fünf x und ein a, das sind zusammen sechs, und die Buchstaben schreibt man dazu.»
- **Abgrenzung**: Nicht M13. Kein Problem mit dem Distributivgesetz.
- **Aufdeckbar durch**: «Wenn x = 2 und a = 3 ist, was ist dann 5x + a?» Sie rechnet 13 und vergleicht mit 6 · 2 · 3 = 36.
- **Belege**: Malle (1993, S. 179) mit 3xy + 4yz = 7xyz und 8a + 4 = 12a (S. 15), erklärt über «Sammelschemata» aus dem Rechnen mit Masseinheiten und das «Antwortformschema», dass am Schluss immer ein einziger Ausdruck stehen müsse (S. 138, 178). Moru & Mathunya (2022) messen bei 95 Achtklässler:innen 47 % für 3x + 5 → 8x und zitieren: «we cannot leave it as 5a + 4b since it is not simplified». Ojose (2015, Misconception 24): 2X + 4 + 3X + 5 → 14X.

## 3. Zahlbereiche und Lösungen

### M8 Unübliche Lösung wird abgelehnt (Stufe B für negative, C für gebrochene Lösungen)

- **Regel**: «Eine Gleichung lösen heisst, am Schluss eine Zahl zu bekommen, wie man sie kennt. Ein Ergebnis, das ‹nicht geht›, heisst: Die Gleichung ist unlösbar.» Belegt ist die Ablehnung negativer Lösungen; die Ablehnung von Brüchen und Dezimalzahlen ist eine Hypothese der ersten Fassung.
- **Kontrast**: Unlösbar ist eine Gleichung nur, wenn die Umformung auf eine falsche Aussage führt.
- **An Aufgaben der LU 11**:
  - Negative Variante: SB 3, x + 7 = 2 → «−5, das geht nicht, unlösbar» (richtig −5). Im 9. Schuljahr nach SB 3 nur noch bei schwachen Lernenden plausibel.
  - Bruch-Variante (Hypothese): SB 5B endet bei 10x = 33 → «geht nicht auf → L = { }» (richtig 3.3). AH 8C «Wähle b so, dass 5x + 8 = 71 + bx unlösbar ist»: b = 7, weil −2x = 63 «nicht aufgeht» (richtig b = 5).
- **Begründung in Schülerworten**: «Dreiunddreissig durch zehn geht nicht. Dann gibt es halt keine Zahl, die passt.»
- **Abgrenzung**: Nicht M9, nicht M10.
- **Aufdeckbar durch**: «Setz 3.3 ein.»
- **Belege**: Vlassis & Demonty (2022) berichten mit Bezug auf Gallardo (2002) und Vlassis (2008), dass Lernende beim Einstieg in die ganzen Zahlen eine negative Zahl als Lösung einer Gleichung nicht akzeptieren, weil sie ihr keine Bedeutung geben können. Für Brüche als abgelehnte Lösung liegt in den Quellen kein Beleg vor; die Vorstellung, jede Aufgabe müsse «aufgehen», gehört zu Malles Antwortformschema (S. 138), ist dort aber nicht auf Lösungen bezogen.

### M9 Null ist keine Lösung (Stufe C)

- **Regel**: «Null heisst nichts. Kommt x = 0 heraus, ist nichts herausgekommen, also hat die Gleichung keine Lösung.»
- **Kontrast**: 0 ist eine Zahl; L = {0} ist von L = ∅ verschieden.
- **An Aufgaben der LU 11**: AH 11, (a + 3)x = x → für a = 5: 7x = 0 → x = 0 → «unlösbar». 3x + 4 = 4 → «L = { }». x(x − 4) = 0 → «x = 4», die Null wird nicht genannt.
- **Begründung in Schülerworten**: «Null ist keine Zahl, die man einsetzen kann, da ist nichts.»
- **Aufdeckbar durch**: «Setz null ein. Stimmt die Gleichung dann?»
- **Belege**: In keiner der zehn Quellen belegt. Weigand et al. (2022, S. 242) behandeln x · (x + 2) = 0 mit L = {0, −2} rein fachlich. Der entfernteste Verwandte ist bei Moru & Mathunya (2022) ein Schüler, der 8q − 5q − 3q zu «0q» macht und die Null nicht als Ergebnis stehen lassen kann. Das Muster bleibt eine Hypothese der Vorsammlung. Für eine Vignette nur mit eigener Quelle verwenden.

### M10 Ein Widerspruch wird zur Lösung umgerechnet (Stufe A)

- **Regel**: «Eine Gleichung hat immer genau eine Zahl als Lösung. Fällt x beim Umformen weg, steht es unsichtbar noch da: Die Zahl auf der Seite, wo x stand, wird wie ein Summand von x auf die andere Seite gebracht.»
- **Kontrast**: 8 = −9 ist eine falsche Aussage, L = ∅; 5 = 5 ist eine wahre Aussage, L = Grundmenge.
- **An Aufgaben der LU 11**:
  - SB 10B: 4.5x + 8 = 2x − 9 + 2.5x → 4.5x + 8 = 4.5x − 9 → «| −4.5x» → 8 = −9 → «x = −9 − 8 = −17».
  - AH 8C mit b = 5: 5x + 8 = 71 + 5x → 8 = 71 → «x = 63».
  - Allgemeingültig: 3x + 5 = 3x + 5 → 5 = 5 → «x = 0». Die Gleichung, die alle Zahlen löst, bekommt bei ihr genau eine.
- **Begründung in Schülerworten**: «Das x ist ja nicht weg, es ist nur allein. Acht rüber, dann ist x gleich minus siebzehn.»
- **Abgrenzung**: Der Weg bis 8 = −9 stimmt. Nicht M9.
- **Aufdeckbar durch**: «Setz −17 in die Anfangsgleichung ein.» Sie sucht den Fehler beim Rechnen, nicht beim Schluss. «Gibt es eine Gleichung, die keine Lösung hat?» legt das Modell offen.
- **Belege**: Malle (1993, S. 20): «Es gab auch Schüler, die die Gleichung 20 = 4 in der Arithmetik als puren Nonsens ansahen, in der Algebra jedoch als einen Zwischenschritt beim Gleichungslösen akzeptierten und weitere Operationen wie 4 − 20 oder 20 − 4 ausführen wollten.» Weigand et al. (2022, S. 287) nennen «unübliche Lösungen» als Quelle fehlerhafter Schlussweisen, weil Lernende schematisch ein Ergebnis der Form x = Zahl erwarten.

## 4. Bruchgleichungen und Definitionsbereich

### M11 Kehrwert gliedweise (Stufe A)

- **Regel**: «Brüche in einer Gleichung darf man umdrehen. Jeder Bruch wird für sich umgedreht, auf beiden Seiten.» Die legitime Kehrwertregel für a/b = c/d (SB, Umformung 6) wird auf Summen ausgedehnt.
- **Kontrast**: Der Kehrwert einer Summe ist nicht die Summe der Kehrwerte.
- **An Aufgaben der LU 11**:
  - AH 9: 1/x − 1/(2x) = 1/16 → x − 2x = 16 → x = −16 (richtig 8).
  - Malles Beispiel: 1/3 = 1/x + 1/7 → 3 = x + 7 → x = −4 (richtig 5.25).
  - Weigands Beispiel: 1/x = a + 5 → x = 1/a + 1/5.
  - SB 6/7: 6/(x − 3) = 15/x → (x − 3)/6 = x/15 → x = 5. Richtig, weil je Seite nur ein Bruch steht. Die Schüler:in hat Erfolgserlebnisse mit ihrer Regel.
- **Begründung in Schülerworten**: «Im Buch steht, man darf die Kehrwerte nehmen. Ich habe alle Brüche umgedreht.»
- **Abgrenzung**: Kein Fehler beim Bruchrechnen; ein Strukturfehler.
- **Aufdeckbar durch**: «Ist der Kehrwert von 1/2 + 1/2 gleich 2 + 2?» oder Probe mit x = 8 auf beiden Seiten der Ausgangsgleichung.
- **Belege**: Malle (1993, S. 175–176) nennt 1/3 = 1/x + 1/7 ⇔ 3 = x + 7 und 1/R = 1/R₁ + 1/R₂ ⇔ R = R₁ + R₂ als «Kehrwertfehler» durch unzulässiges Linearisieren, mit Interview Kurt (S. 178). Weigand et al. (2022, Abb. 5.32) führen 1/x = a + 5 → x = 1/a + 1/5.

### M12 Der Definitionsbereich ist ein eigener Aufgabenteil (Stufe B)

- **Regel**: «‹Bestimme zuerst die nicht zugelassenen Zahlen› ist Teil a der Aufgabe, ‹Löse› ist Teil b. Was in Teil a stand, spielt in Teil b keine Rolle.»
- **Kontrast**: Ein Wert, der einen Nenner null macht, ist keine Lösung. Bei allgemeingültigen Bruchgleichungen ist L = D, nicht «alle Zahlen».
- **An Aufgaben der LU 11**:
  - Im Stil von AH 9/10: 1/(x − 3) + 2 = (x − 2)/(x − 3). Sie schreibt «nicht zugelassen: 3», multipliziert mit (x − 3): 1 + 2x − 6 = x − 2 → x = 3, und notiert «L = {3}» (richtig L = ∅).
  - SB 10D: (4x + 6)/(2x + 3) = 2 → «nicht zugelassen: −1.5» → 4x + 6 = 4x + 6 → «alle Zahlen» (richtig ℝ \ {−1.5}).
  - SB 7B: 9/(2x) = 3/(2x + 2) → x = −1.5, nicht zugelassen sind 0 und −1: richtig, das Muster bleibt unsichtbar.
- **Begründung in Schülerworten**: «Die Drei ist die nicht zugelassene Zahl, das habe ich hingeschrieben. Und die Lösung ist drei, das ist ausgerechnet.»
- **Abgrenzung**: Kein Rechenfehler, kein Nichtwissen.
- **Aufdeckbar durch**: «Setz deine Lösung in die erste Zeile ein.»
- **Belege**: Der Mechanismus ist belegt: Weigand et al. (2022, S. 242, 300) beschreiben das Multiplizieren mit dem Hauptnenner als Gewinnumformung, deren Lösungen an der Ausgangsgleichung geprüft werden müssen, und stellen fest (S. 287), dass Lernende diese Prüfung unterlassen. Malle (1993, S. 20) kritisiert, dass Definitionsmengen im Unterricht als Ritual am Aufgabenanfang stehen. Die zweistufige Form «korrekt bestimmt, dann ignoriert» ist in den Quellen nicht dokumentiert; sie ist für die Vignette konstruiert, weil AH 9 genau diesen Aufgabenaufbau hat.

## 5. Formvariablen

### M13 Die Formvariable bekommt eine selbst gewählte Zahl und wird vergessen (Stufe B)

- **Regel**: «Ein Buchstabe, der nicht x ist, ist ein Platzhalter, in den ich eine Zahl einsetze. Dann ist die Gleichung normal.» Der Einsetzungsaspekt wird auf den Parameter angewandt; die Abhängigkeit der Lösung von a kommt nie in den Blick.
- **Kontrast**: Eine Formvariable steht für eine beliebige, aber feste Zahl; die Lösung ist ein Term in a, und «für welche a» verlangt eine Bedingung, keine Instanz.
- **An Aufgaben der LU 11**:
  - AH 7: 5x + a = 128 → «a = 3» → x = 25. Auf «Finde a so, dass x = 23»: «a ist 3, dann ist x 25, also geht das nicht.» Variante nach Specht: «a = 1».
  - AH 7C «Für welche a hat die Gleichung natürliche Zahlen als Lösung? Beschreibe durch einen Term»: «a = 3, dann x = 25, ja.» Ein Term (a = 128 − 5n) entsteht nicht.
  - AH 11, x(a + 1) = 5: «a = 4» → x = 1, «lösbar».
- **Begründung in Schülerworten**: «Für a muss man halt was nehmen, sonst kann man nicht rechnen.»
- **Abgrenzung**: Nicht M7. Mit gewähltem a rechnet sie richtig.
- **Aufdeckbar durch**: «Was wäre, wenn a = 8 wäre?» Sie rechnet x = 24 und sagt «aber a ist ja drei». «Woher weisst du, dass a drei ist?»
- **Belege**: Weigand et al. (2022, S. 205, 287) beschreiben, dass Lernende ohne Rollenverständnis den Parameter «wie eine Unbekannte auszurechnen» versuchen oder wie eine normale Zahl behandeln. Malle (1993, S. 80–83, 264) verortet den Parameter im Einzelzahlaspekt («beliebig, aber fest»), dessen Verlust zur konkreten Festlegung führt. Akinwunmi (2012, S. 12) zitiert nach Specht eine Achtklässlerin: «wenn x alleine steht, dann ist das immer eins». Moru & Mathunya (2022) zitieren einen Schüler, der aus a + b = 6 auf a = 3, b = 3 und c = 3 schliesst. Die konkrete Form für AH 7 ist konstruiert.

## 6. Ungleichungen

### M14 Das Relationszeichen bleibt beim Teilen durch eine negative Zahl (Stufe A)

- **Regel**: «Eine Ungleichung wird genau wie eine Gleichung umgeformt. Das Zeichen in der Mitte bleibt, wie es ist.»
- **Kontrast**: Multiplikation oder Division mit einer negativen Zahl kehrt das Relationszeichen um (SB, Umformung 7).
- **An Aufgaben der LU 11**:
  - SB 12A: 3 + 7x < 2(4x − 5) → 3 + 7x < 8x − 10 → «| −8x» → 3 − x < −10 → «| −3» → −x < −13 → «| :(−1)» → x < 13 (richtig x > 13). Der Schulbuchweg (| −7x) umgeht die negative Division; wer das x nach links holt, tappt in die Falle.
  - Ojoses Beispiel: −5x < 10 → x < −2 (richtig x > −2).
  - 2x + 1 > 7 → x > 3: richtig, ohne negative Division bleibt das Muster unsichtbar.
- **Begründung in Schülerworten**: «Ich teile durch minus eins, das Zeichen bleibt, wie bei einer Gleichung auch.»
- **Abgrenzung**: Nicht M15, nicht M16. Eine belegte Nachbarvariante (Mutodi et al. 2023): Das Zeichen wird umgedreht, wenn ein negativer Term die Seite wechselt, nicht beim Dividieren; das ist eine falsch gelernte Regel, kein Vergessen.
- **Aufdeckbar durch**: «Nimm x = 0. Stimmt 3 + 7x < 8x − 10 dann?» (3 < −10 ist falsch, obwohl 0 < 13.)
- **Belege**: Ojose (2015, Misconception 39): −5X < 10 → X < −2, «most students would apply the ‹normal› rules of solving equations». Weigand et al. (2022, S. 247, 264–266) begründen die Regel über die Spiegelung am Nullpunkt und nennen die mechanische Übertragung von Gleichungsregeln als Fehlerquelle. Mutodi et al. (2023) dokumentieren beide Varianten mit Schülerarbeiten (Grade 12).

### M15 Die Ungleichung wird als Gleichung gelöst, der Grenzwert ist «die Lösung» (Stufe B)

- **Regel**: «Das Zeichen sagt, dass die Seiten nicht gleich sind. Ausrechnen tut man es wie eine Gleichung, und die Zahl, die herauskommt, ist die Lösung.»
- **Kontrast**: Die Lösung einer Ungleichung ist ein Bereich, nicht eine Zahl.
- **An Aufgaben der LU 11**: SB 12A → «x = 13» (richtig x > 13). AH 12: 2x + 1 > 7 → «x = 3». Auf «Gib alle Lösungen an» dieselbe eine Zahl.
- **Begründung in Schülerworten**: «Da kommt dreizehn raus. Das Zeichen heisst nur, dass es nicht genau gleich ist.»
- **Abgrenzung**: Nicht M14 (sie dreht gar nichts).
- **Aufdeckbar durch**: «Ist 20 eine Lösung? Setz ein.»
- **Belege**: Mutodi et al. (2023) zeigen Zwölftklässler:innen, die 5x² + 4 > 21x faktorisieren, die Faktoren gleich null setzen und x = 1/5, x = 4 als Endergebnis notieren; in Interviews sagen sie, sie hätten «sofort an Gleichungen gedacht». Weigand et al. (2022, S. 243) betonen fachlich, dass Lösungsmengen von Ungleichungen Intervalle sind. Für lineare Ungleichungen im 9. Schuljahr ist die Form konstruiert.

### M16 Die Grenze gehört immer dazu (Stufe C)

- **Regel**: «< und ≤ sind dasselbe; der Strich ist nur eine andere Schreibweise. Die Lösung fängt bei der Grenzzahl an.»
- **An Aufgaben der LU 11**: SB 12A: x > 13 in ℕ → «{13, 14, 15, …}» (richtig {14, 15, …}).
- **Aufdeckbar durch**: «Setz 13 in die Ausgangsungleichung ein.» 94 < 94 ist falsch.
- **Belege**: In den Quellen des Notebooks nicht belegt. Weigand et al. (2022, S. 247) beschreiben nur die fachliche Darstellung mit offenen und gefüllten Punkten. Das Muster stammt aus der Vorsammlung; als eigenständige Vignette nicht empfohlen, allenfalls als Zusatzverhalten zu M15.

## 7. Bruchterme und Struktur

### M18 Verschubspiel: Glieder aus Nennern und Klammern herausziehen (Stufe A, neu)

- **Regel**: «Jedes Glied darf mit seiner Umkehroperation auf die andere Seite, egal wo es steht, auch aus einem Nenner oder einer Klammer heraus.» Malle nennt die Lernenden «Verschieber».
- **Kontrast**: Nur ein Glied auf der obersten Ebene einer Seite lässt sich durch Addition oder Subtraktion auf beiden Seiten entfernen; ein Summand im Nenner ist Teil eines Faktors.
- **An Aufgaben der LU 11**:
  - SB 6/7: 6/(x − 3) = 15/x → «minus drei rüber»: 6/x = 15/x + 3 → 6 = 15 + 3x → x = −3 (richtig 5).
  - AH 3: 240 : (x + 1) = −30 → «plus eins rüber»: 240 : x = −31 → x = −240/31 (richtig −9).
  - Malles Beispiel: a = b/(cd + e) → a − e = b/(cd).
  - 6/x = 15/(x + 2) → «Nenner hinübermultiplizieren» ohne Klammer: 6x + 2 = 15x (richtig 6(x + 2) = 15x).
- **Begründung in Schülerworten**: «Das minus drei kann ich rüberbringen, dann wird es plus drei. Das darf man doch.»
- **Abgrenzung**: Nicht M1 (dort stimmt die Ebene, nur die Rolle von x wird missachtet). Nicht M6.
- **Aufdeckbar durch**: «Nach welcher Regel?» (Malles eigene Diagnosefrage) und Probe mit x = 5 auf beiden Seiten. Die Schüler:in ist, wie Malles Marie, von ihrem Vorgehen überzeugt: «Gleichungen lösen kann ich.»
- **Belege**: Malle (1993, S. 184) beschreibt «Verschieber» mit «zu offenen Schemata»: Ein Schüler macht aus a = b/(1 + cd) die Formel c = b/(1 + ad) («Ich habe a und c vertauscht»); Marie «multipliziert den Nenner hinüber», Glied für Glied (S. 183–184). Auf S. 216–217 und 252–253 die Umformung a = b/(cd + e) → a − e = b/(cd), von der Malle sagt, sie verstosse gegen keine der verbal gelernten Regeln, weil diese die Bedingungen nicht nennen.

### M19 Gliedweises Kürzen in Bruchtermen (Stufe A, neu)

- **Regel**: «Was in Zähler und Nenner gleich aussieht, wird gestrichen, egal ob Summand oder Faktor.»
- **Kontrast**: Kürzen ist nur bei gemeinsamen Faktoren erlaubt; aus Summen kürzt man nicht.
- **An Aufgaben der LU 11**:
  - SB 8B, (9 + x)/(16 − x) = 4 → «x kürzen»: 9/16 = 4 → «unlösbar» (richtig x = 11).
  - (x + 5)/5 = 3 → «Fünf kürzen»: x = 3 (richtig 10).
  - SB 10D, (4x + 6)/(2x + 3) = 2 → «x kürzen»: 10/5 = 2 → 2 = 2 → allgemeingültig. Richtig bis auf den fehlenden Ausschluss von −1.5; die Regel liefert hier zufällig das Ergebnis.
- **Begründung in Schülerworten**: «Oben steht x und unten steht x, das kürzt sich weg.»
- **Abgrenzung**: Nicht M11 (Kehrwert), nicht M18 (Verschieben).
- **Aufdeckbar durch**: «Nimm x = 1: Was ist (9 + 1)/(16 − 1)? Und was ist 9/16?»
- **Belege**: Weigand et al. (2022, Tab. 3.2, S. 108) führen (a + b)/(c + b) = a/c und (ax + b)/a = x + b als systematische Kürzungsfehler. Ojose (2015, Misconception 26): (X + 5)/5 → X, mit der Erklärung, Lernende glaubten, jeder Ausdruck müsse sich weiter vereinfachen lassen.

### M20 Nullprodukt übergeneralisiert (Stufe A, neu; nur für den Vertiefungsteil «Quadrate»)

- **Regel**: «Ein Produkt ist gleich einer Zahl, wenn einer der Faktoren gleich dieser Zahl ist.» Die Regel für a · b = 0 wird auf a · b = c übertragen.
- **Kontrast**: Der Schluss gilt nur für c = 0.
- **An Aufgaben der LU 11** (Richtziel «einfache Gleichungen mit Quadraten»): x(x − 4) = 5 → «x = 5 oder x − 4 = 5 → x = 5 oder x = 9» (richtig 5 und −1). (x − 1)(x − 2) = 6 → «x = 7 oder x = 8» (richtig 4 und −1). x(x − 4) = 0 → x = 0 oder x = 4: richtig.
- **Begründung in Schülerworten**: «Wenn mal gerechnet fünf rauskommt, muss einer von beiden fünf sein.»
- **Aufdeckbar durch**: «Setz 9 ein: 9 · 5 = 45, nicht 5.»
- **Belege**: Malle (1993, S. 175) beobachtet (x − 5)(x − 7) = 3 ⇔ x − 5 = 3 ∨ x − 7 = 3 «in verschiedenen Varianten», etwa x · (x − 3) = 5 ⇔ x = 0 ∨ x − 3 = 5. Weigand et al. (2022, S. 289) führen x(x − 4) = 1 in derselben Weise.

## 8. Mathematisieren (Zahlenrätsel)

### M17 Wortfolge-Übersetzung (Stufe A)

- **Regel**: «Ein Satz wird von links nach rechts in Zeichen übersetzt. Die Zahlen und Buchstaben kommen in der Reihenfolge, in der sie im Satz stehen.» Das ist die Regel hinter dem multiplikativen Umkehrfehler (6S = P) und seinem additiven Bruder; in der LU 11 zeigt sie sich vor allem bei «von» und «zu».
- **Kontrast**: Die Struktur der Aussage bestimmt die Gleichung, nicht die Wortstellung: «subtrahiere x vom Nenner» ist 16 − x.
- **An Aufgaben der LU 11**:
  - SB 8B: «Addiere zum Zähler des Bruchs 9/16 eine Zahl. Subtrahiere dieselbe Zahl vom Nenner. Du erhältst 4.» → (9 + x)/(x − 16) = 4 → x = 24⅓ (richtig 11).
  - «Subtrahiere 5 von einer Zahl, du erhältst 12» → 5 − x = 12 → x = −7 (richtig 17).
  - «Es gibt dreimal so viele Schüler wie Lehrer» → 3S = L (richtig S = 3L). «Astrid hat 5 Marken mehr als Claudia» → 5 + A = C (richtig A = C + 5).
  - SB 8: «Der hundertste Teil einer Zahl ergibt das Neunfache des Kehrwertes» → x/100 = 9 · 1/x: richtig, weil Wortfolge und Struktur hier zusammenfallen.
- **Begründung in Schülerworten**: «Dieselbe Zahl minus der Nenner, so steht es da.»
- **Abgrenzung**: Kein Rechenfehler; das Lösen der falschen Gleichung ist korrekt. Nicht die Objektvorstellung der Variablen (Beispielvignette Julia in `04-beispiele.md`), obwohl beide zum selben Umkehrfehler führen.
- **Aufdeckbar durch**: «Nimm 11. Zähler plus 11, Nenner minus 11. Was ergibt das? Und was sagt deine Gleichung für 11?»
- **Belege**: Malle (1993, Kap. 4, S. 93 ff.) mit Fehlerquoten von 40 % (Professoren) bis 80 % (Ziegen und Kühe) und dem Abschnitt «Additive Umkehrfehler» (S. 102–105): Anabel (13) schreibt zu «Astrid hat um 5 Briefmarken mehr als Claudia» die Gleichung 5 + X = Y. Moru & Mathunya (2022): «Subtract 3a from 5» → 3a − 5 bei 50 % der Achtklässler:innen, mit Interview («less than is minus in algebraic expressions»). Weigand et al. (2022, S. 275, 287) empfehlen als Gegenmittel das Einsetzen konkreter Zahlen. Bansilal & Govender (2021) bestätigen die Erklärungskraft des Wortfolge-Abgleichs bei angehenden Lehrpersonen; Christianson, Mestre & Luke (2012) zeigen, dass wiederholtes Üben den Fehler ohne Rückmeldung abbaut.

## 8a. Nicht empfohlen oder bereits vorhanden

- **Operationales Gleichheitszeichen als Gleichungskette**: gut belegt (Malle 1993, Kap. 6; Otten et al. 2019; Mills et al. 2027 messen 49 % operationale Definitionen am Ende der Primarstufe), liefert beim Gleichungslösen aber meist trotzdem das richtige Ergebnis. Für Klasse 5 bereits als Beispielvignette vorhanden.
- **Rüberbringen ohne Vorzeichenwechsel** (Kieran 1981): als Regel bei mehrgliedrigen Gleichungen nicht stabil. M1, M2 und M18 sind die tragfähigen Ausprägungen desselben Kerns.
- **Term wird zur Gleichung gemacht** («equation formation error», Moru & Mathunya 2022: 3x + 5 → 3x = 5 → x = 5/3): in der LU 11 sind alle Aufgaben Gleichungen, das Muster hat dort keinen Ort.

## 8b. Weitere belegte Muster, nicht ausgearbeitet

Aus Malle und Weigand belegt, aber hier nicht zum vollen Raster ausgebaut, weil sie in der LU 11 nur am Rand vorkommen oder sich mit obigen Mustern überschneiden:

- **Verfall vom Gleichungslösen ins Termumformen** (Malle 1993, S. 203): Bei (x + 3)/2 = (x + 1)/2 addiert die Schüler:in beide Seiten zu (2x + 4)/2 = x + 2 und formt als Term weiter, die Gleichung ist verschwunden. Passt zu Bruchgleichungen mit gleichen Nennern (SB 6, Lösungsweg 3 «gleichnamig machen»). Kandidat für eine spätere Vignette.
- **Division durch einen variablenhaltigen Term ohne Fallunterscheidung** (Weigand et al. 2022, S. 250, 289): 7x² = 2x | :x → x = 2/7, die Lösung 0 geht verloren. Gehört zum Richtziel «Gleichungen mit Quadraten» und ist der einzige belegte Ort, an dem in der LU 11 eine Null-Lösung verschwindet; als Ersatz für M9 denkbar.
- **Aufheben-Schema auf die Multiplikation übertragen** (Malle 1993, S. 174): a · (1/a) = 0, weil «ein Element durch sein Gegenelement aufgehoben wird». Bei Bruchgleichungen mit x und 1/x denkbar, aber selten.
- **Zirkuläres und unzweckmässiges Umformen** (Malle 1993, S. 203): korrekte Schritte, die zur Ausgangsgleichung zurückführen oder nichts vereinfachen. Kein Fehlermuster im Sinne des Leitfadens, weil kein falsches Ergebnis entsteht.

## 9. Empfehlung für die ersten Vignetten

| Muster | Stufe | Aufgabe aus der LU 11 | Warum zuerst |
|---|---|---|---|
| M1 Umkehr-Rezept | A | AH 1 Serie C oder AH 2 Serie C | Die Serie macht das Muster im Heft sichtbar; Probe mit einer Zahl deckt es auf. |
| M2 Minus als Rechenzeichen | A | Gleichung im Stil von SB 5A mit negativem Koeffizienten | Malles Weglass-Schema und der COACTIV-Distraktor in einem Muster; in drei Fragen aufdeckbar. |
| M3 Hauptnenner einseitig | A | Gleichung mit gebrochenen Termen (SB 4/5) | Malles eigenes Beispiel; die Schüler:in kann ihr Verfahren benennen und verteidigen. |
| M5 Klammer halb | A | SB 5 oder AH 2 Serie B | Die Serie erwartet konstantes x; ihr x wandert. |
| M6 Minus vor der Klammer | A | AH 1 Serie D | Ihre Serie fällt statt zu steigen; Kopfrechnung gegen Auflösung. |
| M10 Widerspruch zur Lösung | A | SB 10B | Genau die Aufgabe, an der die LU den Sonderfall einführt; Malles Beobachtung wörtlich. |
| M11 Kehrwert gliedweise | A | AH 9 | Ihre Regel funktioniert bei SB 6/7 und scheitert bei AH 9: reich fürs Gespräch. |
| M17 Wortfolge | A | SB 8B | Zahlenrätsel der LU; Probe mit 11 gegen den Text deckt es auf. |
| M18 Verschubspiel | A | SB 6/7 oder AH 3 | Bruchgleichung der LU; Malles Diagnosefrage «Nach welcher Regel?» passt direkt. |

Zweite Reihe: M4, M7, M14, M19 (Stufe A, aber schwächerer LU-Bezug oder Überschneidung mit einem Muster der ersten Reihe), M12 und M13 (Stufe B, gute Aufgabenpassung, konstruierte Form). Nicht als eigene Vignette: M8, M9, M16 (Stufe C), M20 (nur Vertiefung).

Für alle reicht ein Gesprächsbudget von zehn bis zwölf Schritten. Beim Ausformulieren gilt das Feldraster aus `04-beispiele.md`; die Arbeitsheft-Beschreibung muss die falsch gelöste Aufgabe genau so zeigen, wie sie aus der Regel folgt.

Hinweis zur Quelle `LU11.txt`: In der dortigen AH-3-Serie sind die angegebenen Lösungen für 240 : (x + 1) = −30 und 480 : (x + 2) = −60 falsch (richtig x = −9 und x = −10, nicht −17 und −18). Beim Übernehmen dieser Serie selbst nachrechnen.

## 10. Literatur

Quellen im NotebookLM «FailureOnTheFly FehlermusterAlgebra» (Seitenzahlen laut Auszug):

- Akinwunmi, K. (2012). *Zur Entwicklung von Variablenkonzepten beim Verallgemeinern mathematischer Muster*. Vieweg+Teubner. https://doi.org/10.1007/978-3-8348-2545-2
- Malle, G. (1993). *Didaktische Probleme der elementaren Algebra*. Vieweg.
- Mills, P., et al. (2027). Teaching and learning equivalence. *Journal of Experimental Child Psychology, 273*, 106652.
- Moru, E. K., & Mathunya, M. (2022). A constructivist analysis of Grade 8 learners' errors and misconceptions in simplifying mathematical algebraic expressions. *JRAMathEdu, 7*(3), 130–144. https://doi.org/10.23917/jramathedu.v7i3.16784
- Mutodi, P., Mosimege, M., & Maphutha, K. (2023). Learners' misconceptions and errors when solving inequalities. *Mathematics Education Journal, 7*(2), 136–158. https://doi.org/10.22219/mej.v7i2.27675
- Ojose, B. (2015). *Common misconceptions in mathematics: Strategies to correct them*. University Press of America. (Nummerierte «Misconceptions» nach dem Buch.)
- Otten, M., van den Heuvel-Panhuizen, M., & Veldhuis, M. (2019). The balance model for teaching linear equations: A systematic literature review. *International Journal of STEM Education, 6*(1). https://doi.org/10.1186/s40594-019-0183-2
- Vlassis, J., & Demonty, I. (2022). The role of algebraic thinking in dealing with negative numbers. *ZDM, 54*(6), 1243–1255. https://doi.org/10.1007/s11858-022-01402-1
- Weigand, H.-G., Schüler-Meyer, A., & Pinkernell, G. (2022). *Didaktik der Algebra* (2. Aufl.). Springer Spektrum.

Ergänzend, über scite abgerufen und nur als Zweitbelege verwendet:

- Bansilal, S., & Govender, R. G. (2021). Insights into the reversal error from a study with South African and Spanish prospective primary teachers. *Pythagoras, 42*(1). https://doi.org/10.4102/pythagoras.v42i1.613 (Autorenliste laut scite-Datensatz; der Verlagslink nennt Soneira als Erstautor.)
- Christianson, K., Mestre, J. P., & Luke, S. G. (2012). Practice makes (nearly) perfect: Solving 'students-and-professors'-type algebra word problems. *Applied Cognitive Psychology, 26*(5), 810–822. https://doi.org/10.1002/acp.2863
- Elkjær, M., & Jankvist, U. T. (2021). Designing tasks for a dynamic online environment: Applying research into students' difficulties with linear equations. *Mathematics, 9*(5), 557. https://doi.org/10.3390/math9050557

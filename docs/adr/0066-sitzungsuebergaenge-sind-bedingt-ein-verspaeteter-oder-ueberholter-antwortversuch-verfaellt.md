---
status: accepted
---

# Sitzungsübergänge sind bedingt; ein verspäteter oder überholter Antwortversuch verfällt

ADR-0061 lässt eine Sitzung in jedem Tab und auf jedem Gerät fortsetzen und
sagt, wodurch sie endet, aber nicht, was mit einem Gesprächsschritt geschieht,
der während dieses Endes noch läuft. ADR-0040 verlangt bedingte Übergänge nur
für versionierte Artefakte. Dieses ADR schließt die Lücke (#483).

Anlass: Der Gesprächsschritt prüfte den Status der Sitzung nur beim Laden der
Anfrage. Danach antwortet das Modell bis zu einer Minute lang, und der Sink
schrieb ohne erneute Prüfung. Gibt ein Tab die Diagnose ab, während ein
anderer auf eine Antwort wartet, bekam die abgeschlossene Sitzung noch einen
Gesprächsschritt; scheiterte er endgültig, überschrieb `gescheitert` den
Status `abgeschlossen`, und die Sitzung trug eine Diagnose, obwohl sie
gescheitert war. Ein Doppelklick auf „Senden“ ohne htmx endete in einem
Serverfehler, und ein zweiter Tab setzte die gebuchte Zeit eines Zeitbudgets
auf seinen veralteten Stand zurück.

## Übergänge gelten nur von `laufend` aus

Jeder Statusübergang einer Sitzung, also abschließen, abbrechen und scheitern,
ist eine bedingte Aktualisierung: `UPDATE … WHERE status = laufend`. Ein
verlorener Übergang überschreibt nichts und meldet sich dem Aufrufer, der
darauf mit dem tatsächlichen Stand antwortet. Die Diagnose entsteht nur
zusammen mit einem gelungenen Abschluss.

## Ein Antwortversuch verfällt, wenn er nicht mehr gilt

Ein Antwortversuch wird nur dann zum Gesprächsschritt, wenn beim Schreiben
beides gilt:

- Die Sitzung ist noch `laufend`.
- Der Verlauf hat noch die Schrittzahl, auf der der Antwortversuch begonnen
  hat.

Sonst **verfällt** er: kein Gesprächsschritt, kein antwortloser Abbruchschritt,
keine Fehlversuche, keine Statusänderung. Das gilt für den geglückten wie für
den endgültig gescheiterten Antwortversuch. Von zwei Schritten, die auf
derselben Schrittzahl beginnen, gewinnt der zuerst geschriebene.

Prüfen und Schreiben stehen in derselben Transaktion. Auf SQLite serialisiert
`BEGIN IMMEDIATE` sie (ADR-0059), wo `select_for_update` nichts bewirkt; auf
anderen Backends sperrt der Sink die Sitzungszeile.

## Was die Teilnehmer:in sieht

Nach einem Verfall sieht die Teilnehmer:in den tatsächlichen Stand wie nach
einem Neuladen: die Seite der beendeten Sitzung, in der Erhebung die aktuelle
Stelle des Ablaufs, beim parallelen Schritt das Gespräch mit dem Schritt, der
gewonnen hat. Ist die Sitzung inzwischen beendet, erscheint ein kurzer Hinweis,
dass die letzte Eingabe nicht mehr verarbeitet wurde. Ein Serverfehler entsteht
in keinem Fall.

## Die Uhr bucht auf dem gespeicherten Stand

Die Uhr des Gesprächsbudgets (ADR-0057) liest Status und Budgetstand in ihrer
Transaktion frisch und schreibt nur, solange die Sitzung `laufend` ist. Das
Beenden eines Zuges bucht die offene Spanne auf die gespeicherte verbrauchte
Zeit, nicht auf die des Anfrageobjekts. Der Beginn eines Zuges setzt nur die
offene Spanne neu an.

## Geltung

Die Regeln gelten für jede Sitzung mit Gerüst in der DB: Training, Erhebung und
flüchtige Teilnahme. Bei der flüchtigen Teilnahme prüft der Sink den Status in
der DB, auch wenn die Inhalte in der Browser-Session liegen (ADR-0045). Die
Schrittzahl liest er dort aus der Session seiner Anfrage; zwei gleichzeitige
Anfragen desselben Browsers schreiben die Session nacheinander, sodass auch hier
nur ein Schritt übrig bleibt. Der Probelauf ist schreibfrei und ausgenommen
(ADR-0014).

## Erwogene Optionen

- **Den Schritt trotzdem ablegen, mit oder ohne Markierung**: verworfen. Eine
  beendete Sitzung bekäme einen Gesprächsschritt, den die Teilnehmer:in in ihrem
  Gespräch nie gesehen hat; eine Markierung verschöbe das Problem in jede
  Auswertung.
- **Ein persistierter Zustand „Schritt läuft“ gegen den Doppelklick**:
  verworfen. Er bräuchte einen Ausweg für abgerissene Anfragen, also einen
  Timeout, den ADR-0061 ausschließt, und schützte nicht vor dem Ende der Sitzung
  in einem anderen Tab.
- **Beide parallelen Schritte nacheinander ablegen**: verworfen. Der zweite
  Antwortversuch kennt den ersten Schritt nicht; das Transkript zeigte eine
  Antwort auf einen Verlauf, den es so nie gab.

## Folgen

- `status_setzen`, `diagnose_setzen` und `sitzung_abbrechen` melden, ob der
  Übergang gelang. Der Ausgang eines Gesprächsschritts kennt `VERFALLEN`.
- Die Oberfläche sperrt die Knöpfe während eines laufenden Schritts (#486); die
  Absicherung hier gilt unabhängig davon.

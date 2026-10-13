---
status: accepted
---

# Das Gesprächsbudget gehört der Vignette, ist unsichtbar, und seine Uhr steht an der Sitzung

Dieses ADR fasst den Stand von ADR-0012 (samt Nachführungen durch ADR-0042 und
#60) und ADR-0042 zusammen und ersetzt beide.

## Das Budget ist ein Feld der Vignette

Das **Gesprächsbudget** ist ein Feld der Vignette. Es wird mit ihr finalisiert
und eingefroren; weder Erhebung noch Training dürfen es überschreiben. Das
Budget ist eine didaktische Aussage über die Vignette: Ein Fehlermuster, das
erst nach mehreren gezielten Nachfragen sichtbar wird, braucht mehr
Gesprächsschritte als eines, das beim ersten Nachhaken auffällt. Wer es von
außen verstellte, verstellte die Schwierigkeit der Vignette, ohne sie zu
versionieren, und zwei Sitzungen derselben finalen Fassung wären nicht mehr
gleich dargeboten.

Pro Vignette ist genau ein Budget-Typ aktiv: **Gesprächsschritte** oder
**Zeitbegrenzung**.

## Die Uhr läuft nur, wenn die Teilnehmer:in am Zug ist

Bei einem Zeitbudget hält die Uhr beim Absenden an und läuft weiter, sobald die
Antwort steht. Gemessen wird, was gemessen werden soll: die Zeit, die die
angehende Lehrperson für ihre diagnostischen Entscheidungen aufwendet.
Modelllatenz schwankt zwischen Teilnehmenden und über den Tag; sie ins Budget
zu ziehen hieße, sie in die Daten zu ziehen. Aus demselben Grund kosten
Fehlversuche (ADR-0011) keine Budgetzeit.

Bei schrittbasiertem Budget läuft überhaupt keine Uhr. Dort wird nicht gemessen
und pausiert, sondern gar nicht erst angesetzt: Die Null einer solchen Sitzung
ist die Abwesenheit einer Messung, kein gemessener Wert. Der Export trägt sie
als echte Null, und die Spalte ist nur zusammen mit dem Budget-Typ der
Vignettenfassung zu lesen (ADR-0029).

## Der Stand steht an der Sitzung, die Zeitquelle ist die Wanduhr

Die verbrauchte Zeit und der Startpunkt der offenen Spanne sind **Felder der
Sitzung** (`verbrauchte_zeit`, `offene_spanne_seit`), nicht Einträge der
Browser-Session. Die Sitzung ist die atomare Auswertungseinheit, und die
verbrauchte Zeit ist selbst eine Größe der Datenspur: Sie sagt etwas über
diagnostische Ökonomie. Ein Wert, der Forschungsdatum ist, gehört nicht in
einen Browser. Der Teilnahme-Link ist stabil und der Wiedereinstieg vorgesehen
(ADR-0006, ADR-0058); ein zweiter Browser muss korrekt fortsetzen, statt das
Budget neu geschenkt zu bekommen.

Geführt werden die Felder vom **Sink** über `zug_beginnen` und `zug_beenden`
(ADR-0055). Der **Budgetstand** ist ein speicherloses Wertobjekt mit genau
einer Implementierung; seine Speicher sind die Sink-Adapter: Sitzungsfelder im
`DBSink` und `FluechtigerSink`, Browser-Session im `ScratchSink`. Der Probelauf
misst über dieselbe Quelle, bleibt aber schreibfrei (ADR-0014).

Die Zeitquelle ist `timezone.now()`, nicht `monotonic()`. Ein prozessrelativer
Wert ist über Worker und Prozessneustarts hinweg bedeutungslos, und genau diese
Betriebsform ist der Grund, aus dem persistiert wird. Was die Wanduhr
schlechter kann, Sprünge durch Zeitumstellung oder NTP-Korrektur, ist hier ohne
Gewicht: Budgets sind in Minuten bemessen.

**Die offene Spanne wird beim Wiedereinstieg neu angesetzt.** Jeder erneute
Aufruf der Gesprächsseite setzt sie neu an; die bereits verbrauchte Zeit bleibt
erhalten. Wer vor dem Absenden neu lädt, verschenkt die Denkzeit der offenen
Spanne an sich selbst. Die Alternative, die Spanne bis zum Wiedereinstieg
mitzuzählen, hätte nach einem Absturz oder einer über Nacht offenen Seite das
Budget aufgebraucht, ohne dass jemand gedacht hätte. Bei einem unsichtbaren
Budget, das Obergrenze und nicht Soll ist, ist der geschenkte Rest der
harmlosere Fehler.

## Das Budget ist unsichtbar, und das Gespräch darf früher enden

Der Teilnehmer:in wird der Budgetstand nicht angezeigt, für keinen der beiden
Typen. „Unsichtbar" meint die Darstellung, nicht die Lebensdauer: Sichtbar wird
ein Wert dadurch, dass ein Template ihn ausgibt, nicht dadurch, dass eine
Spalte ihn trägt. Da keine Uhr sichtbar ist, muss auch niemandem erklärt
werden, warum sie zwischendurch steht.

Die Teilnehmer:in darf das Gespräch **jederzeit vorzeitig beenden** und in den
Debrief gehen; das Budget ist eine Obergrenze, kein Soll. Erschöpft sich das
Budget während eines laufenden Gesprächsschritts, wird dieser zu Ende geführt;
eine abgeschnittene Antwort wäre ein beschädigter Datenpunkt. Danach folgt der
Debrief.

## Die Obergrenze gegen ewig offene Sitzungen ist nicht das Budget

Die tatsächliche Sitzungsdauer übersteigt das Zeitbudget, unter Umständen
deutlich. Für Erhebungen ist die harte Obergrenze der **Erhebungszeitraum**:
Nach dem Fenster gilt eine unvollständige Teilnahme als verfallen und ist nicht
fortsetzbar (#60). Für Trainingssitzungen gibt es keine Obergrenze; das ist als
#237 offen. Eine laufende Sitzung endet nur durch Abschließen, Scheitern oder
ausdrücklichen Abbruch, und je Teilnahme läuft höchstens eine (ADR-0053).

## Erwogene Optionen

- **Das Budget als Parameter an Training oder Erhebung** — verworfen. Es
  verstellte die Schwierigkeit der Vignette ohne Versionierung. Eine
  Ausbilder:in, die Anfänger:innen mehr Zeit geben will, braucht eine zweite
  finale Vignettenfassung; sie ist in der Datenspur sauber unterscheidbar.
- **Die Uhr in der Browser-Session** — so bis ADR-0042; verworfen, weil ein
  Fensterschluss ein Forschungsdatum löschte und ein zweiter Browser das Budget
  neu bekam.
- **`monotonic()` als Zeitquelle** — verworfen; über Prozessgrenzen ohne
  Bezugspunkt.
- **Die offene Spanne bis zum Wiedereinstieg mitzählen** — verworfen; das
  verbrannte Budget ist der schlimmere Fehler als der geschenkte Rest.
- **Modelllatenz und Fehlversuche ins Budget rechnen** — verworfen; sie wären
  dann in den Daten.

## Folgen

- Die verbrauchten Schritte beziehungsweise die verbrauchte Zeit sind eine
  Größe der Datenspur und stehen im Export (ADR-0029). Unter einem Zwang, das
  Budget auszuschöpfen, wären sie konstant und wertlos.
- Ein zu früh beendetes Gespräch sieht in den Daten aus wie ein effizientes.
  Das lässt sich nicht am Budget reparieren, nur an der Instruktion; die
  Diagnose zeigt, wer etwas erkannt hat.
- Beim Zeitbudget endet das Gespräch für die Teilnehmer:in unangekündigt. Die
  Instruktion einer Erhebung sollte ankündigen, **dass** das Gespräch begrenzt
  ist, nicht wie stark.
- Ein Browserwechsel, ein Fensterschluss und eine verfallene Session kosten
  kein Budget mehr, bis auf die offene Spanne ohne Schreibpunkt.
- Persistiert wird der Stand einer angehaltenen Uhr, nicht eine Sitzungsdauer.
  Der Startpunkt der offenen Spanne ist interne Buchführung und erscheint
  nicht im Export.

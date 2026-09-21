---
status: accepted
---

# Die Uhr des Gesprächsbudgets wird an der Sitzung persistiert

Die verbrauchte Zeit eines zeitbegrenzten Gesprächsbudgets und der Startpunkt
der laufenden Spanne sind **Felder der Sitzung**. Sie leben nicht mehr in der
Browser-Session, und die Zeitquelle ist die Wanduhr, nicht `monotonic()`.

ADR-0012 bleibt in der Sache unangetastet: Das Budget gehört weiter der
Vignette, die Uhr hält weiter beim Absenden an, und der Teilnehmer:in wird
weiter nichts angezeigt. Dieses ADR führt allein den **Speicherort** und die
**Zeitquelle** nach.

## 1. »Unsichtbar« meint die Darstellung, nicht die Lebensdauer

ADR-0012 sagt: »Der Teilnehmer:in wird der Budgetstand nicht angezeigt.« Das ist
eine Aussage über die Oberfläche. Dass der Stand deshalb auch flüchtig sein
müsse, folgt daraus nicht — die Flüchtigkeit war nie eine Entscheidung, sondern
eine Nebenwirkung des Speicherorts: Wer in die Browser-Session schreibt, schreibt
etwas, das ein Fensterschluss löscht.

Ein persistierter Stand ist genauso unsichtbar wie ein flüchtiger. Sichtbar wird
ein Wert dadurch, dass ein Template ihn ausgibt, nicht dadurch, dass eine Spalte
ihn trägt. Die Zusicherung aus ADR-0012 — es gibt keine Uhr auf dem Schirm, und
niemandem muss erklärt werden, warum sie zwischendurch steht — gilt unverändert.

## 2. Der Stand gehört an die Sitzung

Die Sitzung ist die atomare Auswertungseinheit, und die verbrauchte Zeit ist
laut ADR-0012 selbst eine Größe der Datenspur: Sie sagt etwas über diagnostische
Ökonomie. Ein Wert, der Forschungsdatum ist, gehört nicht in einen Browser.

Das Gegenargument der Flüchtigkeit war operativ, nicht fachlich — und es kehrt
sich um: Der Teilnahme-Link ist stabil, der Wiedereinstieg ausdrücklich
vorgesehen (ADR-0006, ADR-0018), und seit #157 wird der Fortschritt einer
Erhebungsbindung in der Datenbank geführt. Für schrittbasierte Budgets stimmt
die Zusage »ein zweiter Browser setzt korrekt fort« damit bereits; für
zeitbasierte bekäme die Teilnehmer:in ihr Budget beliebig oft geschenkt. Dieselbe
Asymmetrie, die ADR-0041 zwischen den beiden Andockpunkten aufgelöst hat, fällt
hier zwischen den beiden Budget-Typen.

Geführt werden die Felder vom **Sink** — der Naht, die die Uhr schon heute trägt
(ADR-0016). Die Änderung gehört dorthin und nicht in eine View; eine dritte Naht
entsteht nicht.

## 3. Die Zeitquelle ist die Wanduhr

`monotonic()` liefert einen **prozessrelativen** Wert. Die Differenz zweier
solcher Werte über Worker oder Prozessneustarts hinweg ist bedeutungslos — und
genau diese Betriebsform ist der Grund, aus dem persistiert wird. Ein Wert, der
den Prozess nicht überlebt, in einer Spalte, die ihn überleben soll, wäre die
Persistierung einer Zahl ohne Bezugspunkt.

Die Uhr ist deshalb `timezone.now()`. Was die Wanduhr schlechter kann —
Sprünge durch Zeitumstellung oder NTP-Korrektur —, ist hier ohne Gewicht:
Budgets sind in Minuten bemessen, nicht in Millisekunden. Ein um Sekunden
verstellter Bezugspunkt ändert an einer Obergrenze nichts, ein bedeutungsloser
Bezugspunkt alles.

Das betrifft auch den Probelauf: Er misst seine Gesprächszeit über dieselbe
Quelle, bleibt aber schreibfrei und in der Browser-Session (ADR-0014). Die
Zeitquelle ist eine Frage der Bedeutung, die Persistierung eine der Rolle.

## 4. Die offene Spanne wird neu angesetzt

Beim Wiedereinstieg steht die Frage, was mit der Zeit seit dem letzten
Schreibpunkt geschieht. Entschieden ist: **Jeder erneute Aufruf der
Gesprächsseite setzt die laufende Uhr neu an; die bereits verbrauchte Zeit
bleibt erhalten.** Es wird weder geschätzt noch etwas Akkumuliertes verworfen.

Der Preis steht auf der Seite der Teilnehmer:in: Wer vor dem Absenden neu lädt,
verschenkt die Denkzeit der offenen Spanne an sich selbst. Die Alternative wäre,
die Spanne bis zum Wiedereinstieg mitzuzählen — dann hätte ein Absturz oder eine
über Nacht offen gebliebene Seite das Budget aufgebraucht, ohne dass jemand
gedacht hätte. Bei einem unsichtbaren Budget, das Obergrenze und nicht Soll ist,
ist der geschenkte Rest der harmlosere Fehler als das verbrannte Budget: Er
verlängert die Denkzeit, er beendet kein Gespräch.

## Consequences

- Die verbrauchte Gesprächszeit steht in der Datenbank und nimmt damit den Weg
  in den Export (ADR-0029). Sie ist ohnehin eine Größe der Datenspur; bisher
  war sie es nur auf dem Papier.
- Ein Browserwechsel, ein Fensterschluss und eine verfallene Session kosten
  kein Budget mehr — bis auf die offene Spanne, die keinen Schreibpunkt hatte.
- Die gemessene Zeit ist weiterhin die Zeit des Teilnahmezugs, nicht die
  Wanduhrzeit zwischen erstem und letztem Schritt: Modelllatenz und Fehlversuche
  bleiben außen vor (ADR-0012, ADR-0011). Persistiert wird der Stand einer
  angehaltenen Uhr, nicht eine Sitzungsdauer.
- Die Migration bringt für Sitzungen, die vor ihr entstanden sind, den
  Anfangsstand null. Das ist die bisherige Wirklichkeit, nur explizit.

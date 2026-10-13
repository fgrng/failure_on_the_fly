---
status: accepted
---

# Die Denkspur: pro Antwort aus dem Ausgabeschema, Regieperspektive, im Verlauf, für Teilnehmende nie sichtbar

Dieses ADR fasst den Stand von ADR-0005 (samt Nachführungen durch ADR-0049,
ADR-0052, ADR-0062 und ADR-0063), ADR-0062 und ADR-0063 zusammen und ersetzt
alle drei. Die Einsicht in persistierte Sitzungen regelt weiterhin ADR-0049,
die Nachrichtenrollen ADR-0052; beide bleiben unberührt.

## Die Denkspur entsteht zu jeder Antwort

Die **Denkspur** entsteht **zu jeder einzelnen Antwort** der simulierten
Schüler:in, nicht als zusammenfassende Selbstauskunft am Ende einer Sitzung.
Nur so wird nachvollziehbar, ob das Fehlermuster *durchgängig* konsistent
angewandt wurde; genau das ist der forschende und didaktische Kern des
Instruments. Ein Gesprächsschritt ohne Denkspur ist unzulässig (ADR-0061).

## Die Denkspur ist immer ein Feld des Structured Output

Jeder Modellaufruf liefert ein strukturiertes Objekt, dessen Schema das
Feld `denkspur` **vor** dem Feld `aeusserung` führt; die Reihenfolge im Schema
ist es, die das Reasoning tatsächlich vor der Äußerung entstehen lässt. Das
gilt für **jede** Modell-Konfiguration, auch für Reasoning-Modelle.

Eine **native Reasoning-Spur** des Anbieters wird **nicht** aufbewahrt. Drei
Gründe: Native Reasoning-Spuren sind bei mehreren Anbietern nur
zusammengefasst abrufbar und damit Ausgabe eines zweiten, unbekannten Modells.
Sie sind nicht steuerbar; wir können sie nicht bitten, aus der Regel des
Fehlermusters zu argumentieren. Und ihre Herkunft hinge an der
Modell-Konfiguration, die sich aus Betriebsgründen ändert; das Artefakt würde
seinen Charakter bei einem Betriebsvorgang wechseln. Eine Spalte, die
zwischen zwei Modell-Konfigurationen derselben Erhebung Verschiedenes
bedeutet, trägt genau den Vergleich nicht, für den man sie ziehen wollte. Sie
fiele überdies bei etlichen Modellen im Structured-Output-Modus stillschweigend
weg und wäre dann nicht von „das Modell hat nicht nachgedacht“ zu
unterscheiden. Die Naht zum Sprachmodell gibt deshalb allein das geparste
Objekt zurück; es reist nichts am Schema vorbei.

## Ein Schemawechsel verlangt eine neue finale Kern-Fassung

Das Ausgabeschema ist eine Code-Konstante, die Beschreibung dazu steht im
versionierten Text des Simulationskerns, und eine finale Kern-Fassung ist
unveränderlich. Eine Schemaänderung gälte sofort für alle Fassungen, auch für
solche, deren Ausgabebeschreibung noch das alte Schema erklärt; das Ergebnis
wäre keine erkennbar gebrochene Antwort, sondern stille Qualitätsminderung.
Eine Änderung am Ausgabeschema ist deshalb nur zusammen mit einer neuen
finalen Kern-Fassung zulässig. Altfassungen bleiben dabei bewusst beim alten
Schema zurück.

## Die Denkspur ist Regieperspektive, die Äußerung bleibt in der Rolle

Die Denkspur ist die **Regieperspektive** der Simulation auf die nächste
Äußerung: Sie plant, was die simulierte Schüler:in gleich sagt, darf dafür
Fachsprache benutzen, das Fehlermuster beim Namen nennen und eine Nachricht
als Korrektur oder Rollenbruchversuch einordnen. Nur die **Äußerung** ist in
der Rolle. Der Simulationskern sagt das ausdrücklich; die frühere Lesart
„leises Selbstgespräch in der Rolle“ (Kern-Fassungen bis #438) ist abgelöst
(#466).

Drei Gründe: Die Denkspur ist ein Forschungsdatum und soll prüfbar machen, ob
das Fehlermuster in jedem Zug konsistent angewandt wurde; das verlangt die
Sprache der Vignette, nicht die eines Kindes. Ein In-Rolle-Selbstgespräch kann
weder eine Korrektur als solche benennen noch den „einen Schritt“ auswählen,
ohne die Rolle zu verlassen; der Probelauf zu #438 zeigte, dass die Denkspur
ohnehin in die zweite oder dritte Person rutscht. Und eine feste
Markierungsfolge (Gefragt, Regel, Zeigen, Ton) gibt der Denkspur ein
prüfbares Abschlusskriterium, das ein freies Selbstgespräch nicht hat.

Die Lesart gilt für Kern-Fassungen ab #466. Gepinnte Fassungen in laufenden
Erhebungen behalten ihre Lesart.

## Die Denkspur fließt in den Verlauf zurück

Die simulierte Schüler:in sieht ihre früheren Antworten im Verlauf
vollständig: Jede `assistant`-Nachricht trägt Denkspur und Äußerung als
JSON-Objekt nach dem Ausgabeschema, `{"denkspur": "…", "aeusserung": "…"}`.
Der Verlauf reist als **native Konversationsnachrichten** des Anbieters, nicht
als nacherzählter Verlaufsblock im User-Prompt (#467).

Zwei Gründe: Die Schüler:in kennt ihre früheren Überlegungen und kann über
Gesprächsschritte hinweg konsistent begründen, auch wenn die Teilnehmer:in
nach einem früheren Schritt fragt. Und der Verlauf zeigt, was das Modell
tatsächlich ausgegeben hat, statt ihm eine Klartext-Vorgeschichte
unterzuschieben, die es so nie geschrieben hat und die nicht dem Format
entspricht, das es selbst ausgeben muss. Das Präzedenz-Risiko, mit dem
ADR-0005 den Verlauf ohne Denkspur begründete (eine frühe Fehlanwendung
würde zum Präzedenzfall, und die Simulation bliebe konsistent mit sich selbst
statt mit der Vignette), war eine Annahme und wurde nie empirisch geprüft;
zudem wirken die sichtbaren Äußerungen ohnehin als Präzedenzfall.

Das JSON wird aus den gespeicherten Feldern rekonstruiert
(`json.dumps(…, ensure_ascii=False)`, Schlüsselreihenfolge wie im Schema),
nicht aus einer aufbewahrten Rohantwort. Es ist inhaltlich identisch mit der
Ausgabe; Abweichungen in Leerraum oder Escapes sind für das Modell
bedeutungslos.

Weil die Denkspur im Verlauf steht, schreibt die Regieperspektive nur, was sie
braucht, und führt keine Listen zu vermeidender Wörter, die das Modell im
nächsten Zug wiederläse.

## Sichtbarkeit

Die Sichtbarkeit ist bewusst gestaffelt:

- **Autor:in im Probelauf:** live sichtbar; sie muss prüfen können, ob die
  Regel greift.
- **Teilnehmer:in:** **nie**, weder während der Sitzung noch nachträglich,
  auch nicht im Training und nicht in einer Abschrift. Wer die Denkspur
  liest, diagnostiziert nicht mehr, sondern liest ab.
- **Forschende:r:** immer, als Teil der Datenspur und des Exports.
- **Ausbilder:in:** nie. Ihre Fremdeinsicht zeigt, was die Teilnehmer:in sieht
  (ADR-0049).

Die Zusage sitzt im Rendering, nicht in den Daten: Der CheckConstraint auf dem
Gesprächsschritt verlangt Denkspur und Äußerung gemeinsam, und eine Abschrift
(ADR-0058) trägt die Denkspur als Kopie mit.

## Erwogene Optionen

- **Native Reasoning-Spur aufbewahren oder als Denkspur verwenden** —
  verworfen, siehe oben: nicht steuerbar, nicht anbieterstabil, nicht
  vergleichbar.
- **Verlauf ohne Denkspur** (ADR-0005) — verworfen: Das Präzedenz-Risiko war
  unbelegt, und der Verlauf soll zeigen, was das Modell ausgegeben hat.
- **Rohantwort byte-genau speichern und zurückspielen** — verworfen. Das
  Schema hat genau zwei Felder ohne Zusätze; die Rohantwort kostete eine
  Migration und einen Eingriff in den Exportkontrakt (ADR-0029).
- **Pro Kern-Fassung umschalten, ob die Denkspur im Verlauf steht** —
  verworfen. Wie bei ADR-0052 ist die Nachrichtenordnung Code und gilt ab dem
  Deploy für alle Fassungen, auch für gepinnte in laufenden Erhebungen; dass
  eine Datenspur Gespräche beider Ordnungen enthält, nehmen wir hin.
- **Die Denkspur über ein natives Reasoning-Feld des Anbieters zurückgeben**
  — verworfen. Nicht jeder Anbieter kennt eins.
- **Denkspur als Selbstgespräch in der Rolle** (Kern-Fassungen bis #438) —
  verworfen. Die Perspektive hielt im Probelauf nicht, und die Fachsprache der
  Vignette ließ sich darin nur mit Verrenkungen vermeiden.
- **Zwei Felder: Regie und In-Rolle-Gedanke** — verworfen. Ein Schemawechsel
  verlangt eine neue finale Kern-Fassung, und das zweite Feld hätte keinen
  Abnehmer.
- **Trainingsteilnehmenden nachträglich zeigen, „wie die Simulation gedacht
  hat“** — verworfen, so didaktisch reizvoll es ist.

## Folgen

- Die Vignette braucht eine **Arbeitsheft-Bildbeschreibung**, eine textuelle
  Fassung dessen, was im Arbeitsheft-Bild zu sehen ist. Sie ist Alt-Text für
  Menschen und speist, an der Bildposition zusammen mit dem Arbeitsheft-Text,
  das Reasoning.
- Die Menge der zulässigen Anbieter und Modelle ist auf solche eingeschränkt,
  die Structured Output beherrschen. Weitere Anforderungen an das Modell gibt
  es nicht; ob es daneben natives Reasoning führt, ist gleichgültig.
- Der Verlauf mit Denkspur gilt gleich für Sitzung, Probelauf und
  Evalgespräch. Die simulierte Lehrperson sieht die Schüler:in weiterhin nur
  über ihre Äußerungen; am Bewerter ändert sich nichts (ADR-0052).
- Ein gescheiterter Gesprächsschritt bleibt ganz aus dem Verlauf (ADR-0061).
- Der Rollenschutz gilt der Äußerung. Die Denkspur darf „Rollenbruchversuch“
  schreiben, die Äußerung reagiert als Kind.
- Art. 15 DSGVO erfasst die Kopie einer Abschrift samt Denkspur, obwohl die
  Teilnehmer:in sie nie sieht (ADR-0058).

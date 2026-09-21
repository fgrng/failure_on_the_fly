---
status: accepted
---

# Denkspur entsteht pro Antwort; Teilnehmende sehen sie nie

Die **Denkspur** — das interne Reasoning der simulierten Schüler:in — entsteht **zu jeder einzelnen Antwort**, nicht als zusammenfassende Selbstauskunft am Ende einer Sitzung. Nur so wird nachvollziehbar, ob das Fehlermuster *durchgängig* konsistent angewandt wurde; genau das ist der forschende und didaktische Kern des Instruments.

## Die Denkspur ist immer ein Feld des Structured Output

Jeder Modellaufruf liefert ein strukturiertes Objekt, dessen Schema das Reasoning-Feld **vor** dem Äußerungsfeld führt — die Reihenfolge im Schema ist es, die das Reasoning tatsächlich vor der Äußerung entstehen lässt. Das gilt für **jede** Modell-Konfiguration, auch für Reasoning-Modelle.

Eine **native Reasoning-Spur** des Anbieters wird **nicht** aufbewahrt. Drei Gründe: Native Reasoning-Spuren sind bei mehreren Anbietern nur zusammengefasst abrufbar und damit Ausgabe eines zweiten, unbekannten Modells. Sie sind nicht steuerbar — wir können sie nicht bitten, aus der Regel des Fehlermusters zu argumentieren. Und ihre Herkunft hinge an der Modell-Konfiguration, die sich aus Betriebsgründen ändert; das Artefakt würde seinen Charakter bei einem Betriebsvorgang wechseln.

Damit wäre sie kein auswertbares Forschungsdatum: Eine Spalte, die zwischen zwei Modell-Konfigurationen derselben Erhebung Verschiedenes bedeutet, trägt genau den Vergleich nicht, für den man sie ziehen wollte. Sie fiele überdies bei etlichen Modellen im Structured-Output-Modus stillschweigend weg und wäre dann nicht von „das Modell hat nicht nachgedacht" zu unterscheiden. Die Naht zum Sprachmodell gibt deshalb allein das geparste Objekt zurück; es reist nichts am Schema vorbei.

## Ein Schemawechsel verlangt eine neue finale Kern-Fassung

Das Ausgabeschema ist eine Code-Konstante, die Beschreibung dazu steht im versionierten Text des Simulationskerns — und eine finale Kern-Fassung ist unveränderlich. Eine Schemaänderung gälte sofort für alle Fassungen, auch für solche, deren Ausgabebeschreibung noch das alte Schema erklärt; das Ergebnis wäre keine erkennbar gebrochene Antwort, sondern stille Qualitätsminderung. Eine Änderung am Ausgabeschema ist deshalb nur zusammen mit einer neuen finalen Kern-Fassung zulässig. Altfassungen bleiben dabei bewusst beim alten Schema zurück.

## Die Denkspur fließt nicht in den Kontext zurück

Der Gesprächsverlauf, der bei jedem Zug an das Modell zurückgeht, enthält die Eingaben der Teilnehmer:in und die sichtbaren Äußerungen der simulierten Schüler:in — beide Gesprächsseiten, aber keine Denkspur. Jeder Zug leitet das Verhalten neu aus dem Fehlermuster im System-Prompt ab. Anderenfalls würde eine frühe Fehlanwendung im Kontext zum Präzedenzfall, und die Simulation bliebe konsistent mit *sich selbst* statt mit der Vignette — womit das Instrument genau die Frage nicht mehr beantwortet, für die es gebaut wird.

Der Verlauf reist als **native Konversationsnachrichten** des Anbieters, nicht als nacherzählter Verlaufsblock im User-Prompt. Die Einträge der simulierten Schüler:in tragen ausschließlich ihre sichtbare Äußerung als Klartext — die Denkspur bleibt also auch dann draußen, wenn die Antwort, aus der sie stammt, wieder im Kontext steht.

## Sichtbarkeit

Die Sichtbarkeit ist bewusst gestaffelt:

- **Autor:in im Probelauf:** live sichtbar — sie muss prüfen können, ob die Regel greift.
- **Teilnehmer:in:** **nie** — weder während der Sitzung noch nachträglich, auch nicht im Training. Wer die Denkspur liest, diagnostiziert nicht mehr, sondern liest ab.
- **Forschende:r:** immer, als Teil der Datenspur und des Exports.
- **Ausbilder:in:** im Rahmen der Sitzungseinsicht ihres eigenen Trainings.

## Folgen

- Die Vignette braucht eine **Arbeitsheft-Bildbeschreibung** — eine textuelle Fassung dessen, was im Arbeitsheft-Bild zu sehen ist. Sie ist Alt-Text für Menschen und speist, an der Bildposition zusammen mit dem Arbeitsheft-Text, das Reasoning.
- Der didaktisch reizvolle Gedanke, Trainingsteilnehmenden nachträglich zu zeigen, „wie die Simulation gedacht hat", ist verworfen.
- Die Menge der zulässigen Anbieter und Modelle ist auf solche eingeschränkt, die Structured Output beherrschen. Weitere Anforderungen an das Modell gibt es nicht; ob es daneben natives Reasoning führt, ist gleichgültig.
- Weil die Denkspur nicht in den Kontext zurückfließt, bleibt der Kontext klein und die Denkspur ein reines Ausgabeprodukt.

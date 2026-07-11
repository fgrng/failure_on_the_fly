---
status: accepted
---

# Denkspur entsteht pro Antwort; Teilnehmende sehen sie nie

Die **Denkspur** — das interne Reasoning der simulierten Schüler:in — entsteht **zu jeder einzelnen Antwort**, nicht als zusammenfassende Selbstauskunft am Ende einer Sitzung. Nur so wird nachvollziehbar, ob das Fehlermuster *durchgängig* konsistent angewandt wurde; genau das ist der forschende und didaktische Kern des Instruments.

## Die Denkspur ist immer ein Feld des Structured Output

Jeder Modellaufruf liefert ein strukturiertes Objekt, dessen Schema das Reasoning-Feld **vor** dem Äußerungsfeld führt — die Reihenfolge im Schema ist es, die das Reasoning tatsächlich vor der Äußerung entstehen lässt. Das gilt für **jede** Modell-Konfiguration, auch für Reasoning-Modelle.

Liefert das Modell zusätzlich eine **native Reasoning-Spur**, wird sie als optionales Feld am **Gesprächsschritt** aufbewahrt — neben der Denkspur, nie als sie. Sie steht damit im selben Objekt wie Eingabe, Denkspur und Äußerung, und nicht in der Fehlversuch-Schreibbahn aus ADR-0011: Sie gehört zu einer geglückten Antwort, nicht zu einer verworfenen.

Drei Gründe: Native Reasoning-Spuren sind bei mehreren Anbietern nur zusammengefasst abrufbar und damit Ausgabe eines zweiten, unbekannten Modells. Sie sind nicht steuerbar — wir können sie nicht bitten, aus der Regel des Fehlermusters zu argumentieren. Und ihre Herkunft hinge an der Modell-Konfiguration, die sich aus Betriebsgründen ändert; die Denkspur würde ihren Charakter bei einem Betriebsvorgang wechseln.

## Die Denkspur fließt nicht in den Kontext zurück

Der Gesprächsverlauf, der bei jedem Zug an das Modell zurückgeht, enthält ausschließlich die sichtbaren Äußerungen. Jeder Zug leitet das Verhalten neu aus dem Fehlermuster im System-Prompt ab. Anderenfalls würde eine frühe Fehlanwendung im Kontext zum Präzedenzfall, und die Simulation bliebe konsistent mit *sich selbst* statt mit der Vignette — womit das Instrument genau die Frage nicht mehr beantwortet, für die es gebaut wird.

## Sichtbarkeit

Die Sichtbarkeit ist bewusst gestaffelt:

- **Autor:in im Probelauf:** live sichtbar — sie muss prüfen können, ob die Regel greift.
- **Teilnehmer:in:** **nie** — weder während der Sitzung noch nachträglich, auch nicht im Training. Wer die Denkspur liest, diagnostiziert nicht mehr, sondern liest ab.
- **Forschende:r:** immer, als Teil der Datenspur und des Exports.
- **Ausbilder:in:** im Rahmen der Sitzungseinsicht ihres eigenen Trainings.

## Consequences

- Die Vignette braucht eine **Arbeitsheft-Beschreibung** — eine textuelle Fassung dessen, was im Arbeitsheft-Inhalt zu sehen ist. Das Bild ist für den Menschen, der Text speist das Reasoning.
- Der didaktisch reizvolle Gedanke, Trainingsteilnehmenden nachträglich zu zeigen, „wie die Simulation gedacht hat", ist verworfen.
- Die Menge der zulässigen Anbieter und Modelle ist auf solche eingeschränkt, die Structured Output beherrschen. Ob ein Modell Structured Output und natives Reasoning zugleich zulässt, ist bei der Implementierung je Anbieter zu prüfen.
- Weil die Denkspur nicht in den Kontext zurückfließt, bleibt der Kontext klein und die Denkspur ein reines Ausgabeprodukt.

---
status: accepted
---

# Die Denkspur fließt in den Verlauf zurück

Die simulierte Schüler:in sieht ihre früheren Antworten im Verlauf vollständig: Jede `assistant`-Nachricht trägt Denkspur und Äußerung als JSON-Objekt nach dem Ausgabeschema, `{"denkspur": "…", "aeusserung": "…"}`. Das löst den Abschnitt „Die Denkspur fließt nicht in den Kontext zurück“ aus ADR-0005 ab (#467).

Zwei Gründe: Die Schüler:in kennt ihre früheren Überlegungen und kann über Gesprächsschritte hinweg konsistent begründen, auch wenn die Teilnehmer:in nach einem früheren Schritt fragt. Und der Verlauf zeigt, was das Modell tatsächlich ausgegeben hat, statt ihm eine Klartext-Vorgeschichte unterzuschieben, die es so nie geschrieben hat und die nicht dem Format entspricht, das es selbst ausgeben muss. Das Präzedenz-Risiko, mit dem ADR-0005 den Verlauf ohne Denkspur begründete, war eine Annahme und wurde nie empirisch geprüft; zudem wirken die sichtbaren Äußerungen ohnehin als Präzedenzfall.

Das JSON wird aus den gespeicherten Feldern rekonstruiert (`json.dumps(…, ensure_ascii=False)`, Schlüsselreihenfolge wie im Schema), nicht aus einer aufbewahrten Rohantwort. Es ist inhaltlich identisch mit der Ausgabe; Abweichungen in Leerraum oder Escapes sind für das Modell bedeutungslos.

## Considered Options

- **Rohantwort byte-genau speichern und zurückspielen** — verworfen. Das Schema hat genau zwei Felder ohne Zusätze, die Rohantwort enthält nichts darüber hinaus; sie kostete eine Migration und einen Eingriff in den Exportkontrakt (ADR-0029).
- **Pro Kern-Fassung umschalten** — verworfen. Wie bei ADR-0052 ist die Nachrichtenordnung Code und gilt ab dem Deploy für alle Fassungen, auch für gepinnte in laufenden Erhebungen; dass eine Datenspur Gespräche beider Ordnungen enthält, nehmen wir hin.
- **Die Denkspur über ein natives Reasoning-Feld des Anbieters zurückgeben** — verworfen. Nicht jeder Anbieter kennt eins, und ADR-0005 führt Reasoning bewusst nicht über den nativen Weg.

## Consequences

- Gilt gleich für Sitzung, Probelauf und Evalgespräch.
- Die simulierte Lehrperson sieht die Schüler:in weiterhin nur über ihre Äußerungen; am Bewerter ändert sich nichts (ADR-0052).
- Ein gescheiterter Gesprächsschritt bleibt wie bisher ganz aus dem Verlauf (ADR-0011).

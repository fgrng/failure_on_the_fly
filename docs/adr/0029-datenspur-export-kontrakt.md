---
status: accepted
---

# Die Datenspur wird long-relational, selbsttragend und pro Erhebung exportiert

Der Export ist ein veröffentlichter Datenformatvertrag: Änderungen daran können
Analyseskripte und bereits ausgegebene Datensätze brechen. Er liefert einen
ZIP-Download mit relationalen CSV-Dateien nach RFC 4180. Jede Entität hat eine
eigene Tabelle; es gibt keinen Wide-Pivot und kein Einebnen. Das Pivotieren
bleibt der Forschenden und ihrer Auswertungssoftware überlassen.

Die Erhebung ist die Exporteinheit, über alle ihre Stichproben hinweg. Die
Stichprobe ist als Spalte an der Teilnahme enthalten und bildet damit die in
`CONTEXT.md` gemeinte Gruppenstruktur im Export ab. Ein Export je Stichprobe
wäre kein Abbild des Untersuchungsdesigns, sondern ein willkürlicher Ausschnitt.

Der Export ist selbsttragend: Die tatsächlich verwendeten Vignetten- und
Simulationskern-Fassungen sowie Modell-Konfigurationen werden mit vollständigem
Inhalt in eigenen Tabellen ausgeliefert und per ID referenziert. Kein
exportierter Fremdschlüssel zeigt ins Leere. So bleibt der Datensatz ohne
Datenbankzugriff interpretierbar, ohne denselben Fassungstext in jeder
Sitzungszeile zu wiederholen.

Die CSV schreibt `NA` für `NULL`; ein Leerstring bleibt leer. Ein
leeres CSV-Feld würde beide Werte einebnen. Das Ausgabeschema der
Sprachmodell-Naht prüft Denkspur und Äußerung nicht auf Nichtleere: Eine
inhaltsleere, aber erfolgreiche Antwort ist daher möglich. Der antwortlose
Gesprächsschritt nach ADR-0011 trägt dagegen `NULL`. Nur `NA` bewahrt diesen
Abbruch als unterscheidbaren Befund.

Historien-Tabellen werden nicht exportiert. Sie enthalten über ihre
Eigentümerinnen Klarnamen und gehören deshalb nicht in den pseudonymen
Datensatz. Die Historie bleibt allein als Gruppierungsschlüssel der verwendeten
Fassungen erhalten.

Transkribierte Eingaben sind im Export derzeit nicht erkennbar: Nach der
Transkription wird nur ihr Text als gewöhnliche Eingabe gespeichert. Diese
bekannte Grenze wird in #122 behandelt und blockiert den Export nicht.

## Considered Options

- **Wide-Export mit einer Zeile je Teilnahme oder Sitzung** — verworfen. Er
  würde Gesprächsschritte, Fehlversuche und verwendete Fassungen entweder
  vervielfachen oder verlieren.
- **Leere Felder für `NULL`** — verworfen. Sie unterschieden einen Abbruch
  nicht mehr von einer erfolgreichen, inhaltsleeren Modellantwort.
- **Historien mit Eigentümerinnen exportieren** — verworfen. Sie würden die
  Pseudonymität des Forschungsdatensatzes brechen.

## Consequences

- CSV-Dateien, Schlüsselspalten und die Bedeutung von `NA` sind Teil des
  stabilen Datenformatvertrags.
- Auswertungen können alle Stichproben einer Erhebung gemeinsam lesen und bei
  Bedarf über die Stichprobenspalte gruppieren.
- Die vollständige Datenspur bleibt ohne Zugriff auf die Anwendungsdatenbank
  nachvollziehbar; Identitäten von Forschenden bleiben außerhalb des Exports.

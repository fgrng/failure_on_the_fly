---
status: accepted
---

# Flüchtige Teilnahme: Gerüst in der DB, Inhalte nie

Wer bei einer Erhebung der Speicherung und Verwendung für Forschungszwecke
(Einwilligung c) widerspricht, macht eine **flüchtige Teilnahme**. Sie läuft
vollständig ab — Diagnosegespräch, Debrief und Diagnose funktionieren wie
gewohnt —, aber Gesprächsschritte (Eingabe, Äußerung, Denkspur, Eingabemodus),
Fehlversuche und Diagnose werden **nie** gespeichert.

Getragen wird das von einer dritten Senke hinter dem bestehenden
Sitzungssenken-Protokoll, dem `FluechtigerSink`:

- Das **Ablaufgerüst** schreibt sie wie der `DBSink` in die Datenbank: die
  Sitzung mit Vignette, Kern, Modell-Konfiguration, Status und Zeitstempeln
  sowie die Budget-Uhr (ADR-0042). Ziehung und Vignettenposition schreibt der
  Ablauf ohnehin selbst.
- Die **Inhalte** der Sitzung hält sie allein in der Browser-Session, je
  Sitzung unter ihrem Primärschlüssel, in derselben Speicherform wie die
  Scratch-Senke des Probelaufs (ADR-0014).

Die Wahl der Senke hängt allein an der Einwilligung in c. Eine unentschiedene
Speicherung — etwa im Training — führt weiter zum `DBSink`.

## Warum das Gerüst in der DB bleibt

Der Ablauf einer Erhebung wird aus der Datenbank abgeleitet (ADR-0041): welche
Sitzung läuft, welche Vignette ansteht, welcher Block offen ist. Eine flüchtige
Teilnahme mit einem zweiten, sessiongebundenen Ablauf hätte diese Logik
verdoppelt. So nutzt sie denselben Ablauf unverändert, und nur das, was die
Teilnehmer:in eingibt oder was aus ihrer Eingabe entsteht, bleibt draußen.

Das Gerüst ist technische Ablaufdaten im Sinne des Systemtexts zu c: welche
Vignetten in welcher Reihenfolge wie lange gespielt wurden. Es wird normal
exportiert (ADR-0029) und weder nachträglich reduziert noch gesperrt.

## Considered Options

- **Ganz in der Session, wie der Probelauf** — verworfen: Der Ablauf, der
  Wiedereinstieg per Token und der Export des Rücklaufs hängen an der DB.
- **Inhalte speichern und beim Export ausfiltern** — verworfen: Die Zusage
  lautet „nie gespeichert“, nicht „nicht ausgewertet“.
- **Die Wahl in die Views legen** — verworfen: Sie gehört an die Naht, die die
  Persistierung schon trägt (ADR-0016); die Views fragen nur nach der Senke
  einer Sitzung. Das gilt für die Inhalte einer Sitzung. Fragebogen-Antworten,
  der Abschlusshinweis und die Abschrift sind keine Sitzungsinhalte; der
  Fragebogen (`block_vorlegen`, `ItemblockFormular`), die Abschlussseite und
  die Abschrift fragen deshalb direkt `Teilnahme.ist_fluechtig` bzw. in
  Abfragen `Teilnahme.fluechtig_q`. Eine andere Formulierung der Regel gibt es
  nicht.

## Consequences

- Das Sitzungssenken-Protokoll hat nun drei Adapter; die Zahl der Nähte bleibt
  gleich. `DBSink` und `FluechtigerSink` teilen Gerüst und Uhr über die
  gemeinsame Basis `GeruestSink` und unterscheiden sich nur darin, wo Schritte
  und Diagnose liegen.
- Ein endgültig gescheiterter Antwortversuch setzt den Status `gescheitert` in
  der DB; der antwortlose Schritt steht nur im Verlauf der Session.
- Der Verlauf einer flüchtigen Sitzung lässt sich nach dem Verlust der
  Browser-Session nicht wiederherstellen. Der `FluechtigerSink` legt den
  Session-Eintrag deshalb schon beim Sitzungsstart an; fehlt er beim
  Wiedereinstieg, wird die laufende Sitzung als `abgebrochen` beendet und der
  Ablauf geht weiter (#281).
- Die gespeicherte Diagnose-Zeile fehlt; die Diagnose im Debrief liest die
  Senke aus der Session.

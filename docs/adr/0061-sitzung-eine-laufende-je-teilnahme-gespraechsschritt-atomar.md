---
status: accepted
---

# Die Sitzung: höchstens eine laufende je Teilnahme, der Gesprächsschritt ist atomar, Fehlversuche stehen neben dem Transkript

Dieses ADR fasst den Stand von ADR-0011 (samt Nachführung durch #27) und
ADR-0053 zusammen und ersetzt beide. Das Gesprächsbudget regelt ADR-0057, die
Teilnahme ADR-0058, den Sink und den Ausgang eines Gesprächsschritts ADR-0055.

## Höchstens eine laufende Sitzung je Teilnahme

Je Teilnahme gibt es höchstens eine Sitzung im Status `laufend`. Die
Datenbank erzwingt das mit einem partiellen `UniqueConstraint` auf der Sitzung
über die Teilnahme mit der Bedingung `status = laufend`. Der Constraint gehört
der Sitzungs-App und gilt für alle Teilnahmen: Training, Erhebung und
flüchtige Teilnahme, deren Gerüst-Sitzung in der DB liegt (ADR-0045). Im
Training ist er die eigentliche Absicherung; in der Erhebung serialisiert
weiterhin die gesperrte Erhebungsbindung (ADR-0041), der Constraint sichert
nur zusätzlich ab. Der Probelauf ist schreibfrei und nicht betroffen.

Anlass (Grilling #205): Im Training merkte sich der Browser die aktuelle
Sitzung über einen einzigen Zeiger in der Browser-Session. Ein zweiter Start
aus einem zweiten Tab oder auf einem anderen Gerät überschrieb ihn; die erste
Sitzung blieb für immer `laufend`, nicht fortsetzbar, nicht abschließbar, und
verfälschte die Statuszählung auf der Trainingsseite und in der Fremdeinsicht.

- **Die laufende Sitzung wird aus der Datenbank abgeleitet**, nicht aus einem
  Browser-Zeiger. Die Sitzungsrouten des Trainings tragen die Sitzungs-pk;
  Fortsetzen gelingt dadurch in jedem Tab, Browser und auf jedem Gerät.
- **Ein zweiter Start im Training wird abgewiesen.** Die Abweisung nennt die
  laufende Sitzung (Vignette, Beginn) und bietet „Fortsetzen“ und „Abbrechen
  und neu starten“ an, auch wenn dieselbe Vignette gewählt wurde. Letzteres
  bricht die laufende Sitzung über den bestehenden Abbruchweg ab, also
  ausdrücklich durch die Teilnehmende ausgelöst, und startet die Wahl in
  derselben Transaktion. Der Start sperrt die Teilnahme; ein `IntegrityError`
  aus dem Constraint führt zur selben Abweisung, nicht zu einem Serverfehler.
- Laufende Sitzungen in verschiedenen Trainings bleiben gleichzeitig erlaubt:
  Jedes Training ist eine eigene Teilnahme.
- Eine laufende Sitzung endet nur durch Abschließen, Scheitern oder einen
  ausdrücklichen Abbruch; einen Timeout gibt es nicht (ADR-0057).

## Der Gesprächsschritt ist atomar

Ein **Gesprächsschritt** existiert nur, wenn Eingabe, Denkspur und sichtbare
Äußerung alle vorliegen. Ein Gesprächsschritt **ohne Denkspur ist
unzulässig**: Die Denkspur ist laut ADR-0005 der Kern des Instruments, und eine
Sitzung mit Lücken darin kann die Frage nach der Konsistenz des Fehlermusters
nicht mehr beantworten, ohne dass es beim Auswerten jemandem auffiele.

Liefert das Modell kein verwertbares Ergebnis (Formatbruch, Anbieterfehler,
Filter), wird begrenzt wiederholt: `MAX_VERSUCHE = 3` in `simulation` (#27).
Scheitert der dritte Versuch, ist der Gesprächsschritt endgültig gescheitert;
die Teilnehmer:in sieht einen Fehler, das Transkript bleibt unberührt und ein
Schritt-Budget unangetastet. Die Wiederholung liegt in `simulation` und nicht
hinter der Sprachmodell-Naht, damit der Fake die Fehlversuch-Schreibbahn prüfen
kann (ADR-0055).

## Fehlversuche gehören in die Datenspur, nicht in das Transkript

Jede verworfene Antwort wird samt ihrem Grund als **Fehlversuch**
protokolliert, sichtbar für Forschende, unsichtbar für Teilnehmende. Wenn das
Modell in Zug sieben zweimal aus der Rolle fällt und beim dritten Versuch eine
brauchbare Antwort liefert, ist das ein Befund über die Simulation, und genau
für solche Befunde wird dieses Instrument gebaut.

Das **Transkript** nimmt sie nicht auf. Es ist die Aufzeichnung der
diagnostischen Gesprächsführung der angehenden Lehrperson (ADR-0007); was
verworfen wurde, hat sie nie gesehen und nie beantwortet, und es war nie Teil
des Verlaufs. Neben dem Transkript existiert damit eine zweite Schreibbahn;
beide gehören zur Datenspur, nur eine zum Gespräch. Fehlversuche verbrauchen
Zeit, aber kein Budget (ADR-0057).

## Erwogene Optionen

- **Eine laufende Sitzung beim Neustart automatisch beenden** — verworfen. Es
  verwirft die Arbeit der Teilnehmenden ohne Rückfrage und erfindet einen
  Abbruch, den niemand ausgelöst hat.
- **Den Browser-Zeiger behalten und nur aufräumen** — verworfen. Ein
  Gerätewechsel verlöre weiterhin den Zugang zur eigenen Sitzung, obwohl die
  Budget-Uhr längst an der Sitzung persistiert ist (ADR-0057).
- **Den Constraint nur für Erhebungen** — verworfen. Gerade im Training
  entstanden die verwaisten Sitzungen.
- **Fehlversuche im Transkript** — verworfen. Die Teilnehmer:in hat sie nie
  gesehen; sie wären kein Teil des Gesprächs.

## Folgen

- Ob ein endgültig gescheiterter Schritt neben dem Transkript stehen bleibt,
  entscheidet der Sink: Die persistierte Sitzung behält ihn als Abbruchschritt
  und setzt den Status `gescheitert`, der Probelauf verwirft ihn (ADR-0055).
- Der Export trägt Fehlversuche in einer eigenen Tabelle und den antwortlosen
  Gesprächsschritt als `NULL` (ADR-0029).
- Der Abschrift-Import bleibt unverändert: Die Quelle hat höchstens eine
  laufende Sitzung, die Kopie hält den Constraint ebenfalls (ADR-0058).

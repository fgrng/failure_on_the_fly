---
status: superseded
superseded-by: ADR-0061
---

# Höchstens eine laufende Sitzung je Teilnahme

Je Teilnahme gibt es höchstens eine Sitzung im Status `laufend`. Die Datenbank
erzwingt das mit einem partiellen `UniqueConstraint` auf der Sitzung über die
Teilnahme mit der Bedingung `status = laufend`. Damit ist die Frage geschlossen,
die ADR-0041 bewusst offengelassen hat (Grilling #205).

Anlass: Im Training merkte sich der Browser die aktuelle Sitzung über einen
einzigen Zeiger in der Browser-Session. Ein zweiter Start, etwa aus einem
zweiten Tab oder auf einem anderen Gerät, überschrieb ihn, und die erste Sitzung
blieb für immer `laufend`: nicht fortsetzbar, nicht abschließbar, und sie
verfälschte die Statuszählung auf der Trainingsseite und in der Fremdeinsicht.

## Entscheidung

- **Der Constraint gilt für alle Teilnahmen**, also für Training, Erhebung und
  flüchtige Teilnahme (deren Gerüst-Sitzung liegt in der DB, ADR-0045). Er
  gehört der Sitzungs-App. Im Training ist er die eigentliche Absicherung; in
  der Erhebung serialisiert weiterhin die gesperrte Erhebungsbindung (ADR-0041),
  der Constraint sichert nur zusätzlich ab. Der Probelauf ist schreibfrei und
  nicht betroffen.
- **Ein zweiter Start im Training wird abgewiesen.** Die Abweisung nennt die
  laufende Sitzung (Vignette, Beginn) und bietet „Fortsetzen“ und „Abbrechen und
  neu starten“ an, auch wenn dieselbe Vignette gewählt wurde. Letzteres bricht
  die laufende Sitzung über den bestehenden Abbruchweg ab, also ausdrücklich
  durch die Teilnehmende ausgelöst, und startet die Wahl in derselben
  Transaktion. Der Start sperrt die Teilnahme; ein `IntegrityError` aus dem
  Constraint führt zur selben Abweisung, nicht zu einem Serverfehler.
- **Die laufende Sitzung wird aus der Datenbank abgeleitet**, nicht aus einem
  Browser-Zeiger. Die Sitzungsrouten des Trainings tragen die Sitzungs-pk;
  Fortsetzen gelingt dadurch in jedem Tab, Browser und auf jedem Gerät.
- **Waisen werden einmalig aufgelöst.** Je Teilnahme mit mehreren laufenden
  Sitzungen bleibt die jüngste (nach `erstellt_am`, bei Gleichstand höchste pk)
  `laufend` und fortsetzbar, alle älteren werden `abgebrochen`. Hier bezeichnet
  `abgebrochen` ausnahmsweise passiv liegen gebliebene Altbestände.

## Erwogene Optionen

- **Eine laufende Sitzung beim Neustart automatisch beenden** — verworfen. Es
  verwirft die Arbeit der Teilnehmenden ohne Rückfrage und erfindet einen
  Abbruch, den niemand ausgelöst hat.
- **Den Browser-Zeiger behalten und nur aufräumen** — verworfen. Ein
  Gerätewechsel verlöre weiterhin den Zugang zur eigenen Sitzung, obwohl die
  Budget-Uhr längst an der Sitzung persistiert ist (ADR-0042).
- **Ein eigener Status wie `verlassen` für die Waisen** — verworfen. Künftig
  erzeugte ihn nichts mehr; ein Begriff nur für Altbestand lohnt nicht.
- **Den Constraint nur für Erhebungen** — verworfen. Gerade im Training
  entstanden die Waisen.

## Folgen

- Laufende Sitzungen in verschiedenen Trainings bleiben gleichzeitig erlaubt:
  Jedes Training ist eine eigene Teilnahme.
- Eine laufende Sitzung endet nur durch Abschließen, Scheitern oder einen
  ausdrücklichen Abbruch; einen Timeout gibt es nicht.
- Der Abschrift-Import bleibt unverändert: Die Quelle hat höchstens eine
  laufende Sitzung, die Kopie hält den Constraint ebenfalls.

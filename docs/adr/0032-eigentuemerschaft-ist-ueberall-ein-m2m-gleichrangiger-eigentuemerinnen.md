---
status: accepted
---

# Eigentümerschaft ist überall ein M2M gleichrangiger Eigentümerinnen

Das M2M gleichrangiger Eigentümerinnen aus ADR-0022 gilt auch für Training und
Erhebung. Damit tragen Vignetten- und Fragebogen-Item-Historien ebenso wie
Training und Erhebung einen Eigentümer-Kreis; Eigentümerschaft bleibt je Objekt
uniform und alles-oder-nichts.

## Die Erhebung teilt ihren Bestand

Eine Vignette oder ein Fragebogen-Item lässt sich in eine Erhebung einbinden,
wenn sich ihr Eigentümer-Kreis mit dem der Erhebung schneidet. So kann jede
Ko-Forschende die gemeinsame Erhebung verantworten. Sie sieht über deren
Detailansicht und Export auch Vignetten- und Item-Inhalte, an denen sie nicht
Ko-Autorin ist. Das ist bewusst akzeptiert: Die in ADR-0015 festgelegte
Privatheit regelt den Zugriff auf den Bestand, nicht die Unsichtbarkeit jedes
Inhalts in einer gemeinsam verantworteten Erhebung.

## Verantwortlichkeit bleibt beweglich

Jedes Training und jede nicht archivierte Erhebung hat mindestens eine
Eigentümerin.
Archivierte Erhebungen dürfen eigentümerlos werden; Training hat dafür bewusst
keinen Archiv-Zustand. Beim Löschen eines Kontos wird keine Nachfolgerin
automatisch eingetragen: Ein Mensch fügt sie vorher dem Kreis hinzu und entfernt
sich dann selbst.

Der Eigentümer-Kreis einer finalisierten Erhebung und eines veröffentlichten
Trainings bleibt änderbar. Eingefroren ist ihr Design, nicht die Verantwortung;
gerade laufende Bestände müssen übertragbar bleiben.

## Administration und Privatheit

Die Administration sieht alle Vignetten-, Item-, Trainings- und
Erhebungsbestände. Das führt ADR-0019 fort und ist neben dem Teilungskanal der
Erhebung die zweite Aufweichung von ADR-0015 an derselben Stelle: Privatheit
schließt andere Eigentümer-Kreise aus, nicht die Administration.

## Erwogene Optionen

- **Eine Übertragungs-Operation** — verworfen. Übertragung ist die Änderung
  des Eigentümer-Kreises: Nachfolgerin hinzufügen, sich selbst entfernen.
  Ein zweiter Weg zu demselben Zustand wäre eine zweite Wahrheit.
- **Through-Model mit ausgezeichneter Urheberin** — verworfen. Alle
  Eigentümerinnen sind gleichrangig; eine unterschiedliche Beteiligung ist
  nicht gefordert.
- **`django-guardian`** — verworfen. Die Eigentümerschaft ist kein
  Rechte-Gitter, sondern uniform und alles-oder-nichts je Objekt.

## Folgen

- ADR-0022 ist für Training und Erhebung fortgeführt: Auch sie gehören einem
  Kreis gleichrangiger Eigentümerinnen.
- ADR-0019 ist fortgeführt: Die Sichtbarkeitsregel bleibt am QuerySet, nun für
  M2M-Eigentümer-Kreise aller fachlichen Bestände.
- ADR-0015 ist zweifach nachgeführt: Die gemeinsame Erhebung teilt ihren
  Inhalt mit ihren Ko-Forschenden, und die Administration sieht alle Bestände.

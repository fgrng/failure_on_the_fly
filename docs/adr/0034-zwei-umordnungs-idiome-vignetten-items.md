---
status: accepted
---

# Zwei Umordnungs-Idiome nebeneinander: Positions-Select für Vignetten, Hoch/Runter für Items

Die Forschenden-UI der Erhebung ordnet zwei Zuordnungslisten und tut das
**bewusst auf zwei verschiedene Arten**:

- **Vignetten** ordnen über ein **Positions-Select mit Sammel-Speichern**
  (`_feste_reihenfolge_setzen`, `konfiguration_speichern` in
  `erhebungen/views.py`). Die Reihenfolge wird als Ganzes gesetzt.
- **Fragebogen-Items** ordnen über **Hoch/Runter-Knöpfe** je Zeile
  (`item_hoch` / `item_runter` → `_item_verschieben`), die je einen
  Nachbartausch am selben Andockpunkt vornehmen.

Das ist keine Unfertigkeit, sondern folgt aus einem Unterschied im Modell.

## Begründung

**Vignetten haben neben der festen Reihenfolge die Option
»randomisierte Reihenfolge«** (`Erhebung.Randomisierung`). Die Reihenfolge
ist nur *ein* Zustand des Randomisierungsfeldes; sie wird gemeinsam mit der
Randomisierungsregel im selben Formular gespeichert. Ein Positions-Select,
das im festen Modus erscheint und beim Umschalten auf `zufällig` verschwindet,
bildet genau diese Kopplung ab — die Reihenfolge gehört zur
Konfigurationsentscheidung, nicht zur einzelnen Zeile.

**Fragebogen-Items kennen keine Randomisierung.** Ihre Reihenfolge je
Andockpunkt ist immer fest und lokal (ADR-0008: zwei Andockpunkte, Reihenfolge
je Andockpunkt eindeutig). Für eine reine, immer-feste Ordnung ist die
Zeilen-Interaktion Hoch/Runter das direktere Mittel: keine globale
Formularrunde, kein Umschaltzustand, jede Bewegung ist ein lokaler
Nachbartausch. Dies wurde am Prototyp #98 entschieden (Variante A) und ist
die **bevorzugte Variante**, wenn keine Randomisierungsoption dazwischensteht.

## Erwogene Optionen

- **Beide Listen per Positions-Select** — verworfen für Items. Es würde den
  nicht vorhandenen Randomisierungszustand mitschleppen und eine
  Sammel-Speichern-Runde erzwingen, wo ein Nachbartausch genügt.
- **Beide Listen per Hoch/Runter** — verworfen für Vignetten. Hoch/Runter
  hat keinen Ort für die Randomisierungsregel; die Reihenfolge würde von der
  Regel entkoppelt, mit der sie zusammen eingefroren wird.

## Folgen

- Die zwei Idiome stehen dauerhaft nebeneinander. Das ist **gewollt** und
  darf nicht in eine Richtung vereinheitlicht werden, ohne den Unterschied
  aufzulösen, aus dem es entsteht: Vignetten tragen eine Randomisierungsregel,
  Items nicht.
- Kommt für Items je eine Randomisierung dazu, ist dieser ADR neu zu bewerten;
  dann würde das Vignetten-Idiom passen.

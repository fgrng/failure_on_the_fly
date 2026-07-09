---
status: proposed
---

# Das Fragebogen-Item ist die atomare Einheit; „Fragebogen" ist kein Objekt

Fragebögen werden nicht als Container modelliert. Die echte, wiederverwendbare und versionierte Einheit ist das **Fragebogen-Item**. Es wird über eine Zuordnung an eine Erhebung gebunden, die **Andockpunkt** und Reihenfolge trägt; diese Zuordnung gehört der Erhebung, nicht dem Item. Ein „Fragebogen" ist damit lediglich der informelle Sammelbegriff für die Items einer Erhebung samt ihren Andockpunkten.

Es gibt genau **zwei Andockpunkte**: *nach jeder Vignettensitzung* oder *am Ende nach allen Vignettensitzungen*. Item-Typen sind vorerst nur **Freitext** und eine **sechsstufige Likert-Skala** („Stimme voll zu" … „Stimme gar nicht zu") — also ohne neutrale Mitte, mit erzwungener Tendenz.

## Consequences

- Der „Fragebogen-Editor" aus der Vision pflegt die Item-Bibliothek und deren Zuordnung zu Erhebungen, kein Fragebogen-Objekt.
- Items sind versionierte Artefakte (ADR-0003): Der Wortlaut eines einmal eingesetzten Items kann nicht nachträglich mutieren.
- Weitere Item-Typen (Single/Multiple Choice, Zahleneingabe) werden erst gebaut, wenn sie gebraucht werden.
- Die sechsstufige Skala ohne Mitte ist eine methodische Festlegung, keine UI-Frage. Sie zu ändern, entwertet bereits erhobene Daten.

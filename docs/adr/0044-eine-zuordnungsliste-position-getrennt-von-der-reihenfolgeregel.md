---
status: accepted
---

# Eine Zuordnungsliste für Vignetten und Items; die Position ist von der Reihenfolgeregel getrennt

Löst ADR-0034 ab.

Vignetten und Fragebogen-Items einer Erhebung werden **auf dieselbe Weise**
zugeordnet und geordnet: je Bereich eine Liste (`zuordnungsliste.html`), darüber
eine Einfügezeile (Fassung und Stelle), je Zeile eine Icon-Leiste mit Hoch,
Runter, Entfernen und bei Items Umhängen. Umsortieren geht zusätzlich durch
Ziehen am Griff. Jede Änderung wird sofort gespeichert. Entschieden am
Prototyp #291 (Variante B).

**Jede Vignettenbindung trägt immer eine Position** (`Erhebungsvignette.position`
ist Pflicht und je Erhebung eindeutig). Ob diese Position für die Teilnahme
gilt, entscheidet allein `Erhebung.randomisierung`: Bei `fest` ist die Liste die
Reihenfolge, bei `zufällig` wird je Teilnahme gemischt, die Positionen bleiben
aber gespeichert. Das Umschalten ändert nur die Regel.

## Begründung

ADR-0034 hielt zwei Idiome fest, weil die Reihenfolge der Vignetten an die
Randomisierungsregel gekoppelt war: Bei `zufällig` durfte eine Bindung keine
Position tragen (Modellprüfung und SQLite-Trigger), beim Wechsel zu `fest`
wurden Positionen neu nach Aufnahme vergeben. Deshalb musste die Reihenfolge
zusammen mit der Regel in einem Formular gespeichert werden.

Diese Kopplung hatte eine sichtbare Folge: Wer auf `zufällig` und zurück
schaltete, verlor seine feste Reihenfolge. Trennt man Position und Regel, fällt
der Grund für zwei Idiome weg. Die Vignettenliste verhält sich dann wie die
Itemliste; die Regel ist ein Schalter über der Liste, der Nummern, Positionswahl
und Verschieben nur ausblendet.

## Erwogene Optionen

- **Positionen bei `zufällig` weiter leeren** — verworfen, weil die
  Reihenfolge beim Zurückschalten verloren geht.
- **Position nullbar lassen, aber immer schreiben** — verworfen. Das Modell
  würde einen Zustand erlauben, den kein Weg mehr erzeugt.

## Folgen

- Migration `erhebungen/0017` trägt fehlende Positionen in Aufnahme-Reihenfolge
  nach, entfernt den Trigger `erhebungen_reihenfolgeregel_bewahren` und legt die
  Prüf-Trigger der Vignettenbindung ohne Positionsregel neu an. Sie hängt von
  `vignetten/0007` ab, weil diese die Trigger mit der alten SQL neu anlegt.
- Die Ziehung (`Erhebungsbindung.ziehung_festschreiben`) liest bei `zufällig`
  die Positionen nicht; sie mischt die Bindungen wie bisher.
- Kommt für Items eine Randomisierung dazu, passt dasselbe Muster: Positionen
  bleiben, eine Regel entscheidet.

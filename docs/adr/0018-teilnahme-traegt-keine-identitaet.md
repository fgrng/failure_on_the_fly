---
status: accepted
---

# Die Teilnahme trägt keine Identität; Bindung und Pseudonymität liegen getrennt

Die **Teilnahme** ist genau ein Objekt, so wie `CONTEXT.md` sie definiert: die Klammer, unter der alle Sitzungen einer Person in genau einem Training oder genau einer Erhebung zusammengefasst sind. Sie trägt ihre Identität und ihre Sitzungen — und sonst nichts. Weder Training noch Stichprobe, weder Nutzerkonto noch Teilnahme-Token.

Woran eine Teilnahme hängt und wer hinter ihr steht, liegt in zwei **Bindungen**, die jeweils ihrer eigenen App gehören:

- `training.Trainingsbindung` hält Training und Nutzerkonto.
- `erhebungen.Erhebungsbindung` hält Stichprobe und Teilnahme-Token.

Beide zeigen mit einer 1:1-Beziehung auf die Teilnahme.

## Pseudonymität, die kein Constraint tragen muss

ADR-0006 verlangt, dass Erhebungs-Teilnahmen strikt von jedem Nutzerkonto getrennt sind; die Vision nennt die Trennung von Kontakt- und Forschungsdaten als eigenes Ziel. Eine einzige Teilnahme-Tabelle mit vier nullbaren Spalten könnte das erfüllen — solange ein Check-Constraint hält. Sie wäre eine Tabelle, in der die verbotene Verknüpfung *ausdrückbar* ist und nur verboten wird.

Mit zwei Bindungstabellen ist sie **nicht ausdrückbar**: Keine Tabelle hat eine Spalte für ein Nutzerkonto und eine für ein Token. Der Schutz sitzt im Schema, nicht in einer Prüfung. Das ist dieselbe Bewegung, mit der ADR-0016 den Probelauf schreibfrei macht, statt ihm ein `dry_run`-Flag zu geben: Eine Zusage, die an einer Prüfung hängt, ist schwächer als eine, die das Schema gar nicht formulieren kann.

Nebenwirkung, die den Ausschlag mitgibt: Alle Fremdschlüssel zeigen nun von `training` und `erhebungen` nach `sitzungen`. `sitzungen` importiert keine seiner beiden Aufrufer-Apps, und der Import-Zyklus, den eine XOR-Teilnahme erzeugt hätte, entsteht nicht.

## Considered Options

- **Eine Teilnahme-Tabelle mit `training`, `stichprobe`, `nutzerkonto`, `token` als nullbaren Spalten und zwei korrelierten Check-Constraints** — verworfen. Die Pseudonymität hinge an den Constraints, und `sitzungen` müsste `training` und `erhebungen` kennen.
- **Zwei Teilnahme-Modelle, je eines in `training` und `erhebungen`** — verworfen. Die Pseudonymität wäre strukturell, aber der Begriff Teilnahme aus dem Glossar hätte kein Gegenstück im Code; die Sitzung bräuchte zwei nullbare Fremdschlüssel, und `datenspuren` zwei Pfade durch ein und dieselbe Aufzeichnung.

## Consequences

- `datenspuren` liest je Datenspur eine Teilnahme und joint genau eine Bindung. Welche, sagt ihm die Erhebung, aus der es exportiert; Trainings werden nicht exportiert.
- Eine Teilnahme ohne Bindung ist technisch möglich und fachlich unsinnig. Sie entsteht nur, wenn Teilnahme und Bindung nicht in derselben Transaktion angelegt werden. Das ist eine Regel des Codes, nicht des Schemas.
- Das Löschen der Forschungsdaten einer Erhebung und das Löschen der Verbindung zu ihren Teilnahme-Tokens sind zwei verschiedene, einzeln ausführbare Vorgänge.
- Dieser ADR schärft ADR-0006 und ersetzt keine seiner Aussagen.

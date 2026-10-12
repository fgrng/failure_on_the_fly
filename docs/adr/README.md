# Architecture Decision Records

Ein ADR hält eine Entscheidung fest, die sich im Code nicht von selbst erklärt,
samt ihrer Gründe. Das Glossar (`GLOSSARY.md`) sagt, *was* ein Begriff meint;
das ADR sagt, *warum* es so ist.

Diese Datei regelt die Form. Sie geht den allgemeinen Vorgaben in
`.claude/skills/domain-modeling/ADR-FORMAT.md` vor, wo beide sich
widersprechen.

## Der Entscheidungstext ist unveränderlich

Ein angenommenes ADR wird nicht umgeschrieben. Was sich danach ändert, läuft
über den Status im Frontmatter, einen Nachführungsblock und neue ADRs. Die
Git-Historie ersetzt das nicht: Wer einem ADR-Verweis aus einem Codekommentar
folgt, muss die Begründung finden, die diesen Code geformt hat, nicht deren
heutige Fassung.

Die einmalige Konsolidierung aus #235 hat ältere ADRs zusammengeführt und neu
eingestuft. Sie war die Ausnahme, mit der diese Regel beginnt.

## Frontmatter

```yaml
---
status: accepted | amended | superseded | deprecated
amended-by: [ADR-0037, "#168"]   # nur bei amended
superseded-by: ADR-0039          # nur bei superseded
deprecated-by: "#123"            # optional bei deprecated
---
```

- **`accepted`**: Die Entscheidung gilt wie geschrieben.
- **`amended`**: Die Entscheidung gilt, aber ein späteres ADR oder Issue
  verengt, erweitert oder korrigiert eine Tatsache darin. Der Text bleibt; ein
  einziger Nachführungsblock unter dem Titel trägt die Differenz.
- **`superseded`**: Die Entscheidung gilt nicht mehr; ein anderes ADR ersetzt
  sie. Der Text bleibt als Begründung ihrer Zeit, Nachführungsblöcke fallen
  weg, das Frontmatter trägt die Warnung.
- **`deprecated`**: Die Entscheidung ist ohne Nachfolger zurückgenommen.
  `deprecated-by` darf auf das Issue zeigen, das sie zurücknahm.

Kein Datum, keine Beteiligten, keine Liste der ADRs, die auf dieses verweisen.
Die Nummer im Dateinamen ordnet die ADRs zeitlich.

## Issue oder ADR?

Eine Nachführung darf auf ein Issue statt auf ein ADR zeigen, wenn nur eine
*Tatsache innerhalb der Regel* wechselt: eine Zahl, ein Name, eine Farbe, ein
Anbieter. Ändert sich die *Regel selbst*, braucht es ein neues ADR. Die Probe:
*Bräche ein Test, wenn ich weiter dem alten Wortlaut folgte?* Dann ein ADR.

## Grundgerüst

Jede ADR-Datei hat dieselbe Form, mit deutschen Abschnittsüberschriften:

1. Frontmatter.
2. `# Titel`: ein Satz, der die Entscheidung ausspricht.
3. Optional **genau ein** Nachführungsblock direkt unter dem Titel, als
   Blockquote in der Form `> **Nachgeführt durch ADR-0037, #168:** …`. Nie ein
   Blockquote mitten im Text, nie ein Abschnitt „Nachtrag“.
4. Der Entscheidungstext, mit freien Zwischenüberschriften.
5. Optional `## Erwogene Optionen`.
6. `## Folgen`.

Englische Überschriften (`Considered Options`, `Consequences`) und
`superseded by ADR-NNNN` im Statusfeld werden nicht verwendet.

## Nummernvergabe

Die nächste freie Nummer wird beim Merge vergeben, nicht beim Anlegen des
Branches. Zwei Branches, die beide die nächste Nummer beanspruchen,
kollidieren. Bis zum Merge heißt das ADR nach seinem Arbeitstitel.

## Wo ADR-Verweise stehen dürfen

- **Glossar (`GLOSSARY.md`)**: am Begriff, der ohne die Entscheidung
  unvollständig wäre, als `(ADR-0036)`. Nie als Volltextkopie des ADRs.
- **Code und Templates**: nur dort, wo die Umsetzung sonst wie ein Fehler
  aussähe.
- **Tests**: frei. Ein Test, der eine ADR-Regel bewacht, nennt sie.
- **README**: nie. Ihre Leser:innen sind Nutzer:innen und Betreiber:innen.
- **ADRs selbst**: Vorwärtsverweise auf andere ADRs sind in Ordnung, eine
  Rückwärtsliste nicht.

Glossar und README verweisen nie auf ein `superseded`- oder
`deprecated`-ADR. Sie folgen `superseded-by` und zeigen auf den Nachfolger.

Offene Fragen stehen nicht in einer Datei, sondern als Issues im Tracker.

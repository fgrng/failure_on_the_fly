# Architecture Decision Records

Diese Datei regelt Form und Pflege der ADRs. Wo sie
`.claude/skills/domain-modeling/ADR-FORMAT.md` widerspricht, gilt sie.

Ein angenommenes ADR ist **eingefroren**: Sein Entscheidungstext bleibt so,
wie er die damalige Umsetzung begründet hat. Wer einem ADR-Verweis aus dem
Code folgt, findet dort diese Begründung. Was sich später ändert, läuft über
den Status, einen Nachführungsblock und neue ADRs.

## Eine Entscheidung ändert sich

1. **Nachführen oder ersetzen?** Wechselt nur eine *Tatsache innerhalb der
   Regel* (eine Zahl, ein Name, eine Farbe, ein Anbieter), wird das alte ADR
   **nachgeführt**, und der Anlass darf ein Issue sein. Wechselt die *Regel
   selbst*, braucht es ein neues ADR. Die Probe: Bräche ein Test, wenn ich
   weiter dem alten Wortlaut folgte? Dann ein neues ADR. Gilt die alte
   Entscheidung danach im Kern nicht mehr, **ersetzt** das neue ADR sie.
2. **Das alte ADR markieren.**
   - Nachgeführt: `status: amended`, der Anlass in `amended-by`, und die
     Differenz im Nachführungsblock unter dem Titel. Gibt es schon einen
     Block, wächst er um einen Absatz; das ADR trägt immer genau einen.
   - Ersetzt: `status: superseded` und `superseded-by`. Sein
     Nachführungsblock fällt weg, der Entscheidungstext bleibt.
3. **Verweise umleiten.** Glossar, Code, Templates und Tests, die auf ein
   ersetztes ADR zeigen, zeigen danach auf den Nachfolger. Der Text anderer
   ADRs bleibt eingefroren: Ein Verweis aus einem angenommenen ADR auf ein
   inzwischen ersetztes ist ein Lesepfad in die Historie und wird nicht
   umgeschrieben. Migrationen bleiben ebenfalls unverändert (ADR-0031).

Fertig, wenn das Frontmatter des alten ADRs auf den Anlass zeigt und
`rg -g '!docs/**' 'ADR-NNNN'` für ein ersetztes ADR keinen Treffer mehr
liefert.

## Frontmatter

Das Frontmatter trägt genau diese Felder:

```yaml
---
status: accepted | amended | superseded | deprecated
amended-by: [ADR-0037, "#168"]   # nur bei amended
superseded-by: ADR-0039          # nur bei superseded
deprecated-by: "#123"            # optional bei deprecated
---
```

- **`accepted`**: Die Entscheidung gilt wie geschrieben.
- **`amended`**: Die Entscheidung gilt; ein späteres ADR oder Issue verengt,
  erweitert oder korrigiert eine Tatsache darin.
- **`superseded`**: Ein anderes ADR ersetzt die Entscheidung. Der Text bleibt
  als Begründung seiner Zeit.
- **`deprecated`**: Die Entscheidung ist ohne Nachfolger zurückgenommen.

Die Nummer im Dateinamen ordnet die ADRs zeitlich; Datum und Beteiligte
stehen in der Git-Historie.

## Grundgerüst

Jede ADR-Datei hat dieselbe Form, mit deutschen Abschnittsüberschriften:

1. Frontmatter.
2. `# Titel`: ein Satz, der die Entscheidung ausspricht.
3. Optional der Nachführungsblock direkt unter dem Titel, als Blockquote:
   `> **Nachgeführt durch ADR-0037, #168:** …`. Er ist der einzige Ort für
   Nachführungen.
4. Der Entscheidungstext, mit freien Zwischenüberschriften.
5. Optional `## Erwogene Optionen`.
6. `## Folgen`.

## Nummernvergabe

Die nächste freie Nummer wird beim Merge vergeben. Bis dahin heißt das ADR
nach seinem Arbeitstitel; so kollidieren zwei Branches nicht.

## Wo ADR-Verweise stehen

- **Glossar (`GLOSSARY.md`)**: am Begriff, der ohne die Entscheidung
  unvollständig wäre, als `(ADR-0036)`.
- **Code und Templates**: dort, wo die Umsetzung sonst wie ein Fehler
  aussähe.
- **Tests**: frei. Ein Test, der eine ADR-Regel bewacht, nennt sie.
- **ADRs**: Vorwärtsverweise auf andere ADRs. Ein Sammel-ADR nennt in seinem
  ersten Absatz, welche ADRs es zusammenfasst und ersetzt.
- **README**: keine. Ihre Leser:innen sind Nutzer:innen und Betreiber:innen.

Glossar, Code und Tests zeigen auf ADRs mit `accepted` oder `amended`.

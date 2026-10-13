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

## Wegweiser

Nur ADRs mit `accepted` oder `amended`, nach Thema. Wer ein ADR anlegt oder
ersetzt, führt die Liste nach; ersetzte ADRs erscheinen hier nicht.

**Domäne und Forschungsinstrument**

- ADR-0001 Fehlermuster als einziger Oberbegriff, verortet in der Vignette
- ADR-0002 Training und Erhebung getrennt, gemeinsames Sitzungs-Rückgrat
- ADR-0004 Ein zentraler, fach-agnostischer Simulationskern, gepinnt von der Vignette
- ADR-0008 Das Fragebogen-Item ist die atomare Einheit
- ADR-0009 Die Diagnose wird erfasst, nicht bewertet
- ADR-0046 Evals prüfen die Simulation; eigener, ungepinnter Evalkatalog

**Pseudonymität und Datenschutz**

- ADR-0006 Erhebungs-Teilnahmen sind pseudonym und vom Training getrennt
- ADR-0007 Audio wird nie gespeichert; das Transkript ist nicht korrigierbar
- ADR-0026 Transkription über externen Auftragsverarbeiter mit Zero-Retention
- ADR-0045 Flüchtige Teilnahme: Gerüst in der DB, Inhalte nie
- ADR-0058 Die Teilnahme trägt keine Identität: zwei Bindungen, Abschrift als Kopie

**Eigentum, Rollen und Lebenszyklus**

- ADR-0027 Die Erhebung leiht die Statusnamen, ist aber ein einzelnes Objekt
- ADR-0037 Der Eigentümer-Kreis ist eine gemeinsame Basis in `konten`
- ADR-0039 Eigentümerschaft: Privatheit, Kreis, Sichtbarkeit am QuerySet
- ADR-0040 Lebenszyklus versionierter Artefakte, samt Kern-Sonderform
- ADR-0048 Vignettenposition getrennt von der Reihenfolgeregel

**Sitzung und Datenspur**

- ADR-0005 Denkspur pro Antwort; Teilnehmende sehen sie nie
- ADR-0014 Der Probelauf ist eine schreibfreie Funktion über einem Tripel
- ADR-0029 Die Datenspur wird long-relational, selbsttragend, pro Erhebung exportiert
- ADR-0049 Einsicht folgt dem Anlass, nie der Vignette
- ADR-0057 Das Gesprächsbudget gehört der Vignette, ist unsichtbar, Uhr an der Sitzung
- ADR-0061 Höchstens eine laufende Sitzung je Teilnahme; der Gesprächsschritt ist atomar

**Simulation, Vorlagen und Anbieter**

- ADR-0020 Die Vorlagen des Kerns sind `string.Template`
- ADR-0052 Wem die Nachrichtenrollen gehören
- ADR-0054 Fester Vertrag zwischen Vignette und Vorlagen, samt Positionsmarker
- ADR-0056 Anbieter und Modell-Konfiguration: append-only, ein Zeiger je Verwendung

**Architektur und Betrieb**

- ADR-0031 Historische Migrationen sind unveränderlich
- ADR-0041 Der Ablauf-Schritt ist ein Objekt, der Itemblock bekommt eine Tabelle
- ADR-0044 Markdown mit zwei Profilen, Quelle bleibt roh
- ADR-0055 Apps entlang der Domänenobjekte, azyklischer Importgraph, drei Nähte
- ADR-0059 Nebenläufigkeit: SQLite, ein Thread je wartender Anfrage, ein Prozess für Evalläufe

**UI**

- ADR-0060 CD-konformes Tool-UI, semantische Tokens, die Sitzung wächst auf einer Seite

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

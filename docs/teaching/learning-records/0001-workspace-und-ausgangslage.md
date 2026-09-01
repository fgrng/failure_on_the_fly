# 0001 — Workspace eingerichtet, Ausgangslage bestimmt

**Datum:** 2026-09-01
**Status:** aktiv

## Kontext

Der Lernende hatte bereits sechs selbst verfasste Wissenslektionen in
`docs/teaching/0X-*.md` plus Glossar und Quellenverzeichnis. Das Wissen
war also gelesen und geordnet — aber ausschliesslich rezeptiv. Es gab
keine Abrufpraxis, keine Anwendung auf eigene Artefakte und keine
festgehaltene Mission.

## Entscheidung

`docs/teaching/` wird zum Lehr-Workspace ausgebaut. Die vorhandenen
Markdown-Dateien bleiben als Wissensschicht (Selbststudium); dazu kommen
HTML-Lektionen als Skill-Schicht mit Abruf, Anwendung und sofortigem
Feedback.

## Einschätzung der Ausgangslage

- **Wissen:** hoch für Lektionen 1–3 und 5–6, unbestätigt für Lektion 4
  (Fine-Tuning).
- **Skill:** ungeprüft. Ob der Lernende die Konstrukte an einem echten
  Transkript unterscheiden kann, weiss er selbst noch nicht.
- **Zone of Proximal Development:** nicht mehr Theorie, sondern
  Anwendung der bekannten Begriffe auf `simulation/standardkern.py`.

## Erste Lektion

`lessons/0001-drei-anforderungen-am-eigenen-kern.html`: Abrufquiz zu den
drei gekoppelten Anforderungen, dann Zuordnung der Sätze des eigenen
System-Prompts, dann Schreibaufgabe (Named Ignorance für Lukas).

## Zentrale Einsicht dieser Lektion

Der Simulationskern zieht die *Boundary of Competence* einseitig: Er sagt
„Du kennst den fachlich richtigen Lösungsweg nicht“, aber nirgends, was
die simulierte Schüler:in stattdessen sicher kann. In diese Leerstelle
fällt das Modell auf sein eigenes — also Experten- — Wissen zurück.
Named Ignorance braucht beide Blöcke.

Das ist ein Kandidat für eine echte Änderung an `standardkern.py` oder
für eine Ergänzung des Autor:innen-Leitfadens zu Simulationshinweisen.

## Offen

- Zitationen in `quellen.md` sind vor der CERME-Einreichung gegen die
  Primärquellen zu verifizieren.
- Community-Anbindung (über CERME hinaus) noch nicht geklärt.

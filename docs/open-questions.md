# Offene Fragen

Fragen, die in den Modellierungssitzungen aufgetaucht, aber **nicht entschieden** worden sind. Sobald eine Frage beantwortet ist: hier streichen und — falls die Entscheidung schwer umkehrbar ist — als ADR in `docs/adr/` festhalten bzw. den betroffenen ADR-Entwurf aktualisieren.

Begriffe folgen `CONTEXT.md`.

Die Administration ist keine offene Rollenfrage mehr: Sie ist als Django-
Superuser in ADR-0033 entschieden; nur die drei Fachrollen sind Groups.

## 1. Wiederholversuche und Sitzungsobergrenze

`docs/adr/0011` lässt begrenzte Wiederholungen eines gescheiterten Gesprächsschritts zu, ohne die Grenze zu nennen. Offen: Wie viele Versuche, bevor eine Sitzung aufgibt, und was sieht die Teilnehmer:in dann? Getrennt davon verlangt `docs/adr/0012` eine **harte Obergrenze** gegen ewig offene Sitzungen — sie hat nichts mit dem Gesprächsbudget zu tun und ist noch unbeziffert.

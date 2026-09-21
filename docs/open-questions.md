# Offene Fragen

Fragen, die in den Modellierungssitzungen aufgetaucht, aber **nicht entschieden** worden sind. Sobald eine Frage beantwortet ist: hier streichen und — falls die Entscheidung schwer umkehrbar ist — als ADR in `docs/adr/` festhalten bzw. den betroffenen ADR-Entwurf aktualisieren.

Begriffe folgen `CONTEXT.md`.

Die Administration ist keine offene Rollenfrage mehr: Sie ist als Django-
Superuser in ADR-0033 entschieden; nur die drei Fachrollen sind Groups.

## 1. Wiederholversuche und Sitzungsobergrenze

`docs/adr/0011` lässt begrenzte Wiederholungen eines gescheiterten Gesprächsschritts zu, ohne die Grenze zu nennen. Offen: Wie viele Versuche, bevor eine Sitzung aufgibt, und was sieht die Teilnehmer:in dann? Getrennt davon verlangt `docs/adr/0012` eine **harte Obergrenze** gegen ewig offene Sitzungen — sie hat nichts mit dem Gesprächsbudget zu tun und ist noch unbeziffert.

## 2. Zulässige Anbieter und Modelle — beantwortet (ADR-0038)

`docs/adr/0005` schreibt fest, dass die Denkspur immer aus dem Structured Output stammt. Damit sind nur Anbieter und Modelle zulässig, die das beherrschen. Offen ist die konkrete Liste.

**Stand 2026-09-18** ([#166](https://github.com/fgrng/failure_on_the_fly/issues/166), Recherche in `docs/research/2026-09-18-zulaessige-anbieter-und-modelle.md`): Unterstützt werden **OpenRouter** und **Infomaniak**. Die Liste wird **nicht erzwungen** — bei OpenRouter hängt Structured Output am Endpunkt statt am Modell, eine Namens-Whitelist wäre Scheinsicherheit; geprüft wird stattdessen die Anbieterbindung.

**Entschieden 2026-09-21** in **ADR-0038**: zwei Anbieter, keine erzwungene Modellliste. Diese Frage ist damit geschlossen.

**Stand 2026-09-21** ([#174](https://github.com/fgrng/failure_on_the_fly/issues/174)): Die native Reasoning-Spur wird gestrichen; die frühere zweite Hälfte dieser Frage — ob Structured Output und natives Reasoning gleichzeitig möglich sind — ist damit gegenstandslos. Das einzige verbliebene Kriterium an ein Modell ist, dass es Structured Output beherrscht.

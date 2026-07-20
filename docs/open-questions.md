# Offene Fragen

Fragen, die in den Modellierungssitzungen aufgetaucht, aber **nicht entschieden** worden sind. Sobald eine Frage beantwortet ist: hier streichen und — falls die Entscheidung schwer umkehrbar ist — als ADR in `docs/adr/` festhalten bzw. den betroffenen ADR-Entwurf aktualisieren.

Begriffe folgen `CONTEXT.md`.

## 1. Übertragung der Eigentümerschaft an Vignetten und Fragebogen-Items

Folgt zwingend aus `docs/adr/0015` und ADR-0028: Weil Vignetten und Fragebogen-Items privat sind, sind sie beim Weggang einer Autor:in für niemanden erreichbar — auch nicht für laufende Erhebungen. Administrator:innen brauchen eine Übertragung der Eigentümerschaft.

Entschieden ist inzwischen in `docs/adr/0019`, fortgeführt durch ADR-0022 und ADR-0028: Die **Vignetten-** und **Fragebogen-Item-Historie** tragen die Eigentümer:innen, nicht die einzelne Fassung. Eine finale Fassung ist unveränderlich, ein Eigentümerwechsel an ihr wäre eine Mutation.

Offen bleibt der **Wechsel** selbst: Was geschieht mit dem offenen Entwurf, und wandern Trainings und Erhebungen der weggegangenen Person mit? Zu bedenken ist dabei, dass `docs/adr/0015` die Privatheit ausdrücklich als **revidierbar** bezeichnet. Fällt sie, wird aus der Eigentümerschaft eine Zugriffsregel mit mehreren Beteiligten; die Eigentümerschaft an der Historie bliebe richtig, wäre aber nicht mehr die ganze Antwort.

## 2. Wiederholversuche und Sitzungsobergrenze

`docs/adr/0011` lässt begrenzte Wiederholungen eines gescheiterten Gesprächsschritts zu, ohne die Grenze zu nennen. Offen: Wie viele Versuche, bevor eine Sitzung aufgibt, und was sieht die Teilnehmer:in dann? Getrennt davon verlangt `docs/adr/0012` eine **harte Obergrenze** gegen ewig offene Sitzungen — sie hat nichts mit dem Gesprächsbudget zu tun und ist noch unbeziffert.

## 3. Zulässige Anbieter und Modelle

`docs/adr/0005` schreibt fest, dass die Denkspur immer aus dem Structured Output stammt. Damit sind nur Anbieter und Modelle zulässig, die das beherrschen. Offen ist die konkrete Liste sowie die Frage, ob und bei welchen Anbietern Structured Output und natives Reasoning gleichzeitig möglich sind — die native Reasoning-Spur ist als optionales Feld am Gesprächsschritt vorgesehen.

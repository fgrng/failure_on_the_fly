# Offene Fragen

Fragen, die in den Modellierungssitzungen aufgetaucht, aber **nicht entschieden** worden sind. Sobald eine Frage beantwortet ist: hier streichen und — falls die Entscheidung schwer umkehrbar ist — als ADR in `docs/adr/` festhalten bzw. den betroffenen ADR-Entwurf aktualisieren.

Begriffe folgen `CONTEXT.md`.

## 1. Übertragung der Eigentümerschaft an Vignetten

Folgt zwingend aus `docs/adr/0015`: Weil Vignetten privat sind, sind sie beim Weggang einer Autor:in für niemanden erreichbar — auch nicht für laufende Erhebungen. Administrator:innen brauchen eine Übertragung der Eigentümerschaft.

Entschieden ist inzwischen in `docs/adr/0019`: Die **Vignettenhistorie** trägt den Eigentümer, nicht die einzelne Fassung. Eine finale Fassung ist unveränderlich, ein Eigentümerwechsel an ihr wäre eine Mutation.

Offen bleibt der **Wechsel** selbst: Was geschieht mit dem offenen Entwurf, und wandern Trainings und Erhebungen der weggegangenen Person mit? Zu bedenken ist dabei, dass `docs/adr/0015` die Privatheit ausdrücklich als **revidierbar** bezeichnet. Fällt sie, wird aus der Eigentümerschaft eine Zugriffsregel mit mehreren Beteiligten; der Fremdschlüssel an der Historie bliebe richtig, wäre aber nicht mehr die ganze Antwort.

## 2. Erhebungs-Status und Teilnahmesteuerung

Aus der Vision übernommen, aber nie durchgesprochen:

- **Status einer Erhebung** (angelegt, laufend, abgeschlossen): Wer setzt ihn, und was ändert er? `docs/adr/0013` knüpft das Pinning der Modell-Konfiguration an die **Aktivierung** einer Erhebung — dieser Übergang braucht also eine Definition. Insbesondere: Darf eine laufende Erhebung noch verändert werden? Bei Trainings dürfen Vignetten im laufenden Betrieb ausgetauscht werden — bei Erhebungen wäre das ein Reproduzierbarkeitsbruch.
- **Teilnahmefenster und -limits**: Zeitraum, in dem ein Teilnahme-Link gültig ist; maximale Zahl an Teilnahmen je Stichprobe.
- **Abgebrochene Teilnahmen**: Was passiert mit einer Teilnahme, die nach zwei von drei Vignettensitzungen endet? Landet sie im Export, und wenn ja, wie gekennzeichnet?

## 3. Randomisierung

Erwähnt, aber nie präzisiert. Randomisiert wird vermutlich die **Reihenfolge der Vignetten** innerhalb einer Teilnahme. Offen ist, ob es weitere Randomisierungsachsen gibt, ob die gezogene Reihenfolge Teil der Datenspur ist (sie sollte es sein) und ob Randomisierung pro Erhebung an- und abschaltbar ist.

## 4. Export-Formate und Granularität

Die Vision nennt CSV und JSON. Offen ist, welche Tabellen bzw. Objekte der Export ausgibt und auf welcher Ebene: eine Zeile je Sitzung, je Teilnahme oder je Gesprächsschritt? Wie werden Transkript und Denkspur — beide mehrzeilig — in ein tabellarisches Format überführt? Werden die verwendeten Fassungen von Vignette, Simulationskern und Modell-Konfiguration als IDs oder als eingebetteter Inhalt exportiert? Und wie erscheinen die **Fehlversuche** aus `docs/adr/0011`, die neben dem Transkript stehen?

## 5. Wiederholversuche und Sitzungsobergrenze

`docs/adr/0011` lässt begrenzte Wiederholungen eines gescheiterten Gesprächsschritts zu, ohne die Grenze zu nennen. Offen: Wie viele Versuche, bevor eine Sitzung aufgibt, und was sieht die Teilnehmer:in dann? Getrennt davon verlangt `docs/adr/0012` eine **harte Obergrenze** gegen ewig offene Sitzungen — sie hat nichts mit dem Gesprächsbudget zu tun und ist noch unbeziffert.

## 6. Zulässige Anbieter und Modelle

`docs/adr/0005` schreibt fest, dass die Denkspur immer aus dem Structured Output stammt. Damit sind nur Anbieter und Modelle zulässig, die das beherrschen. Offen ist die konkrete Liste sowie die Frage, ob und bei welchen Anbietern Structured Output und natives Reasoning gleichzeitig möglich sind — die native Reasoning-Spur ist als optionales Feld am Gesprächsschritt vorgesehen.

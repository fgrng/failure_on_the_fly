---
status: amended
amended-by: ["#27"]
---

# Der Gesprächsschritt ist atomar; Fehlversuche stehen neben dem Transkript

> **Nachgeführt durch #27:** Die begrenzte Wiederholung ist beziffert:
> `MAX_VERSUCHE = 3` in `simulation`. Scheitert der dritte Versuch, ist der
> Gesprächsschritt endgültig gescheitert. Die Folge „noch offen" unten ist
> damit entschieden.

Ein **Gesprächsschritt** existiert nur, wenn Eingabe, Denkspur und sichtbare Äußerung alle vorliegen. Liefert das Modell kein verwertbares Ergebnis — Formatbruch, Anbieterfehler, Filter —, wird begrenzt wiederholt. Scheitert es endgültig, sieht die Teilnehmer:in einen Fehler; das Transkript bleibt unberührt und ein Schritt-Budget unangetastet.

Ein Gesprächsschritt **ohne Denkspur ist unzulässig**. Die Denkspur ist laut ADR-0005 der Kern des Instruments: Eine Sitzung mit Lücken darin kann die Frage nach der Konsistenz des Fehlermusters nicht mehr beantworten, und beim Auswerten fiele es niemandem auf.

## Fehlversuche gehören in die Datenspur, nicht in das Transkript

Jede verworfene Antwort wird samt ihrem Grund als **Fehlversuch** protokolliert — sichtbar für Forschende, unsichtbar für Teilnehmende. Wenn das Modell in Zug sieben zweimal aus der Rolle fällt und beim dritten Versuch eine brauchbare Antwort liefert, ist das ein Befund über die Simulation, und genau für solche Befunde wird dieses Instrument gebaut.

Das **Transkript** nimmt sie nicht auf. Es ist die Aufzeichnung der diagnostischen Gesprächsführung der angehenden Lehrperson (ADR-0007); was verworfen wurde, hat sie nie gesehen und nie beantwortet, und es war nie Teil des Verlaufs.

## Folgen

- Neben dem Transkript existiert eine zweite Schreibbahn. Beide gehören zur Datenspur, nur eine zum Gespräch.
- Wie viele Wiederholungen zulässig sind, bevor eine Sitzung aufgibt, ist noch offen.
- Fehlversuche verbrauchen Zeit. Bei einem Zeitbudget wird sie nicht angerechnet (ADR-0012).

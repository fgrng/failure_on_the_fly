---
status: accepted
---

# Training und Erhebung sind getrennte Konzepte auf gemeinsamem Sitzungs-Rückgrat

Training und Erhebung bündeln beide eine Auswahl von Vignetten und erzeugen beide Sitzungen. Naheliegend wäre ein einziges Objekt mit einem `modus`-Attribut. Wir modellieren sie trotzdem als **zwei eigenständige Konzepte**, weil sich fast alle Regeln unterscheiden: freie vs. gesteuerte Vignetten-Auswahl, beliebig oft wiederholbar vs. einmaliger Durchlauf, keine vs. Pflicht-Fragebogen-Items, Kontozugang vs. pseudonymer Teilnahme-Link, Einsicht in eigene Transkripte vs. keine. Ein Flag, das die Hälfte der Felder und Regeln an- und abschaltet, wäre ein Modellierungsfehler; zudem passt das Wort „Erhebung" semantisch nicht auf ein Ausbildungs-Training.

Gemeinsam ist beiden das **Rückgrat der Datenspur**: Teilnahme → Sitzung. Dieses wird geteilt, der Behälter nicht.

## Considered Options

- **Ein Objekt mit Modus-Flag** — verworfen: die Unterschiede sind strukturell, nicht kosmetisch.
- **Vollständig getrennte Modelle inkl. eigener Sitzungs-Typen** — verworfen: Forschende und Ausbilder:innen wollen dieselbe Auswertungseinheit.

## Consequences

- Eine gewisse Duplikation (beide brauchen „Menge finaler Vignetten", Teilnahme, Statusverwaltung) wird bewusst in Kauf genommen.
- Ob Training und Erhebung technisch einen gemeinsamen Elterntyp erhalten, bleibt eine Implementierungsfrage. Begrifflich bleiben es zwei Wörter.

---
status: accepted
---

# Evalläufe laufen in einem eigenen Hintergrundprozess, eine Warteschlange in der Datenbank

Bis hierher kam das Projekt ohne Hintergrundverarbeitung aus: Ein Gesprächsschritt wartet synchron auf das Sprachmodell, der Export ist ein synchroner Download (#104). Ein Evallauf (ADR-0046) sprengt das. Bei einer Handvoll Evals mit je zwei Evalinputs, *k* = 3 und drei Inputschritten kommen gut zweihundert Modellaufrufe zusammen — nacheinander eher zwanzig bis vierzig Minuten.

Evalläufe werden deshalb von einem **eigenen Prozess** abgearbeitet: einem Management-Command, das als zweiter supervisord-Dienst neben gunicorn läuft und offene Evalläufe aus der Datenbank holt. Der Status des Evallaufs ist die Warteschlange; eine eigene Queue-Infrastruktur gibt es nicht. Der Prozess arbeitet **einen Evallauf nach dem anderen** ab, instanzweit — das ist zugleich die Kostenbremse und hält die Anbieterlimits ein. Je Vignettenfassung wartet oder läuft höchstens einer.

Bricht der Prozess mitten in einem Lauf ab, bleibt der Evallauf **abgebrochen** stehen; was fertig war, bleibt sichtbar. Fortgesetzt wird nicht, er wird neu ausgelöst.

## Considered Options

- **Synchron in der Anfrage** — unmöglich; das Worker-Timeout liegt bei 180 s.
- **Der Browser treibt den Lauf**, Evalgespräch für Evalgespräch per HTMX — verworfen. Jede Anfrage belegte einen der drei gunicorn-Worker und konkurrierte mit laufenden Erhebungen; ein geschlossener Tab bräche den Lauf ab.
- **Nur als Management-Command für Administrator:innen** — verworfen. Der Evallauf ist ein Werkzeug der Autor:in.
- **Eine Worker-Bibliothek mit eigenem Broker** — verworfen. Ein Dienst, eine Abhängigkeit und ein Betriebsrisiko mehr für einen einzigen Anwendungsfall, dessen Durchsatz ein Lauf nach dem anderen ist.

## Consequences

- Die Instanz betreibt künftig zwei Prozesse; `docs/DEPLOYMENT.md` beschreibt beide.
- Der Hintergrundprozess schreibt in dieselbe SQLite-Datei wie gunicorn. Bei einem Lauf nach dem anderen ist das eine zusätzliche Schreiberin, keine Last.
- Er ist das Fundament für eine spätere Regressionsreihe über viele Vignetten.

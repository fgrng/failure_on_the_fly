# Prototyp #296: Evallauf-Ansicht

Throwaway auf `prototype/296-evallauf`, außerhalb von main.

## Festgehaltene Entscheidung

Die Autor:in hat die ursprüngliche Variante C gewählt: Evalinputs und Quoten
links, Gespräch und Urteile rechts. Der Abschnitt „Vignettenkontext“ entfällt.
Die Spalten und Steuerelemente folgen dem bestehenden Evalkatalog-Editor und den
Vignettenformularen: voller Inhaltsbereich, schmale Auswahl links,
gekennzeichneter gewählter Input, Formularfeld für die Wiederholung. Auf
schmalen Inhaltsbereichen stehen die Spalten untereinander (erst unter 560 px
Hauptbereichsbreite). Die ursprünglichen Ergebnisboxen bleiben erhalten.

Der Vorschau-Runner lädt Templates bei jeder Anfrage neu: Nach Änderungen genügt
ein Neuladen im Browser, auch wenn neue Stylesheets hinzukommen.

Die große Box „Evallauf · Fertig · nicht bestanden“ ist zu prominent. Die zweite
Runde prüft daher drei unterschiedliche Orte für den Laufstatus, bei
unverändertem Zweispaltenlayout:

- A: Knappe Kopfzeile über den Ergebnissen, Aktion rechts, Laufangaben darunter
  eingeklappt.
- B: Laufzusammenfassung in der linken Auswahlspalte, vor den Evalinputs.
- C: Abgeschlossene Läufe als Fußzeile unter den Ergebnissen. Noch nicht
  gestartete, wartende und laufende Läufe stehen oben.

Gewählt ist Variante C: Der Status eines abgeschlossenen Evallaufs steht als
Fußnote unter den Ergebnissen. „Erneut prüfen“ steht dort als sekundäre Aktion;
die Angaben zum Lauf bleiben eingeklappt. Ohne Lauf sowie bei wartenden und
laufenden Läufen steht der Status oben. Die Autor:in hat diese Variante nach
Korrektur der Spaltenansicht bestätigt. C ist die Standardansicht des Prototyps.

Damit sind Zweispaltenansicht, Wegfall des Vignettenkontexts und Platzierung des
Laufstatus entschieden. Die tatsächliche Aktualisierung laufender Läufe (Polling
oder manuelles Neu laden) bleibt für die Umsetzung zu klären. Die ursprünglichen
drei Layoutvarianten liegen im Vorgängercommit `a92c84a`.

## Start und Bedienung

```sh
uv run python -m vignetten.prototype_296
```

Adresse: <http://127.0.0.1:8296/vignetten/296/?variant=C>

Die schwebende Leiste und Pfeiltasten wechseln `?variant=A|B|C`. Alle Varianten
haben dieselben Beispieldaten. Die Auswahl links zeigt das Gespräch rechts, mit
Wiederholungen, Denkspur, Fehlversuchen und begründeten Urteilen. Rollentreue
gilt übergreifend; das andere Kriterium gehört zum jeweiligen Eval.

Unter „Prototyp-Zustand / Szenario“ lassen sich sämtliche Laufzustände sowie
„veraltet“ unabhängig davon ausprobieren. „Erneut prüfen“ ersetzt das Beispiel
durch „wartet“; „Stand neu laden“ führt über „läuft“ zu „fertig“. Das ist eine
manuelle Simulation, kein Polling. Die Zustandsanzeige zeigt sämtliche
Beispielurteile. Fehlende Voraussetzungen blenden Evals samt Hinweis beim
Finalisieren aus. Finalisieren bleibt in jedem Szenario möglich.

Der Runner nutzt die echten Templates, Navigation und Design-Tokens, aber keine
Datenbank, Modellaufrufe oder produktiven Aktionen. Er bindet nur an localhost.
Ein regulärer Django-Start erhält weder Prototyp-Route noch Variantenleiste. Die
gewählte Darstellung soll später in #299 umgesetzt werden. Der Branch und ein
Issue-Verweis wurden noch nicht veröffentlicht.

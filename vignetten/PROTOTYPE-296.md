# Prototyp #296: Evallauf-Ansicht

Throwaway auf `prototype/296-evallauf`, außerhalb von main. Frage: Wie sieht die
Autor:in Ergebnisse und welchen Platz bekommen sie an der Vignette?

Start aus diesem Worktree:

```sh
uv run python -m vignetten.prototype_296
```

Adresse: <http://127.0.0.1:8296/vignetten/296/?variant=A>

- A: Ergebnisse als Matrix direkt unter dem Vignettenkontext.
- B: Eigene Ergebnisübersicht, Evals als aufklappbare Abschnitte.
- C: Evalinputs und Quoten links, Gespräch und Urteile rechts.

Alle Varianten haben dieselben Beispieldaten. Die schwebende Leiste und die
Pfeiltasten wechseln `?variant=A|B|C`. Zellen öffnen die Gespräche mit Auswahl
der Wiederholung, Denkspur, Fehlversuchen und begründeten Urteilen. Rollentreue
ist übergreifend; das andere Kriterium gehört zum jeweiligen Eval.

Unter „Prototyp-Zustand / Szenario“ lassen sich alle Laufzustände sowie
„veraltet“ unabhängig davon ausprobieren. „Starten“ ersetzt das Beispiel durch
„wartet“; „Stand neu laden“ führt über „läuft“ zu „fertig“. Das ist bewusst eine
manuelle Simulation, kein Polling. Die Zustandsanzeige zeigt sämtliche
Beispielurteile. Fehlende Voraussetzungen blenden Evals samt Hinweis beim
Finalisieren aus. Finalisieren ist in jedem Szenario möglich.

Der Runner nutzt die echten Templates, Navigation und Design-Tokens, aber keine
Datenbank, keine Modellaufrufe und keine produktiven Aktionen. Er bindet nur an
localhost und dient ausschließlich dieser Vorschau. Ein regulärer Django-Start
erhält weder Prototyp-Route noch Variantenleiste.

Noch keine validierte Entscheidung. Vorschlag zum Prüfen: A für den Überblick an
der Vignette; B bei vielen Evals; C wenn das Nachlesen der Gespräche die
häufigste Tätigkeit ist. Die tatsächliche Wahl und das Verhalten bei laufenden
Läufen werden nach Sichtung in #296 festgehalten und fließen in #299 ein.

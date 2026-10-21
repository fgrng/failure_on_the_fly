# Simulation ohne App durchspielen

`scripts/simulieren.py` spielt einen Gesprächsschritt mit der simulierten
Schüler:in, ohne Django, Datenbank oder Server. Es rendert eine Vignette aus
`docs/vignetten/` in einen System-Prompt aus `docs/simulation_prompts/` mit
denselben Platzhaltern wie die App und fragt das Sprachmodell aus `.env`. So
lässt sich ein Prompt-Entwurf prüfen, bevor er als Kern-Fassung in die App
kommt.

## Aufruf

```sh
uv run scripts/simulieren.py \
    --vignette docs/vignetten/lu11-01-gleichheitszeichen-als-rechenaufforderung.md \
    --prompt docs/simulation_prompts/2026-10-21-systemprompt.md \
    --verlauf @verlauf.json \
    "Was hast du bei a) eingetragen?"
```

- `--nur-prompt` gibt den gerenderten System-Prompt aus, ohne Modellaufruf und
  ohne Kosten.
- `--verlauf` ist eine JSON-Liste bisheriger Schritte, direkt als String oder
  mit `@pfad.json` aus einer Datei. Ohne `--verlauf` beginnt das Gespräch.
- Das Skript ist zustandslos und liest Vignette und Prompt bei jedem Aufruf neu.

Die Ausgabe auf stdout ist der neue Schritt als JSON, im selben Format wie ein
Verlaufseintrag:

```json
{"eingabe": "Was hast du bei a) eingetragen?", "denkspur": "Gefragt: …", "aeusserung": "Zwölf."}
```

Für den nächsten Schritt die Ausgabe an die Verlaufsliste anhängen, etwa mit
`jq -s '.' schritt1.json schritt2.json > verlauf.json`. Ganze Evalgespräche mit
mehreren Wiederholungen spielt `scripts/evalgespraech.py`
(docs/evals/README.md). Die `denkspur` ist im Verlauf optional; so lassen sich
Schülerantworten von Hand vorgeben. Das Modell sieht frühere Antworten wie in
der App als JSON aus Denkspur und Äusserung (ADR-0064).

Exit-Codes: `0` Erfolg, `1` Modellfehler (`Formatbruch`, `Anbieterfehler`,
`ContentFilter`; Rohantwort auf stderr), `2` Eingabefehler (Datei, Überschrift,
Platzhalter, Umgebung). Anders als die App macht das Skript nur einen Versuch.

## Umgebungsvariablen

In `.env` oder der Umgebung:

```sh
SIMULIEREN_MODELL=openai/moonshotai/Kimi-K2.6        # LiteLLM-Modell-String, Pflicht
SIMULIEREN_API_KEY=…                                  # Pflicht
SIMULIEREN_API_BASE=https://…/openai/v1               # optional
SIMULIEREN_PARAMETER={"reasoning_effort": "none", "allowed_openai_params": ["reasoning_effort"], "temperature": 1}   # optional, JSON-Objekt
```

Welche Modelle der Anbieter hat und welche Parameter sie brauchen (Thinking,
Temperatur, JSON-Schema): scripts/README.md.

## Vignetten-Markdown

Jede `##`-Überschrift ist ein Feldname der Vignette in der Datenbank
(`fehlermuster_beschreibung`, `lernauftrag_text`,
`arbeitsheft_simulationshinweise`, `schuelerin_name`, `lehrperson_geschlecht`
usw.); der Abschnitt darunter ist der Wert. Fehlende oder leere Abschnitte sind
leere Felder, unbekannte Überschriften ein Fehler. Text vor der ersten
`##`-Überschrift ist Einleitung; eine Trennlinie `---` nach dem letzten Feld
beendet die Vignette, was folgt, ist Kommentar. Der Wert ist der Abschnitt,
wie das Formular der App ihn speichert: ohne Leerzeilen und Leerraum außen,
aber mit der Einrückung der ersten Zeile. Mehrzeilige Heftinhalte stehen
deshalb als eingerückter Block (vier Leerzeichen je Zeile), den die App mit
Spalten und Einrückung zeigt; ein umzäunter Codeblock ist ein Fehler, weil die
App die Zäune wörtlich zeigt. Geschlechter sind `weiblich` oder `männlich`;
`budget_typ` darf wie im Editor `Schritte` heißen und wird kleingeschrieben.
Bildfelder tragen einen Dateinamen; das Bild selbst wird nicht gelesen, es
schaltet nur die Bildbeschreibung frei.

## Prompt-Datei

Steht ein ```` ```text ````-Block unter `## System-Prompt-Vorlage`, ist er die
Vorlage; sonst die ganze Datei. Der Block darf einen längeren Zaun tragen
(````` ````text `````), damit die Vorlage selbst Codeblöcke enthalten kann. Verfügbar sind die Prompt- und die
Rahmen-Platzhalter der App (`vignetten/prompt.py`), also auch die
Rahmen-Platzhalter außerhalb des Promptvertrags wie `$lehrperson_pronomen`, die
die App in Prompt-Vorlagen abweist. Ein unbekannter Platzhalter ist ein Fehler.

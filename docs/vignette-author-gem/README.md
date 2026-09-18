# Autoren-Gem: Vignetten-Co-Autor

Dieses Verzeichnis enthält die Bausteine für einen KI-Assistenten (Gem, Skill,
Custom GPT …), der Autor:innen dialogisch beim Verfassen von **Vignetten** für
**FailureOnTheFly** unterstützt. Die Ausgabe ist **feldweise entlang der fünfzehn
Felder des Vignetten-Editors** (kein JSON) und lässt sich direkt ins Formular der
App übertragen.

Autor:innen schreiben **keine** Prompts: System-Prompt, User-Prompt und
Rahmenhandlung kommen aus dem **Simulationskern** und sind für alle Vignetten und
alle Fächer identisch (ADR-0004, ADR-0010). Der Assistent liefert deshalb
ausschließlich Inhaltsfelder.

## Dateien

- `SYSTEM_PROMPT.md` — die Systeminstruktion des Assistenten.
- `knowledge/01-editor-felder-und-schema.md` — die fünfzehn Editor-Felder mit
  Labels, Reihenfolge, Wirkung, Lebenszyklus und Finalisierungsregeln.
- `knowledge/02-prompt-und-sichtbarkeit.md` — der Simulationskern, der
  Acht-Felder-Vertrag mit den Prompt-Vorlagen, die Rahmenhandlung und die
  Teilnehmendensichtbarkeit.
- `knowledge/03-fehlermuster-leitfaden.md` — Kern: ein simulierbares Fehlermuster
  schreiben.
- `knowledge/04-beispiele.md` — zwei vollständige Beispielvignetten im
  Zielformat.

## Gem in Google Gemini anlegen

1. In Gemini ein neues **Gem** erstellen.
2. Den Inhalt von `SYSTEM_PROMPT.md` als **Instruktion** des Gems einfügen.
3. Die vier Dateien unter `knowledge/` als **Wissensdateien** hochladen.
4. Das Gem testen: ein Fehlermuster oder eine Aufgabenidee nennen und den
   feldweisen Entwurf erzeugen lassen.

## Ergebnis übertragen

Den ausgegebenen Feld-Block Feld für Feld in den **Vignetten-Editor** übertragen
(`/vignetten/<pk>/bearbeiten/`, siehe `vignetten/`). Ein Arbeitsheft-Bild lädt
die Autor:in dort selbst hoch; der Assistent liefert dafür nur den
Arbeitsheft-Text und die Arbeitsheft-Beschreibung.

Vor dem **Finalisieren** die Vignette im **Probelauf** spielen: Dort ist die
Denkspur der simulierten Schüler:in live sichtbar, und es zeigt sich, ob das
Fehlermuster im Gespräch trägt. Ein Entwurf lässt sich beliebig oft ändern; eine
finale Fassung ist unveränderlich.

## Pflege

Wenn sich die Felder von `vignetten.models.Vignette`, die Labels in
`vignetten.forms.VignetteForm`, die Finalisierungsregeln in
`Vignette.finalisieren()` oder die Vorlagen in `simulation/standardkern.py`
ändern, müssen `knowledge/01-editor-felder-und-schema.md` und
`knowledge/02-prompt-und-sichtbarkeit.md` nachgezogen werden. Der
Platzhaltervertrag steht in `simulation/models.py` (`VERTRAG_PROMPT`,
`VERTRAG_RAHMEN`); die Projektterminologie in `CONTEXT.md`.

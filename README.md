# failure_on_the_fly

Web-basierter Simulator von Schüler:innen mit Fehlermustern für das Üben
diagnostischer Gesprächsführung.

## Simulationskern

Angemeldete Nutzer:innen können die aktuellste finale Kern-Fassung und die
aktive Modell-Konfiguration read-only unter `/system/kern/` einsehen. Ist noch
kein finaler Kern vorhanden, weist die Ansicht auf `manage.py kern_initialisieren`
hin.

## Modell-Konfiguration

Eine Modell-Konfiguration wählt über `sprachmodell` entweder den
deterministischen Testadapter `fake` oder einen LiteLLM-Modell-String wie
`openai/gpt-…` beziehungsweise `anthropic/claude-opus-4-8`. Ihre `parameter`
werden unverändert an LiteLLM weitergereicht, etwa `{"temperature": 0.2}`.
Damit kann eine neue Konfiguration Anbieter oder Modell ohne Codeänderung
wechseln.

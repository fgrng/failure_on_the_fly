# failure_on_the_fly

Web-basierter Simulator von Schüler:innen mit Fehlermustern für das Üben
diagnostischer Gesprächsführung.

## Modell-Konfiguration

Eine Modell-Konfiguration wählt über `sprachmodell` entweder den
deterministischen Testadapter `fake` oder einen LiteLLM-Modell-String wie
`openai/gpt-…` beziehungsweise `anthropic/claude-opus-4-8`. Ihre `parameter`
werden unverändert an LiteLLM weitergereicht, etwa `{"temperature": 0.2}`.
Damit kann eine neue Konfiguration Anbieter oder Modell ohne Codeänderung
wechseln.

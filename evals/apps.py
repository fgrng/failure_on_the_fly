"""App-Konfiguration der Evalläufe."""

from django.apps import AppConfig


class EvalsConfig(AppConfig):
    """Evallauf, Evalgespräch und Urteil; nichts zeigt auf diese App (ADR-0016)."""

    name = "evals"

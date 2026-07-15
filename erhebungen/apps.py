"""App-Konfiguration für Erhebungen."""

from django.apps import AppConfig


class ErhebungenConfig(AppConfig):
    """Bündelt Erhebungen, Stichproben und ihre späteren Bindungen."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "erhebungen"

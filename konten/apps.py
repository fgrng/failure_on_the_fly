"""Django-App-Konfiguration für Konten."""

from django.apps import AppConfig


class KontenConfig(AppConfig):
    """Konfiguriert die Konten-App."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "konten"

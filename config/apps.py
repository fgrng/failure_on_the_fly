"""Django-App-Konfiguration für projektweite Einstellungen jenseits von settings.py."""

from django.apps import AppConfig


class ConfigConfig(AppConfig):
    """Passt Django dort an, wo eine Einstellung allein nicht reicht."""

    name = "config"

    def ready(self) -> None:
        """Ersetzt Djangos Leerauswahl, die in der deutschen Übersetzung fehlt."""
        from django.db.models import fields

        fields.BLANK_CHOICE_LABEL = "Bitte wählen …"

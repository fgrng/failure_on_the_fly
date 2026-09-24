"""Django-App-Konfiguration für die Darstellung der Markdown-Texte."""

from django.apps import AppConfig


class TexteConfig(AppConfig):
    """Stellt das Rendermodul und seine Template-Filter allen Apps bereit."""

    name = "texte"

    def ready(self) -> None:
        """Ersetzt Djangos Leerauswahl, die in der deutschen Übersetzung fehlt."""
        from django.db.models import fields

        fields.BLANK_CHOICE_LABEL = "Bitte wählen …"

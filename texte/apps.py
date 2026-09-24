"""Django-App-Konfiguration für die Darstellung der Markdown-Texte."""

from django.apps import AppConfig


class TexteConfig(AppConfig):
    """Stellt das Rendermodul und seine Template-Filter allen Apps bereit."""

    name = "texte"

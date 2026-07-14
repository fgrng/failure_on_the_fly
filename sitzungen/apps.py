"""App-Konfiguration der Sitzungsabläufe."""

from django.apps import AppConfig


class SitzungenConfig(AppConfig):
    """Bündelt schreibfreie und spätere persistierte Sitzungsabläufe."""

    name = "sitzungen"

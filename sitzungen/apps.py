"""App-Konfiguration der Sitzungsabläufe."""

from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_out


class SitzungenConfig(AppConfig):
    """Bündelt schreibfreie und spätere persistierte Sitzungsabläufe."""

    name = "sitzungen"

    def ready(self) -> None:
        """Verbindet das Abmelden mit dem Löschen des Probelaufs."""

        from sitzungen.probelauf_speicher import probelauf_beim_abmelden_loeschen

        user_logged_out.connect(probelauf_beim_abmelden_loeschen)

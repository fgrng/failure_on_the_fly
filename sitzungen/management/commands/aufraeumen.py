"""Das nächtliche Aufräumen im Betrieb."""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from sitzungen import kurzlebiger_speicher


class Command(BaseCommand):
    """Löscht abgelaufene Einträge des kurzlebigen Speichers und Konto-Sessions."""

    help = (
        "Löscht abgelaufene Einträge des kurzlebigen Speichers (flüchtige "
        "Teilnahme, Probelauf) und führt clearsessions aus."
    )

    def handle(self, *args: object, **options: object) -> None:
        """Räumt zuerst den kurzlebigen Speicher, dann die Sessions."""

        geloescht: int = kurzlebiger_speicher.abgelaufene_loeschen()
        self.stdout.write(f"{geloescht} abgelaufene Einträge gelöscht.")
        call_command("clearsessions")

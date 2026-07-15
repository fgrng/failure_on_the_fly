"""Initialisiert den Simulationskern einer frischen Instanz."""

from django.core.management.base import BaseCommand

from simulation.models import Simulationskern
from simulation.standardkern import STANDARDKERN_VORLAGEN


class Command(BaseCommand):
    """Legt den finalen Platzhalter-Kern genau einmal an."""

    def handle(self, *args: object, **options: object) -> None:
        """Finalisiert den Vorlagentext über die reguläre Lebenszyklus-Naht."""

        if Simulationskern.objects.exists():
            return

        kern: Simulationskern = Simulationskern.objects.anlegen(
            **STANDARDKERN_VORLAGEN
        )
        kern.finalisieren()

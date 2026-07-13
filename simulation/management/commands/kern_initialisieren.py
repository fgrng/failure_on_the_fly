"""Initialisiert den Simulationskern einer frischen Instanz."""

from pathlib import Path

from django.core.management.base import BaseCommand

from simulation.models import Simulationskern


_PLATZHALTER_SYSTEM_PROMPT_VORLAGE_PFAD: Path = (
    Path(__file__).resolve().parents[2]
    / "vorlagen"
    / "platzhalter_system_prompt.txt"
)


class Command(BaseCommand):
    """Legt den finalen Platzhalter-Kern genau einmal an."""

    def handle(self, *args: object, **options: object) -> None:
        """Finalisiert den Vorlagentext über die reguläre Lebenszyklus-Naht."""

        if Simulationskern.objects.exists():
            return

        kern: Simulationskern = Simulationskern.objects.anlegen(
            system_prompt_vorlage=_PLATZHALTER_SYSTEM_PROMPT_VORLAGE_PFAD.read_text(
                encoding="utf-8",
            ),
        )
        kern.finalisieren()

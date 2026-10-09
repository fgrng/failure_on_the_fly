"""Der Hintergrundprozess der Evalläufe (ADR-0047)."""

import logging
from argparse import ArgumentParser

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from evals.ausfuehrung import evallauf_ausfuehren
from evals.models import Evallauf

logger: logging.Logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Arbeitet den ältesten wartenden Evallauf ab."""

    help = "Arbeitet im Einmal-Modus höchstens den ältesten wartenden Evallauf ab."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Der Einmal-Modus ist bisher der einzige."""

        parser.add_argument(
            "--einmal",
            action="store_true",
            help="Höchstens einen Evallauf abarbeiten und dann enden.",
        )

    def handle(self, *args: object, einmal: bool, **options: object) -> None:
        """Nimmt den ältesten wartenden Lauf, führt ihn aus und schließt ihn ab."""

        if not einmal:
            raise CommandError("Bisher gibt es nur den Einmal-Modus: --einmal.")
        lauf: Evallauf | None = (
            Evallauf.objects.filter(zustand=Evallauf.Zustand.WARTET)
            .order_by("ausgeloest_am", "pk")
            .first()
        )
        # Die bedingte Aktualisierung nimmt den Lauf nur, solange er wartet.
        if lauf is None or not Evallauf.objects.filter(
            pk=lauf.pk, zustand=Evallauf.Zustand.WARTET
        ).update(zustand=Evallauf.Zustand.LAEUFT, gestartet_am=timezone.now()):
            return
        ende: Evallauf.Zustand = Evallauf.Zustand.FERTIG
        try:
            evallauf_ausfuehren(lauf)
        # Anbieterfehler fängt die Simulation selbst ab; was hier ankommt, ist
        # unerwartet und soll den Lauf abgebrochen hinterlassen (ADR-0047).
        except Exception:
            logger.exception("Evallauf %s abgebrochen.", lauf.pk)
            ende = Evallauf.Zustand.ABGEBROCHEN
        Evallauf.objects.filter(pk=lauf.pk, zustand=Evallauf.Zustand.LAEUFT).update(
            zustand=ende, beendet_am=timezone.now()
        )

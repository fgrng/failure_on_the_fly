"""Der Hintergrundprozess der Evalläufe (ADR-0047)."""

import fcntl
import logging
from argparse import ArgumentParser
from collections.abc import Iterator
from contextlib import contextmanager

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from evals.ausfuehrung import evallauf_ausfuehren
from evals.models import Evallauf

logger: logging.Logger = logging.getLogger(__name__)


@contextmanager
def _exklusiv() -> Iterator[bool]:
    # Ob dieser Prozess als einziger arbeitet. Die Sperre hängt an der offenen
    # Datei: Stirbt der Prozess, gibt das Betriebssystem sie frei, und erst
    # dann gilt ein laufender Lauf als verwaist.

    with settings.EVALLAEUFE_SPERRE.open("a") as sperre:
        try:
            fcntl.flock(sperre, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
        else:
            yield True


class Command(BaseCommand):
    """Bricht verwaiste Evalläufe ab und arbeitet den ältesten wartenden ab."""

    help = "Arbeitet im Einmal-Modus höchstens den ältesten wartenden Evallauf ab."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Der Einmal-Modus ist bisher der einzige."""

        parser.add_argument(
            "--einmal",
            action="store_true",
            help="Höchstens einen Evallauf abarbeiten und dann enden.",
        )

    def handle(self, *args: object, einmal: bool, **options: object) -> None:
        """Arbeitet nur, wenn kein anderer Hintergrundprozess die Sperre hält."""

        if not einmal:
            raise CommandError("Bisher gibt es nur den Einmal-Modus: --einmal.")
        with _exklusiv() as allein:
            if not allein:
                self.stderr.write("Ein anderer Hintergrundprozess arbeitet bereits.")
                return
            # Mit der Sperre läuft kein anderer Prozess mehr; was noch „Läuft“
            # sagt, stammt von einem abgebrochenen Vorgänger.
            Evallauf.objects.filter(zustand=Evallauf.Zustand.LAEUFT).update(
                zustand=Evallauf.Zustand.ABGEBROCHEN, beendet_am=timezone.now()
            )
            self._aeltesten_abarbeiten()

    def _aeltesten_abarbeiten(self) -> None:
        # Nimmt den ältesten wartenden Lauf, führt ihn aus und schließt ihn ab.

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

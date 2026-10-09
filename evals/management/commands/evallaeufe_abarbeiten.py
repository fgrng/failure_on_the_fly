"""Der Hintergrundprozess der Evalläufe (ADR-0047)."""

import fcntl
import logging
import math
import signal
import time
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
    """Bricht verwaiste Evalläufe ab und arbeitet wartende nacheinander ab."""

    help = (
        "Arbeitet wartende Evalläufe dauerhaft ab, den ältesten zuerst; "
        "mit --einmal höchstens einen."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Dauerbetrieb als Dienst oder Einmal-Modus für Tests und Fehlersuche."""

        parser.add_argument(
            "--einmal",
            action="store_true",
            help="Höchstens einen Evallauf abarbeiten und dann enden.",
        )
        parser.add_argument(
            "--intervall",
            type=float,
            default=10.0,
            help="Sekunden Wartezeit, wenn kein Evallauf wartet (Standard: 10).",
        )

    def handle(
        self, *args: object, einmal: bool, intervall: float, **options: object
    ) -> None:
        """Arbeitet nur, wenn kein anderer Hintergrundprozess die Sperre hält."""

        # Ohne echte Wartezeit scheiterte `time.sleep` oder der Dienst pollte
        # die Datenbank pausenlos.
        if not 0 < intervall < math.inf:
            raise CommandError("--intervall braucht eine positive Zahl von Sekunden.")
        with _exklusiv() as allein:
            if not allein:
                self.stderr.write("Ein anderer Hintergrundprozess arbeitet bereits.")
                return
            # Mit der Sperre läuft kein anderer Prozess mehr; was noch „Läuft“
            # sagt, stammt von einem abgebrochenen Vorgänger.
            verwaist: int = Evallauf.objects.filter(
                zustand=Evallauf.Zustand.LAEUFT
            ).update(zustand=Evallauf.Zustand.ABGEBROCHEN, beendet_am=timezone.now())
            if verwaist:
                logger.warning("%d verwaiste Evalläufe abgebrochen.", verwaist)
            if einmal:
                self._aeltesten_abarbeiten()
            else:
                self._dauerhaft_abarbeiten(intervall)

    def _dauerhaft_abarbeiten(self, intervall: float) -> None:
        # Bis supervisord stoppt (SIGTERM) oder Strg+C: SIGTERM wird wie
        # SIGINT zum KeyboardInterrupt, damit ein laufender Lauf noch als
        # abgebrochen abgeschlossen wird.

        vorher = signal.signal(signal.SIGTERM, signal.default_int_handler)
        logger.info("Hintergrundprozess gestartet, Intervall %s s.", intervall)
        try:
            while True:
                if not self._aeltesten_abarbeiten():
                    time.sleep(intervall)
        except KeyboardInterrupt:
            logger.info("Hintergrundprozess beendet.")
        finally:
            signal.signal(signal.SIGTERM, vorher)

    def _aeltesten_abarbeiten(self) -> bool:
        # Nimmt den ältesten wartenden Lauf, führt ihn aus und schließt ihn ab.
        # Sagt, ob es einen gab.

        lauf: Evallauf | None = (
            Evallauf.objects.filter(zustand=Evallauf.Zustand.WARTET)
            .order_by("ausgeloest_am", "pk")
            .first()
        )
        # Die bedingte Aktualisierung nimmt den Lauf nur, solange er wartet.
        if lauf is None or not Evallauf.objects.filter(
            pk=lauf.pk, zustand=Evallauf.Zustand.WARTET
        ).update(zustand=Evallauf.Zustand.LAEUFT, gestartet_am=timezone.now()):
            return False
        logger.info("Evallauf %s gestartet.", lauf.pk)
        ende: Evallauf.Zustand = Evallauf.Zustand.ABGEBROCHEN
        try:
            evallauf_ausfuehren(lauf)
            ende = Evallauf.Zustand.FERTIG
        # Anbieterfehler fängt die Simulation selbst ab; was hier ankommt, ist
        # unerwartet und soll den Lauf abgebrochen hinterlassen (ADR-0047).
        except Exception:
            logger.exception("Unerwarteter Fehler in Evallauf %s.", lauf.pk)
        # Auch ein Stopp des Dienstes mitten im Lauf schließt ihn ab.
        finally:
            Evallauf.objects.filter(pk=lauf.pk, zustand=Evallauf.Zustand.LAEUFT).update(
                zustand=ende, beendet_am=timezone.now()
            )
            logger.info("Evallauf %s %s.", lauf.pk, ende.label.lower())
        return True

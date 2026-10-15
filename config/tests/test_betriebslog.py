"""Tests für das Betriebslog auf stderr (ADR-0065)."""

import io
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from django.http import HttpRequest, HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import path, reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finaler_kern,
    konto_mit_rollen,
    vignetten_entwurf,
)
from simulation.models import Verwendung


def _scheitern(request: HttpRequest) -> HttpResponse:
    raise RuntimeError("Absichtlicher Serverfehler")


urlpatterns = [path("scheitern/", _scheitern)]


@contextmanager
def _stderr_mitschneiden() -> Iterator[io.StringIO]:
    """Leitet alle konfigurierten Stream-Handler in einen gemeinsamen Puffer um.

    Jeder Handler hält den Strom, den er beim Start von Django vorfand; ein
    Umlenken von `sys.stderr` erreicht ihn nicht mehr.
    """

    handler: list[logging.StreamHandler] = [
        h
        for name in logging.getHandlerNames()
        if isinstance(h := logging.getHandlerByName(name), logging.StreamHandler)
    ]
    puffer: io.StringIO = io.StringIO()
    vorher = [h.setStream(puffer) for h in handler]
    try:
        yield puffer
    finally:
        for h, strom in zip(handler, vorher, strict=True):
            h.setStream(strom)


@override_settings(DEBUG=False, ROOT_URLCONF=__name__)
class BetriebslogTests(TestCase):
    """Was mit DEBUG=False auf stderr landet und was nicht."""

    def setUp(self) -> None:
        """Ein Client, der Serverfehler als 500-Antwort zurückgibt."""

        self.client = Client(raise_request_exception=False)

    def test_unbehandelte_ausnahme_schreibt_traceback(self) -> None:
        """Ein Serverfehler erscheint samt Traceback auf stderr."""

        with _stderr_mitschneiden() as stderr:
            response: HttpResponse = self.client.get("/scheitern/")

        self.assertEqual(response.status_code, 500)
        self.assertIn("ERROR django.request: Internal Server Error", stderr.getvalue())
        self.assertIn("Traceback", stderr.getvalue())
        self.assertIn("RuntimeError: Absichtlicher Serverfehler", stderr.getvalue())

    def test_404_schreibt_nichts(self) -> None:
        """Ein 404 bleibt still, auch wenn sein Pfad ein Token trüge."""

        with _stderr_mitschneiden() as stderr:
            response: HttpResponse = self.client.get("/gibt-es-nicht/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(stderr.getvalue(), "")

    def test_warnung_eines_beliebigen_loggers_erscheint(self) -> None:
        """Ein Logger ohne eigene Konfiguration schreibt ab WARNING."""

        with _stderr_mitschneiden() as stderr:
            logging.getLogger("simulation.irgendwo").info("Nur eine Info")
            logging.getLogger("simulation.irgendwo").warning("Eine Warnung")

        self.assertNotIn("Nur eine Info", stderr.getvalue())
        self.assertIn("WARNING simulation.irgendwo: Eine Warnung", stderr.getvalue())

    def test_evals_schreibt_info_genau_einmal(self) -> None:
        """Der Logger `evals` schreibt ab INFO, jede Meldung einmal."""

        with _stderr_mitschneiden() as stderr:
            logging.getLogger("evals.management").info("Evallauf gestartet")

        self.assertEqual(stderr.getvalue().count("Evallauf gestartet"), 1)

    def test_runserver_meldet_jede_anfrage_genau_einmal(self) -> None:
        """Die Anfragezeilen von runserver bleiben ab INFO erhalten, ohne Doppel."""

        with _stderr_mitschneiden() as stderr:
            logging.getLogger("django.server").info('"GET /start/ HTTP/1.1" 200 5')

        self.assertEqual(stderr.getvalue().count('"GET /start/ HTTP/1.1" 200 5'), 1)


@override_settings(DEBUG=False)
class InhalteImBetriebslogTests(TestCase):
    """ADR-0065: Ausnahmetexte an den Nähten tragen keine Inhalte."""

    def test_gescheiterter_gespraechsschritt_verraet_die_eingabe_nicht(
        self,
    ) -> None:
        """Eine unerwartete Ausnahme der Sprachmodell-Naht lässt die Eingabe aus.

        Das leere Skript des Fakes lässt den Aufruf mit einem `IndexError`
        scheitern, den keine Fehlversuchs-Behandlung abfängt.
        """

        ada = konto_mit_rollen("ada", "Autor:in")
        finaler_kern()
        aktive_modell_konfiguration(Verwendung.SCHUELERIN, skript=[])
        client: Client = Client(raise_request_exception=False)
        client.force_login(ada)
        client.post(
            reverse("sitzungen:probelauf_starten", args=[vignetten_entwurf(ada).pk])
        )
        inhalt: str = "Markante Frage 7f3a an die Schülerin"

        with _stderr_mitschneiden() as stderr:
            response: HttpResponse = client.post(
                reverse("sitzungen:probelauf_gespraech"), {"eingabe": inhalt}
            )

        self.assertEqual(response.status_code, 500)
        self.assertIn("IndexError", stderr.getvalue())
        self.assertNotIn("7f3a", stderr.getvalue())
        self.assertNotIn("7f3a", response.content.decode())

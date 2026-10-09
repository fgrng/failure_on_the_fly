"""Der Hintergrundprozess im Einmal-Modus über `call_command`."""

from datetime import UTC, datetime

import pytest
import time_machine
from django.core.management import CommandError, call_command

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from evals.models import Evallauf
from evals.tests.aufbau import antworten, drei_fakes, finaler_katalog, urteile
from konten.models import Konto

_AUSGELOEST: datetime = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)
_ABGEARBEITET: datetime = datetime(2026, 10, 9, 10, 0, tzinfo=UTC)


def _ausgeloest(konto: Konto, name: str, um: datetime) -> Evallauf:
    # Löst zu einer festen Zeit einen Lauf über einer neuen finalen Fassung aus.

    with time_machine.travel(um, tick=False):
        return Evallauf.objects.ausloesen(finale_vignette(konto, name=name))


@pytest.mark.django_db
def test_einmal_modus_arbeitet_nur_den_aeltesten_wartenden_lauf_ab() -> None:
    """Der älteste wird fertig samt Zeitpunkten, der jüngere wartet weiter."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    ada: Konto = konto_mit_rollen("ada", "Autor:in")
    juengerer: Evallauf = _ausgeloest(ada, "Jünger", _AUSGELOEST.replace(minute=5))
    aeltester: Evallauf = _ausgeloest(ada, "Älter", _AUSGELOEST)

    with time_machine.travel(_ABGEARBEITET, tick=False):
        call_command("evallaeufe_abarbeiten", "--einmal")

    aeltester.refresh_from_db()
    juengerer.refresh_from_db()
    assert (
        aeltester.zustand,
        aeltester.gestartet_am,
        aeltester.beendet_am,
        juengerer.zustand,
    ) == (
        Evallauf.Zustand.FERTIG,
        _ABGEARBEITET,
        _ABGEARBEITET,
        Evallauf.Zustand.WARTET,
    )


@pytest.mark.django_db
def test_einmal_modus_ohne_wartenden_lauf_aendert_nichts() -> None:
    """Ein fertiger Lauf wird nicht noch einmal ausgeführt."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    lauf: Evallauf = _ausgeloest(konto_mit_rollen("ada", "Autor:in"), "", _AUSGELOEST)
    call_command("evallaeufe_abarbeiten", "--einmal")

    call_command("evallaeufe_abarbeiten", "--einmal")

    assert lauf.gespraeche.count() == 1


@pytest.mark.django_db
def test_abbruch_mitten_im_lauf_laesst_die_fertigen_gespraeche_stehen() -> None:
    """Ein Fehler mitten im Lauf hinterlässt ihn abgebrochen samt dem Fertigen."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    # Das Skript reicht nur für das erste Gespräch; das zweite bricht ab.
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    lauf: Evallauf = _ausgeloest(konto_mit_rollen("ada", "Autor:in"), "", _AUSGELOEST)

    call_command("evallaeufe_abarbeiten", "--einmal")

    lauf.refresh_from_db()
    assert lauf.zustand == Evallauf.Zustand.ABGEBROCHEN
    assert lauf.uebersicht()[0].zeilen[0].zellen[0].erfuellt == 1


def test_ohne_einmal_modus_verweigert_der_command() -> None:
    """Der dauerhafte Dienst folgt; bis dahin gibt es nur den Einmal-Modus."""

    with pytest.raises(CommandError):
        call_command("evallaeufe_abarbeiten")

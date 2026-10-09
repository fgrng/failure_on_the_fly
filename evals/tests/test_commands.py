"""Der Hintergrundprozess im Einmal-Modus über `call_command`."""

import fcntl
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
import time_machine
from django.core.management import CommandError, call_command

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from evals.ausfuehrung import evallauf_ausfuehren
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


def _verwaist(lauf: Evallauf) -> None:
    # Ein Lauf, dessen Prozess nach dem ersten Gespräch starb: Er steht auf
    # „Läuft“, das Geschriebene bleibt.

    evallauf_ausfuehren(lauf)
    Evallauf.objects.filter(pk=lauf.pk).update(zustand=Evallauf.Zustand.LAEUFT)


@pytest.mark.django_db
def test_start_bricht_verwaiste_laeufe_ab_und_arbeitet_wartende_ab() -> None:
    """Der Verwaiste wird abgebrochen, ohne Fortsetzung; der Wartende läuft danach."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, True))
    ada: Konto = konto_mit_rollen("ada", "Autor:in")
    verwaist: Evallauf = _ausgeloest(ada, "Verwaist", _AUSGELOEST)
    _verwaist(verwaist)
    wartend: Evallauf = _ausgeloest(ada, "Wartend", _AUSGELOEST.replace(minute=5))

    with time_machine.travel(_ABGEARBEITET, tick=False):
        call_command("evallaeufe_abarbeiten", "--einmal")

    verwaist.refresh_from_db()
    wartend.refresh_from_db()
    assert (
        verwaist.zustand,
        verwaist.beendet_am,
        verwaist.gespraeche.count(),
        wartend.zustand,
    ) == (Evallauf.Zustand.ABGEBROCHEN, _ABGEARBEITET, 1, Evallauf.Zustand.FERTIG)


@pytest.mark.django_db
def test_zweiter_prozess_laesst_aktiven_lauf_und_warteschlange_unberuehrt(
    eigene_sperrdatei: Path,
) -> None:
    """Solange ein Prozess die Sperre hält, bereinigt und nimmt ein zweiter nichts."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, True))
    ada: Konto = konto_mit_rollen("ada", "Autor:in")
    aktiv: Evallauf = _ausgeloest(ada, "Aktiv", _AUSGELOEST)
    _verwaist(aktiv)
    wartend: Evallauf = _ausgeloest(ada, "Wartend", _AUSGELOEST.replace(minute=5))

    meldung: StringIO = StringIO()

    with eigene_sperrdatei.open("a") as sperre:
        fcntl.flock(sperre, fcntl.LOCK_EX | fcntl.LOCK_NB)
        call_command("evallaeufe_abarbeiten", "--einmal", stderr=meldung)

    aktiv.refresh_from_db()
    wartend.refresh_from_db()
    assert (aktiv.zustand, wartend.zustand, meldung.getvalue()) == (
        Evallauf.Zustand.LAEUFT,
        Evallauf.Zustand.WARTET,
        "Ein anderer Hintergrundprozess arbeitet bereits.\n",
    )


def test_ohne_einmal_modus_verweigert_der_command() -> None:
    """Der dauerhafte Dienst folgt; bis dahin gibt es nur den Einmal-Modus."""

    with pytest.raises(CommandError):
        call_command("evallaeufe_abarbeiten")

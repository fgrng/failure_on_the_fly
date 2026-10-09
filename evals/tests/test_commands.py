"""Der Hintergrundprozess im Einmal-Modus über `call_command`."""

import fcntl
import logging
import signal
from collections.abc import Callable
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
import time_machine
from django.core.management import call_command
from django.db import connection

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from config.tests.sprachmodell import vor_jedem_aufruf
from evals.ausfuehrung import evallauf_ausfuehren
from evals.models import Evallauf
from evals.tests.aufbau import (
    aeusserungen,
    antworten,
    drei_fakes,
    finaler_katalog,
    gelenkt,
    urteile,
)
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


def _anhalten_nach(wartezeiten: list[float], anzahl: int) -> Callable[[float], None]:
    # Ersetzt das Warten des Dienstes: merkt sich jede Wartezeit und schickt
    # nach `anzahl` Wartezeiten ein SIGTERM, wie supervisord beim Stoppen.

    def warten(sekunden: float) -> None:
        wartezeiten.append(sekunden)
        if len(wartezeiten) >= anzahl:
            signal.raise_signal(signal.SIGTERM)

    return warten


@pytest.mark.django_db
def test_dauermodus_arbeitet_wartende_nacheinander_ab_und_wartet_dann() -> None:
    """Ohne --einmal nimmt der Dienst den ältesten zuerst und pollt bei leerer Warteschlange."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, True))
    ada: Konto = konto_mit_rollen("ada", "Autor:in")
    juengerer: Evallauf = _ausgeloest(ada, "Jünger", _AUSGELOEST.replace(minute=5))
    aeltester: Evallauf = _ausgeloest(ada, "Älter", _AUSGELOEST)
    wartezeiten: list[float] = []

    with mock.patch("time.sleep", _anhalten_nach(wartezeiten, 1)):
        call_command("evallaeufe_abarbeiten", "--intervall", "7")

    aeltester.refresh_from_db()
    juengerer.refresh_from_db()
    assert aeltester.gestartet_am < juengerer.gestartet_am
    assert (aeltester.zustand, juengerer.zustand, wartezeiten) == (
        Evallauf.Zustand.FERTIG,
        Evallauf.Zustand.FERTIG,
        [7.0],
    )


@pytest.mark.django_db
def test_dauermodus_nimmt_einen_waehrend_des_wartens_ausgeloesten_lauf() -> None:
    """Nach einer Wartezeit ohne Arbeit pollt der Dienst erneut."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    ada: Konto = konto_mit_rollen("ada", "Autor:in")
    spaeter: list[Evallauf] = []
    wartezeiten: list[float] = []
    anhalten: Callable[[float], None] = _anhalten_nach(wartezeiten, 2)

    def warten(sekunden: float) -> None:
        # Während der ersten Wartezeit startet die Autor:in einen Lauf.
        if not wartezeiten:
            spaeter.append(Evallauf.objects.ausloesen(finale_vignette(ada)))
        anhalten(sekunden)

    with mock.patch("time.sleep", warten):
        call_command("evallaeufe_abarbeiten")

    spaeter[0].refresh_from_db()
    assert (spaeter[0].zustand, len(wartezeiten)) == (Evallauf.Zustand.FERTIG, 2)


@pytest.mark.django_db
def test_stopp_mitten_im_lauf_bricht_ihn_ab_und_beendet_den_dienst(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SIGTERM im Lauf: Fertiges bleibt, der Lauf ist abgebrochen, das Log sagt es."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, True))
    lauf: Evallauf = _ausgeloest(konto_mit_rollen("ada", "Autor:in"), "", _AUSGELOEST)
    aufrufe: list[list[dict[str, str]]] = []

    def stoppen(nachrichten: list[dict[str, str]]) -> None:
        # Nach Antwort und Urteil des ersten Gesprächs stoppt supervisord.
        aufrufe.append(nachrichten)
        if len(aufrufe) == 3:
            signal.raise_signal(signal.SIGTERM)

    with (
        caplog.at_level(logging.INFO),
        vor_jedem_aufruf(stoppen),
        mock.patch("time.sleep", _anhalten_nach([], 1)),
    ):
        call_command("evallaeufe_abarbeiten")

    lauf.refresh_from_db()
    assert (lauf.zustand, lauf.uebersicht()[0].zeilen[0].zellen[0].erfuellt) == (
        Evallauf.Zustand.ABGEBROCHEN,
        1,
    )
    assert [r.getMessage() for r in caplog.records] == [
        "Hintergrundprozess gestartet, Intervall 10.0 s.",
        f"Evallauf {lauf.pk} gestartet.",
        f"Evallauf {lauf.pk} abgebrochen.",
        "Hintergrundprozess beendet.",
    ]


@pytest.mark.django_db(transaction=True)
def test_kein_modellaufruf_haelt_eine_schreibtransaktion() -> None:
    """Zwischen den kurzen Schreibvorgängen bleibt die Datenbank für andere frei."""

    finaler_katalog(k=1, schritte=("Eins", gelenkt("Nachfragen")))
    drei_fakes(
        schuelerin=antworten(2),
        lehrperson=aeusserungen(1),
        bewerter=urteile(True, True),
    )
    _ausgeloest(konto_mit_rollen("ada", "Autor:in"), "", _AUSGELOEST)
    offen: list[bool] = []

    with vor_jedem_aufruf(
        lambda _nachrichten: offen.append(connection.in_atomic_block)
    ):
        call_command("evallaeufe_abarbeiten", "--einmal")

    assert offen == [False] * 5


@pytest.mark.django_db
def test_dauermodus_bricht_beim_start_verwaiste_laeufe_ab(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Nach einem Neustart des Dienstes steht kein Lauf mehr auf „Läuft“."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    verwaist: Evallauf = _ausgeloest(
        konto_mit_rollen("ada", "Autor:in"), "", _AUSGELOEST
    )
    _verwaist(verwaist)

    with caplog.at_level(logging.INFO), mock.patch("time.sleep", _anhalten_nach([], 1)):
        call_command("evallaeufe_abarbeiten")

    verwaist.refresh_from_db()
    assert verwaist.zustand == Evallauf.Zustand.ABGEBROCHEN
    assert "1 verwaiste Evalläufe abgebrochen." in caplog.messages

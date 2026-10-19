"""Tests für den kurzlebigen Speicher vorgehaltener Inhalte."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from time_machine import TimeMachineFixture

from sitzungen import kurzlebiger_speicher

_SCHLUESSEL: str = "sitzung-1"
_BEGINN: datetime = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


def test_lesen_verschiebt_die_frist_nicht(time_machine: TimeMachineFixture) -> None:
    """Nur Schreiben und Vorhalten halten einen Eintrag am Leben."""

    time_machine.move_to(_BEGINN, tick=False)
    kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 1})

    time_machine.move_to(_BEGINN + timedelta(hours=20), tick=False)
    kurzlebiger_speicher.lesen(_SCHLUESSEL)
    time_machine.move_to(_BEGINN + timedelta(hours=25), tick=False)

    assert kurzlebiger_speicher.lesen(_SCHLUESSEL) is None


def test_vorhalten_verschiebt_die_frist(time_machine: TimeMachineFixture) -> None:
    """Ein Zugriff binnen eines Tages hält den Eintrag einen weiteren Tag."""

    time_machine.move_to(_BEGINN, tick=False)
    kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 1})

    time_machine.move_to(_BEGINN + timedelta(hours=20), tick=False)
    kurzlebiger_speicher.vorhalten(_SCHLUESSEL)
    time_machine.move_to(_BEGINN + timedelta(hours=40), tick=False)

    assert kurzlebiger_speicher.lesen(_SCHLUESSEL) == {"schritte": 1}


def test_vorhalten_belebt_keinen_abgelaufenen_eintrag(
    time_machine: TimeMachineFixture,
) -> None:
    """Nach Ablauf der Frist bleibt der Eintrag abgelaufen."""

    time_machine.move_to(_BEGINN, tick=False)
    kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 1})

    time_machine.move_to(_BEGINN + timedelta(days=1, seconds=1), tick=False)
    kurzlebiger_speicher.vorhalten(_SCHLUESSEL)

    assert kurzlebiger_speicher.lesen(_SCHLUESSEL) is None


def test_vorhalten_ueberschreibt_kein_gleichzeitiges_schreiben(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Speichert eine andere Anfrage während des Vorhaltens, bleibt ihr Inhalt."""

    kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 1})
    lesen_ohne_einschub = Path.read_text
    eingeschoben: bool = False

    def lesen_mit_einschub(pfad: Path, *args: Any, **kwargs: Any) -> str:
        # Die andere Anfrage schreibt, sobald das Vorhalten den Eintrag gelesen hat.
        nonlocal eingeschoben
        text: str = lesen_ohne_einschub(pfad, *args, **kwargs)
        if not eingeschoben:
            eingeschoben = True
            kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 2})
        return text

    with monkeypatch.context() as einschub:
        einschub.setattr(Path, "read_text", lesen_mit_einschub)
        kurzlebiger_speicher.vorhalten(_SCHLUESSEL)
    if not eingeschoben:
        # Liest das Vorhalten den Inhalt nicht, schreibt die Anfrage danach.
        kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 2})

    assert kurzlebiger_speicher.lesen(_SCHLUESSEL) == {"schritte": 2}


def test_misslungenes_schreiben_hinterlaesst_keine_datei(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scheitert das Ersetzen, liegt danach nichts Halbes im Verzeichnis."""

    def ersetzen_scheitert(*args: Any) -> None:
        raise OSError("Datenträger voll")

    monkeypatch.setattr(kurzlebiger_speicher.os, "replace", ersetzen_scheitert)

    with pytest.raises(OSError):
        kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 1})

    assert list(Path(settings.FLUECHTIG_PFAD).iterdir()) == []


def test_das_verzeichnis_ist_nur_fuer_den_dienst_lesbar() -> None:
    """Der Speicher legt sein Verzeichnis mit den Rechten 700 an."""

    kurzlebiger_speicher.schreiben(_SCHLUESSEL, {"schritte": 1})

    assert Path(settings.FLUECHTIG_PFAD).stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("schluessel", ["../geheim", "sitzung/1", "", "Sitzung-1"])
def test_ein_schluessel_fuehrt_nicht_aus_dem_verzeichnis(schluessel: str) -> None:
    """Nur Schlüssel aus Kleinbuchstaben, Ziffern und Bindestrich werden Dateinamen."""

    with pytest.raises(ValueError):
        kurzlebiger_speicher.schreiben(schluessel, {"schritte": 1})


def test_ein_unbekannter_schluessel_liefert_nichts() -> None:
    """Ein nie geschriebener Eintrag fehlt wie ein abgelaufener."""

    assert kurzlebiger_speicher.lesen(_SCHLUESSEL) is None

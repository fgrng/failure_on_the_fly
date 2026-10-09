"""Fake-Verzögerung, Anfragefrist und Verbrauch der Skripteinträge."""

from unittest.mock import patch

import pytest

from simulation import Ausfuehrung, ausgabe_versuchen
from simulation.models import ModellKonfiguration
from simulation.sprachmodell import LEHRPERSON_SCHEMA, Anbieterfehler, FakeSprachmodell


@pytest.mark.parametrize(
    ("verzoegerung", "abgelaufen"), [(2.0, False), (3.0, True), (4.0, True)]
)
def test_fake_begrenzt_seine_verzoegerung_auf_die_anfragefrist(
    verzoegerung: float, abgelaufen: bool
) -> None:
    fake = FakeSprachmodell([{"aeusserung": "Erste"}], verzoegerung)
    gewartet: list[float] = []

    with patch("time.sleep", gewartet.append):
        if abgelaufen:
            with pytest.raises(Anbieterfehler, match="Frist des Fake-Aufrufs"):
                fake.antworten("", "", [], "", LEHRPERSON_SCHEMA, timeout=3.0)
        else:
            assert fake.antworten("", "", [], "", LEHRPERSON_SCHEMA, timeout=3.0) == {
                "aeusserung": "Erste"
            }

    assert gewartet == ([2.0] if not abgelaufen else [3.0])


def test_timeout_verbraucht_den_skripteintrag() -> None:
    fake = FakeSprachmodell(
        [{"aeusserung": "Verworfen"}, {"aeusserung": "Zweite"}], 2.0
    )

    with patch("time.sleep"):
        with pytest.raises(Anbieterfehler):
            fake.antworten("", "", [], "", LEHRPERSON_SCHEMA, timeout=1.0)
        assert fake.antworten("", "", [], "", LEHRPERSON_SCHEMA, timeout=3.0) == {
            "aeusserung": "Zweite"
        }


def test_fake_timeout_nutzt_das_gemeinsame_budget_und_beginnt_naechsten_aufruf_frisch() -> (
    None
):
    konfiguration = ModellKonfiguration(
        sprachmodell="fake",
        parameter={
            "skript_fortlesen": True,
            "verzoegerung": 60,
            "skript": [
                {"fehler": "anbieterfehler", "rohantwort": "Erster Ausfall"},
                {"aeusserung": "Zu spät"},
                {"aeusserung": "Nächster Aufruf"},
            ],
        },
    )
    ausfuehrung = Ausfuehrung()
    vergangen = 0.0
    wartezeiten: list[float] = []

    def warten(sekunden: float) -> None:
        # Nur die Uhr verstreicht; der Test wartet keine echten 150 Sekunden.
        nonlocal vergangen
        vergangen += sekunden
        wartezeiten.append(sekunden)

    with patch("time.monotonic", lambda: vergangen), patch("time.sleep", warten):
        erster = ausgabe_versuchen(
            "", "", konfiguration, [], "", LEHRPERSON_SCHEMA, ausfuehrung
        )
        zweiter = ausgabe_versuchen(
            "", "", konfiguration, [], "", LEHRPERSON_SCHEMA, ausfuehrung
        )

    assert erster.ausgabe is None
    assert any("Frist des Fake-Aufrufs" in f.rohantwort for f in erster.fehlversuche)
    assert all(f.grund == "Anbieterfehler" for f in erster.fehlversuche)
    assert zweiter.ausgabe == {"aeusserung": "Nächster Aufruf"}
    assert wartezeiten == [60.0, 30.0, 60.0]

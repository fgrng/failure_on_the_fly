"""Transkription an ihrer austauschbaren Anbieter-Naht."""

from unittest.mock import Mock, patch

import httpx
import pytest
from django.test import override_settings
from openai import APIConnectionError

from simulation.transkription import (
    AnbieterNichtErreichbar,
    FakeTranskription,
    LeeresTranskript,
    TranskriptionsAnbieterfehler,
    OpenAITranskription,
)


def test_fake_transkription_liefert_das_naechste_skript_transkript() -> None:
    """Audio wird an der Naht in den vorgesehenen Text überführt."""

    transkription = FakeTranskription(["Wie hast du gerechnet?"])

    assert transkription.transkribieren(b"aufgenommene-audiobytes") == "Wie hast du gerechnet?"


@pytest.mark.parametrize(
    "fehler",
    [LeeresTranskript(), TranskriptionsAnbieterfehler(), AnbieterNichtErreichbar()],
)
def test_fake_transkription_spielt_jeden_fehlerzustand_ab(
    fehler: Exception,
) -> None:
    """Fehler bleiben für höhere Nähte unterscheidbar."""

    transkription = FakeTranskription([fehler])

    with pytest.raises(type(fehler)):
        transkription.transkribieren(b"aufgenommene-audiobytes")


@override_settings(TRANSKRIPTION_ZERO_RETENTION=False)
def test_openai_transkription_ohne_zero_retention_nicht_aufruft() -> None:
    """Ohne vertragliche Zusicherung verlässt kein Audio den Server."""

    with patch("simulation.transkription.OpenAI") as openai:
        with pytest.raises(TranskriptionsAnbieterfehler):
            OpenAITranskription().transkribieren(b"aufgenommene-audiobytes")

    openai.assert_not_called()


@override_settings(
    TRANSKRIPTION_ANBIETER="openai",
    TRANSKRIPTION_MODELL="gpt-4o-transcribe",
    TRANSKRIPTION_ZERO_RETENTION=True,
)
def test_openai_transkription_reicht_audio_ohne_sprache_an_konfiguriertes_modell() -> None:
    """OpenAI erkennt die Sprache selbst und der Adapter behält kein Audio."""

    audio = b"aufgenommene-audiobytes"
    client = Mock()
    client.audio.transcriptions.create.return_value.text = "Wie hast du gerechnet?"
    transkription = OpenAITranskription(client)

    assert transkription.transkribieren(audio) == "Wie hast du gerechnet?"
    client.audio.transcriptions.create.assert_called_once_with(
        model="gpt-4o-transcribe",
        file=("aufnahme.webm", audio, "audio/webm"),
    )
    assert audio not in vars(transkription).values()


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
@pytest.mark.parametrize(
    ("fehler", "erwarteter_fehler"),
    [
        (RuntimeError("Anbieterfehler"), TranskriptionsAnbieterfehler),
        (
            APIConnectionError(
                request=httpx.Request(
                    "POST", "https://api.openai.com/v1/audio/transcriptions"
                )
            ),
            AnbieterNichtErreichbar,
        ),
    ],
)
def test_openai_transkription_unterscheidet_anbieterfehler_und_nichterreichbarkeit(
    fehler: Exception, erwarteter_fehler: type[Exception]
) -> None:
    """Höhere Nähte können einen Ausfall anders behandeln als einen Anbieterfehler."""

    client = Mock()
    client.audio.transcriptions.create.side_effect = fehler

    with pytest.raises(erwarteter_fehler):
        OpenAITranskription(client).transkribieren(b"aufgenommene-audiobytes")


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
def test_openai_transkription_kennzeichnet_leere_antwort() -> None:
    """Ein leerer Anbietertext ist kein erfolgreicher Gesprächsbeitrag."""

    client = Mock()
    client.audio.transcriptions.create.return_value.text = "  "

    with pytest.raises(LeeresTranskript):
        OpenAITranskription(client).transkribieren(b"aufgenommene-audiobytes")


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
def test_openai_transkription_kennzeichnet_ungueltige_antwort_als_anbieterfehler() -> None:
    """Eine unerwartete Anbieternachricht bleibt kein technisches Detail der Naht."""

    client = Mock()
    client.audio.transcriptions.create.return_value = object()

    with pytest.raises(TranskriptionsAnbieterfehler):
        OpenAITranskription(client).transkribieren(b"aufgenommene-audiobytes")

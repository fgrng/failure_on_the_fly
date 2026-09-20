"""Transkription an ihrer austauschbaren Anbieter-Naht."""

from unittest.mock import Mock, patch

import httpx
import pytest
from openai import APIConnectionError

from simulation.models import TranskriptionsKonfiguration
from simulation.transkription import (
    PLATZHALTER_TRANSKRIPT,
    AnbieterNichtErreichbar,
    FakeTranskription,
    LeeresTranskript,
    OpenAITranskription,
    TranskriptionsAnbieterfehler,
    transkriptions_anbieter,
)


def test_fake_transkription_liefert_das_naechste_skript_transkript() -> None:
    """Audio wird an der Naht in den vorgesehenen Text überführt."""

    transkription = FakeTranskription(["Wie hast du gerechnet?"])

    assert (
        transkription.transkribieren(b"aufgenommene-audiobytes")
        == "Wie hast du gerechnet?"
    )


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


def _openai_transkription(client: Mock) -> OpenAITranskription:
    # Bildet den Adapter so, wie die Anbieterfunktion ihn bildet.

    return OpenAITranskription(client, modell="gpt-4o-transcribe", sprache="de")


def test_openai_transkription_reicht_audio_an_konfiguriertes_modell_und_sprache() -> (
    None
):
    """Modell und Sprache stehen am Aufruf, statt vom Anbieter geraten zu werden."""

    audio = b"aufgenommene-audiobytes"
    client = Mock()
    client.audio.transcriptions.create.return_value.text = "Wie hast du gerechnet?"

    assert _openai_transkription(client).transkribieren(audio) == (
        "Wie hast du gerechnet?"
    )
    client.audio.transcriptions.create.assert_called_once_with(
        model="gpt-4o-transcribe",
        language="de",
        file=("aufnahme.webm", audio, "audio/webm"),
    )


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
        _openai_transkription(client).transkribieren(b"aufgenommene-audiobytes")


def test_openai_transkription_kennzeichnet_leere_antwort() -> None:
    """Ein leerer Anbietertext ist kein erfolgreicher Gesprächsbeitrag."""

    client = Mock()
    client.audio.transcriptions.create.return_value.text = "  "

    with pytest.raises(LeeresTranskript):
        _openai_transkription(client).transkribieren(b"aufgenommene-audiobytes")


def test_openai_transkription_kennzeichnet_ungueltige_antwort_als_anbieterfehler() -> (
    None
):
    """Eine unerwartete Anbieternachricht bleibt kein technisches Detail der Naht."""

    client = Mock()
    client.audio.transcriptions.create.return_value = object()

    with pytest.raises(TranskriptionsAnbieterfehler):
        _openai_transkription(client).transkribieren(b"aufgenommene-audiobytes")


@pytest.mark.django_db
def test_anbieterfunktion_bildet_fuer_fake_einen_platzhalter_ohne_netz() -> None:
    """Der deterministische Adapter bekommt produktiv einen konstanten Text."""

    with patch("simulation.transkription.OpenAI") as openai:
        anbieter = transkriptions_anbieter()

    assert anbieter.transkribieren(b"aufgenommene-audiobytes") == (
        PLATZHALTER_TRANSKRIPT
    )
    openai.assert_not_called()


@pytest.mark.django_db
def test_anbieterfunktion_haelt_keinen_adapter_ueber_anfragen_hinweg() -> None:
    """Jede Anfrage bekommt einen frischen Adapter mit vollem Skript."""

    erster: FakeTranskription = transkriptions_anbieter()
    erster.transkribieren(b"aufgenommene-audiobytes")

    zweiter: FakeTranskription = transkriptions_anbieter()

    assert zweiter is not erster
    assert zweiter.transkribieren(b"aufgenommene-audiobytes") == PLATZHALTER_TRANSKRIPT


@pytest.mark.django_db
def test_anbieterfunktion_bildet_fuer_openrouter_den_client_aus_der_konfiguration() -> (
    None
):
    """Zugangsdaten und Endpunktwurzel kommen aus der Datenbank, nicht der Umgebung."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    konfiguration.anbieter = TranskriptionsKonfiguration.Anbieter.OPENROUTER
    konfiguration.anbieter_basis_url = "https://openrouter.ai/api/v1"
    konfiguration.anbieter_token = "geheimes-token"
    konfiguration.transkriptionsmodell = "whisper-large-v3"
    konfiguration.sprache = "fr"
    konfiguration.save()

    with patch("simulation.transkription.OpenAI") as openai:
        anbieter: OpenAITranskription = transkriptions_anbieter()

    openai.assert_called_once_with(
        base_url="https://openrouter.ai/api/v1",
        api_key="geheimes-token",
        timeout=120.0,
    )
    assert anbieter.client is openai.return_value
    assert anbieter.modell == "whisper-large-v3"
    assert anbieter.sprache == "fr"


@pytest.mark.django_db
def test_anbieterfunktion_kennt_infomaniak_noch_nicht() -> None:
    """Der asynchrone Adapter fehlt; die Naht sagt das, statt zu raten."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    konfiguration.anbieter = TranskriptionsKonfiguration.Anbieter.INFOMANIAK
    konfiguration.save()

    with pytest.raises(TranskriptionsAnbieterfehler):
        transkriptions_anbieter()

"""Transkription an ihrer austauschbaren Anbieter-Naht."""

import itertools
from unittest.mock import Mock, patch

import httpx
import pytest
from openai import APIConnectionError

from simulation.models import Anbieter, TranskriptionsKonfiguration
from simulation.transkription import (
    INFOMANIAK_INTERVALL_SEKUNDEN,
    PLATZHALTER_TRANSKRIPT,
    TRANSKRIPTION_BUDGET_SEKUNDEN,
    AnbieterNichtErreichbar,
    FakeTranskription,
    InfomaniakTranskription,
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
    konfiguration.anbieter = Anbieter.OPENROUTER
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
        timeout=TRANSKRIPTION_BUDGET_SEKUNDEN,
    )
    assert anbieter.client is openai.return_value
    assert anbieter.modell == "whisper-large-v3"
    assert anbieter.sprache == "fr"


def _antwort(nutzlast: object) -> Mock:
    # Bildet eine httpx-Antwort nach: JSON-Körper und ein Statuswächter.

    antwort = Mock()
    antwort.json.return_value = nutzlast
    antwort.raise_for_status.return_value = None
    return antwort


def _infomaniak_transkription(client: Mock) -> InfomaniakTranskription:
    # Bildet den Adapter so, wie die Anbieterfunktion ihn bildet.

    return InfomaniakTranskription(
        client,
        basis_url="https://api.infomaniak.com/1/ai/4711/openai",
        modell="whisper",
        sprache="de",
    )


def test_infomaniak_transkription_holt_das_ergebnis_nach_dem_absenden() -> None:
    """Absenden und Abholen ergeben zusammen ein Transkript, ohne Netzzugriff."""

    audio = b"aufgenommene-audiobytes"
    client = Mock()
    client.post.return_value = _antwort({"data": {"batch_id": "b-1"}})
    client.get.return_value = _antwort(
        {"data": {"status": "success", "data": "Wie hast du gerechnet?"}}
    )

    assert _infomaniak_transkription(client).transkribieren(audio) == (
        "Wie hast du gerechnet?"
    )
    client.post.assert_called_once_with(
        "https://api.infomaniak.com/1/ai/4711/openai/audio/transcriptions",
        data={"model": "whisper", "language": "de", "response_format": "text"},
        files={"file": ("aufnahme.webm", audio, "audio/webm")},
    )
    client.get.assert_called_once_with(
        "https://api.infomaniak.com/1/ai/4711/results/b-1"
    )


def test_infomaniak_transkription_endet_nach_dem_budget_statt_endlos_zu_fragen() -> (
    None
):
    """Ein nie fertig werdendes Ergebnis terminiert als Anbieterfehler."""

    client = Mock()
    client.post.return_value = _antwort({"data": {"batch_id": "b-1"}})
    client.get.return_value = _antwort({"data": {"status": "pending"}})
    # Die Uhr springt je Abfrage um das Intervall weiter; der Schlaf entfällt.
    uhr = itertools.count(0.0, INFOMANIAK_INTERVALL_SEKUNDEN)

    with (
        patch("simulation.transkription.time.sleep") as schlafen,
        patch("simulation.transkription.time.monotonic", lambda: next(uhr)),
        pytest.raises(TranskriptionsAnbieterfehler),
    ):
        _infomaniak_transkription(client).transkribieren(b"aufgenommene-audiobytes")

    erwartete_abfragen = int(
        TRANSKRIPTION_BUDGET_SEKUNDEN / INFOMANIAK_INTERVALL_SEKUNDEN
    )
    assert client.get.call_count == erwartete_abfragen
    schlafen.assert_called_with(INFOMANIAK_INTERVALL_SEKUNDEN)


def test_infomaniak_transkription_reicht_einen_gemeldeten_fehlschlag_weiter() -> None:
    """Ein gescheiterter Stapel ist ein Anbieterfehler, kein leeres Transkript."""

    client = Mock()
    client.post.return_value = _antwort({"data": {"batch_id": "b-1"}})
    client.get.return_value = _antwort({"data": {"status": "error"}})

    with pytest.raises(TranskriptionsAnbieterfehler):
        _infomaniak_transkription(client).transkribieren(b"aufgenommene-audiobytes")


def test_infomaniak_transkription_kennzeichnet_ein_leeres_ergebnis() -> None:
    """Ein fertiges, aber leeres Transkript bleibt vom Anbieterfehler unterscheidbar."""

    client = Mock()
    client.post.return_value = _antwort({"data": {"batch_id": "b-1"}})
    client.get.return_value = _antwort({"data": {"status": "success", "data": "  "}})

    with pytest.raises(LeeresTranskript):
        _infomaniak_transkription(client).transkribieren(b"aufgenommene-audiobytes")


def test_infomaniak_transkription_wartet_bei_einem_unlesbaren_stand_weiter() -> None:
    """Ein Stand, der keine Zeichenkette ist, läuft ins Budget statt zu brechen."""

    client = Mock()
    client.post.return_value = _antwort({"data": {"batch_id": "b-1"}})
    client.get.return_value = _antwort({"data": {"status": ["unbekannt"]}})
    uhr = itertools.count(0.0, INFOMANIAK_INTERVALL_SEKUNDEN)

    with (
        patch("simulation.transkription.time.sleep"),
        patch("simulation.transkription.time.monotonic", lambda: next(uhr)),
        pytest.raises(TranskriptionsAnbieterfehler),
    ):
        _infomaniak_transkription(client).transkribieren(b"aufgenommene-audiobytes")


def test_infomaniak_transkription_meldet_eine_unerreichbare_route() -> None:
    """Ein Transportfehler bleibt von einer Anbieterabsage unterscheidbar."""

    client = Mock()
    client.post.side_effect = httpx.ConnectError("keine Verbindung")

    with pytest.raises(AnbieterNichtErreichbar):
        _infomaniak_transkription(client).transkribieren(b"aufgenommene-audiobytes")


def test_infomaniak_transkription_meldet_eine_antwort_ohne_kennung() -> None:
    """Ohne Stapelkennung gibt es nichts abzuholen; das ist ein Anbieterfehler."""

    client = Mock()
    client.post.return_value = _antwort({"data": {}})

    with pytest.raises(TranskriptionsAnbieterfehler):
        _infomaniak_transkription(client).transkribieren(b"aufgenommene-audiobytes")


@pytest.mark.django_db
def test_anbieterfunktion_bildet_fuer_infomaniak_den_asynchronen_adapter() -> None:
    """Die Fabrik bildet den Polling-Adapter aus der Konfiguration."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    konfiguration.anbieter = Anbieter.INFOMANIAK
    konfiguration.anbieter_basis_url = "https://api.infomaniak.com/1/ai/4711/openai"
    konfiguration.anbieter_token = "geheimes-token"
    konfiguration.transkriptionsmodell = "whisper"
    konfiguration.sprache = "fr"
    konfiguration.save()

    with patch("simulation.transkription.httpx.Client") as httpx_client:
        anbieter: InfomaniakTranskription = transkriptions_anbieter()

    httpx_client.assert_called_once_with(
        headers={"Authorization": "Bearer geheimes-token"},
        timeout=TRANSKRIPTION_BUDGET_SEKUNDEN,
    )
    assert anbieter.client is httpx_client.return_value
    assert anbieter.basis_url == "https://api.infomaniak.com/1/ai/4711/openai"
    assert anbieter.modell == "whisper"
    assert anbieter.sprache == "fr"

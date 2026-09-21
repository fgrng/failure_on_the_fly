"""Das Modellverzeichnis an seiner austauschbaren Anbieter-Naht."""

from typing import Any
from unittest.mock import Mock

import httpx
import pytest

from simulation.models import Anbieter
from simulation.modellverzeichnis import (
    INFOMANIAK_MODELLE_URL,
    INFOMANIAK_PRODUKT_URL,
    OPENROUTER_MODELLE_URL,
    AnbieterAntwortetFormwidrig,
    AnbieterLehntAb,
    AnbieterNichtErreichbar,
    InfomaniakVerzeichnis,
    KeineModellliste,
    Modellvorschlag,
    Naht,
    OpenRouterVerzeichnis,
    modellverzeichnis,
)


def _client(nutzlast: Any) -> Mock:
    # Setzt einen Client ein, der die angegebene Nutzlast beantwortet.

    client = Mock()
    client.get.return_value.json.return_value = nutzlast
    return client


def _liste(*eintraege: dict[str, Any]) -> dict[str, Any]:
    # Baut die Antwortform, in der OpenRouter seine Modellliste führt.

    return {"data": list(eintraege)}


def test_openrouter_fragt_die_oeffentliche_liste_nach_structured_output() -> None:
    """Die Sprachmodell-Naht verlangt Structured Output (ADR-0005)."""

    client = _client(_liste())

    OpenRouterVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)

    client.get.assert_called_once_with(
        OPENROUTER_MODELLE_URL,
        params={"supported_parameters": "structured_outputs"},
    )


def test_openrouter_bildet_den_vorschlag_aus_id_und_klarnamen() -> None:
    """Der Wert trägt das Präfix des Anbieters, die Anzeige den Klarnamen."""

    client = _client(
        _liste({"id": "anthropic/claude-opus-4.8", "name": "Anthropic: Claude Opus"})
    )

    assert OpenRouterVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL) == [
        Modellvorschlag(
            wert="openrouter/anthropic/claude-opus-4.8",
            modellname="anthropic/claude-opus-4.8",
            anzeige="Anthropic: Claude Opus",
        )
    ]


def test_openrouter_zeigt_die_id_wenn_ein_klarname_fehlt() -> None:
    """Ohne Klarnamen bleibt der technische Name das Einzige, was anzuzeigen ist."""

    client = _client(_liste({"id": "openai/gpt-5"}))

    assert OpenRouterVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)[0].anzeige == (
        "openai/gpt-5"
    )


def test_openrouter_sortiert_alphabetisch_nach_der_anzeige() -> None:
    """Die Sortierung liegt vor der Oberfläche, nicht in ihr."""

    client = _client(
        _liste(
            {"id": "z/modell", "name": "Anthropic: Claude"},
            {"id": "a/modell", "name": "Zhipu: GLM"},
            {"id": "m/modell", "name": "mistral: Magistral"},
        )
    )

    vorschlaege: list[Modellvorschlag] = OpenRouterVerzeichnis(client).vorschlaege(
        Naht.SPRACHMODELL
    )

    assert [vorschlag.anzeige for vorschlag in vorschlaege] == [
        "Anthropic: Claude",
        "mistral: Magistral",
        "Zhipu: GLM",
    ]


def test_openrouter_fragt_die_transkriptionsmodelle_ueber_die_modalitaet() -> None:
    """Ohne den Modalitätsfilter erschiene kein einziges Transkriptionsmodell."""

    client = _client(_liste())

    OpenRouterVerzeichnis(client).vorschlaege(Naht.TRANSKRIPTION)

    client.get.assert_called_once_with(
        OPENROUTER_MODELLE_URL, params={"output_modalities": "transcription"}
    )


def test_openrouter_setzt_an_der_transkription_kein_praefix() -> None:
    """Diese Naht läuft nicht über LiteLLM; ein Präfix wäre ein unbekanntes Modell."""

    client = _client(
        _liste({"id": "openai/whisper-large-v3", "name": "OpenAI: Whisper Large v3"})
    )

    assert OpenRouterVerzeichnis(client).vorschlaege(Naht.TRANSKRIPTION) == [
        Modellvorschlag(
            wert="openai/whisper-large-v3",
            modellname="openai/whisper-large-v3",
            anzeige="OpenAI: Whisper Large v3",
        )
    ]


def test_openrouter_meldet_einen_nicht_erreichbaren_anbieter() -> None:
    """Ein Netzfehler wird benannt, nicht durchgereicht."""

    client = Mock()
    client.get.side_effect = httpx.ConnectError("kein Netz")

    with pytest.raises(AnbieterNichtErreichbar):
        OpenRouterVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)


def test_openrouter_meldet_einen_ablehnenden_anbieter() -> None:
    """Ein Fehlerstatus wird benannt, nicht durchgereicht."""

    client = Mock()
    client.get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429",
        request=httpx.Request("GET", OPENROUTER_MODELLE_URL),
        response=httpx.Response(429),
    )

    with pytest.raises(AnbieterLehntAb):
        OpenRouterVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)


@pytest.mark.parametrize(
    "nutzlast",
    [
        "keine Liste",
        {"data": "keine Liste"},
        _liste({"name": "Modell ohne Kennung"}),
        _liste({"id": 42}),
    ],
)
def test_openrouter_meldet_eine_formwidrige_antwort(nutzlast: Any) -> None:
    """Eine Antwort ohne brauchbare Modellnamen ist ein benannter Fehler."""

    with pytest.raises(AnbieterAntwortetFormwidrig):
        OpenRouterVerzeichnis(_client(nutzlast)).vorschlaege(Naht.SPRACHMODELL)


def test_openrouter_meldet_eine_naht_ohne_liste() -> None:
    """Eine Naht, für die es keine Abfrage gibt, scheitert vor dem Netzaufruf."""

    client = _client(_liste())

    with pytest.raises(KeineModellliste):
        OpenRouterVerzeichnis(client).vorschlaege("bildmodell")

    client.get.assert_not_called()


def test_fabrik_bildet_das_openrouter_verzeichnis_ohne_token() -> None:
    """OpenRouters Liste ist öffentlich: Das getippte Token bleibt im Formular."""

    verzeichnis: OpenRouterVerzeichnis = modellverzeichnis(
        Anbieter.OPENROUTER, "sk-or-v1-geheimnis"
    )

    assert isinstance(verzeichnis, OpenRouterVerzeichnis)
    assert "authorization" not in verzeichnis.client.headers


def test_fabrik_meldet_einen_anbieter_ohne_liste() -> None:
    """Der Anbieter »fake« führt keine Modelle, und das ist kein Serverfehler."""

    with pytest.raises(KeineModellliste):
        modellverzeichnis(Anbieter.FAKE, "")


def _infomaniak_liste(*eintraege: dict[str, Any]) -> dict[str, Any]:
    # Baut den v1-Umschlag, in dem Infomaniak seine kontoweite Liste führt.

    return {"result": "success", "data": list(eintraege)}


def _infomaniak_eintrag(name: str, typ: str = "llm", **felder: Any) -> dict[str, Any]:
    # Baut einen Eintrag, wie ihn »GET /1/ai/models« liefert.

    return {"id": 4711, "name": name, "type": typ, **felder}


def test_infomaniak_fragt_die_kontoweite_liste_ohne_produktkennung() -> None:
    """Die kontoweite Liste hängt allein am Token, nicht an der Basis-URL."""

    client = _client(_infomaniak_liste())

    InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)

    client.get.assert_called_once_with(INFOMANIAK_MODELLE_URL)


def test_infomaniak_bildet_den_vorschlag_aus_dem_modellnamen() -> None:
    """Modellname und Anzeige sind der Name; der Wert trägt das Präfix."""

    client = _client(
        _infomaniak_liste(_infomaniak_eintrag("swiss-ai/Apertus-v1.5-70B"))
    )

    assert InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL) == [
        Modellvorschlag(
            wert="openai/swiss-ai/Apertus-v1.5-70B",
            modellname="swiss-ai/Apertus-v1.5-70B",
            anzeige="swiss-ai/Apertus-v1.5-70B",
        )
    ]


def test_infomaniak_zeigt_nur_die_sprachmodelle() -> None:
    """Embedding-, Reranker-, Bild- und Transkriptionsmodelle sind keine Sprachmodelle."""

    client = _client(
        _infomaniak_liste(
            _infomaniak_eintrag("mistralai/Ministral-3-14B-Instruct-2512"),
            _infomaniak_eintrag("whisper", typ="stt"),
            _infomaniak_eintrag("bge-multilingual-gemma2", typ="embedding"),
            _infomaniak_eintrag("bge-reranker-v2-m3", typ="reranker"),
            _infomaniak_eintrag("flux", typ="image"),
        )
    )

    assert [
        vorschlag.modellname
        for vorschlag in InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)
    ] == ["mistralai/Ministral-3-14B-Instruct-2512"]


def test_infomaniak_traegt_die_numerische_kennung_in_keinem_feld() -> None:
    """Die »id« ist kein Modellname, und Modellnamen sind voller Ziffern."""

    client = _client(
        _infomaniak_liste(
            {"id": 4711, "name": "Qwen/Qwen3.5-122B-A10B-FP8", "type": "llm"}
        )
    )

    vorschlag: Modellvorschlag = InfomaniakVerzeichnis(client).vorschlaege(
        Naht.SPRACHMODELL
    )[0]

    assert "4711" not in (vorschlag.wert + vorschlag.modellname + vorschlag.anzeige)


def test_infomaniak_nimmt_noch_nicht_verfuegbare_modelle_auf() -> None:
    """Der Verfügbarkeitsstatus trügt: »coming_soon«-Modelle antworten."""

    client = _client(
        _infomaniak_liste(
            _infomaniak_eintrag("swiss-ai/Apertus-v1.5-70B", info_status="coming_soon")
        )
    )

    assert len(InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)) == 1


def test_infomaniak_nimmt_beta_modelle_ungekennzeichnet_auf() -> None:
    """Ein Kennzeichen, das nur ein Anbieter füllt, gehört nicht in die Vorschlagsform."""

    client = _client(
        _infomaniak_liste(
            _infomaniak_eintrag("moonshotai/Kimi-K2.6", meta={"is_beta": True})
        )
    )

    assert InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL) == [
        Modellvorschlag(
            wert="openai/moonshotai/Kimi-K2.6",
            modellname="moonshotai/Kimi-K2.6",
            anzeige="moonshotai/Kimi-K2.6",
        )
    ]


def test_infomaniak_sortiert_alphabetisch_nach_der_anzeige() -> None:
    """Die Sortierung liegt vor der Oberfläche, nicht in ihr."""

    client = _client(
        _infomaniak_liste(
            _infomaniak_eintrag("swiss-ai/Apertus-v1.5-70B"),
            _infomaniak_eintrag("google/gemma-4-31B-it"),
            _infomaniak_eintrag("Qwen/Qwen3.5-122B-A10B-FP8"),
        )
    )

    assert [
        vorschlag.anzeige
        for vorschlag in InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)
    ] == [
        "google/gemma-4-31B-it",
        "Qwen/Qwen3.5-122B-A10B-FP8",
        "swiss-ai/Apertus-v1.5-70B",
    ]


def test_infomaniak_zeigt_an_der_transkription_nur_das_stt_modell() -> None:
    """Kein Sprach-, Embedding-, Reranker- oder Bildmodell transkribiert."""

    client = _client(
        _infomaniak_liste(
            _infomaniak_eintrag("mistralai/Ministral-3-14B-Instruct-2512"),
            _infomaniak_eintrag("whisper", typ="stt"),
            _infomaniak_eintrag("bge-multilingual-gemma2", typ="embedding"),
            _infomaniak_eintrag("bge-reranker-v2-m3", typ="reranker"),
            _infomaniak_eintrag("flux", typ="image"),
        )
    )

    assert InfomaniakVerzeichnis(client).vorschlaege(Naht.TRANSKRIPTION) == [
        Modellvorschlag(wert="whisper", modellname="whisper", anzeige="whisper")
    ]


def test_infomaniak_meldet_ein_abgelehntes_token_verstaendlich() -> None:
    """Ein falsches Token wird mit »401« abgewiesen und benannt, nicht durchgereicht."""

    client = Mock()
    client.get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401",
        request=httpx.Request("GET", INFOMANIAK_MODELLE_URL),
        response=httpx.Response(401),
    )

    with pytest.raises(AnbieterLehntAb, match="Token"):
        InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)


def test_infomaniak_meldet_einen_nicht_erreichbaren_anbieter() -> None:
    """Ein Netzfehler wird benannt, nicht durchgereicht."""

    client = Mock()
    client.get.side_effect = httpx.ConnectError("kein Netz")

    with pytest.raises(AnbieterNichtErreichbar):
        InfomaniakVerzeichnis(client).vorschlaege(Naht.SPRACHMODELL)


@pytest.mark.parametrize(
    "nutzlast",
    [
        "keine Liste",
        {"result": "error", "error": {"code": "not_authorized"}},
        _infomaniak_liste(_infomaniak_eintrag("")),
        _infomaniak_liste({"id": 4711, "type": "llm"}),
    ],
)
def test_infomaniak_meldet_eine_formwidrige_antwort(nutzlast: Any) -> None:
    """Eine Antwort ohne brauchbare Modellnamen ist ein benannter Fehler."""

    with pytest.raises(AnbieterAntwortetFormwidrig):
        InfomaniakVerzeichnis(_client(nutzlast)).vorschlaege(Naht.SPRACHMODELL)


def test_infomaniak_meldet_eine_naht_ohne_liste() -> None:
    """Eine Naht, für die es keinen Modelltyp gibt, scheitert vor dem Netzaufruf."""

    client = _client(_infomaniak_liste())

    with pytest.raises(KeineModellliste):
        InfomaniakVerzeichnis(client).vorschlaege("bildmodell")

    client.get.assert_not_called()


def test_fabrik_bildet_das_infomaniak_verzeichnis_mit_dem_getippten_token() -> None:
    """Das getippte Feld ist die einzige Quelle: Es gibt keine gespeicherte Fassung."""

    verzeichnis: InfomaniakVerzeichnis = modellverzeichnis(
        Anbieter.INFOMANIAK, "ik-geheimnis"
    )

    assert isinstance(verzeichnis, InfomaniakVerzeichnis)
    assert verzeichnis.client.headers["authorization"] == "Bearer ik-geheimnis"


def _produktliste(*eintraege: dict[str, Any]) -> dict[str, Any]:
    # Baut die Antwortform, in der »GET /1/ai« die Produkte des Kontos führt.

    return {"result": "success", "data": list(eintraege)}


def _produkt(**felder: Any) -> dict[str, Any]:
    # Baut einen Produkteintrag, wie ihn die Produktabfrage liefert.

    return {
        "product_name": "Ai-Tools",
        "product_id": 314159,
        "account_name": "Frida Musterfrau",
        "status": "ok",
        **felder,
    }


def test_infomaniak_bildet_die_sprachmodell_wurzel_aus_der_produktkennung() -> None:
    """Die Wurzel des Sprachmodells liegt unter der zweiten API-Version."""

    client = _client(_produktliste(_produkt()))

    assert (
        InfomaniakVerzeichnis(client).basis_url(Naht.SPRACHMODELL)
        == "https://api.infomaniak.com/2/ai/314159/openai/v1"
    )
    client.get.assert_called_once_with(INFOMANIAK_PRODUKT_URL)


def test_infomaniak_bildet_die_transkriptions_wurzel_unter_eigener_gestalt() -> None:
    """Dieselbe Kennung, andere API-Version und anderer Pfadrest."""

    client = _client(_produktliste(_produkt()))

    assert (
        InfomaniakVerzeichnis(client).basis_url(Naht.TRANSKRIPTION)
        == "https://api.infomaniak.com/1/ai/314159/openai"
    )


def test_infomaniak_leitet_bei_mehreren_produkten_keine_wurzel_ab() -> None:
    """Ein geratenes Produkt wäre schlimmer als ein leeres Feld."""

    client = _client(_produktliste(_produkt(), _produkt(product_id=271828)))

    assert InfomaniakVerzeichnis(client).basis_url(Naht.SPRACHMODELL) == ""


def test_infomaniak_leitet_ohne_produkt_keine_wurzel_ab() -> None:
    """Ohne Produkt gibt es keine Kennung, aus der sich etwas bilden ließe."""

    client = _client(_produktliste())

    assert InfomaniakVerzeichnis(client).basis_url(Naht.SPRACHMODELL) == ""


def test_infomaniak_leitet_ohne_kennung_keine_wurzel_ab() -> None:
    """Ein Produkteintrag ohne Kennung lässt das Feld unangetastet."""

    client = _client(_produktliste({"product_name": "Ai-Tools", "status": "ok"}))

    assert InfomaniakVerzeichnis(client).basis_url(Naht.SPRACHMODELL) == ""


def test_infomaniak_traegt_den_kontoklarnamen_nicht_in_die_wurzel() -> None:
    """Der Klarname steht neben der Kennung und darf keine Oberfläche erreichen."""

    client = _client(_produktliste(_produkt()))

    assert "Frida" not in InfomaniakVerzeichnis(client).basis_url(Naht.SPRACHMODELL)


def test_infomaniak_meldet_eine_abgelehnte_produktabfrage() -> None:
    """Auch diese Abfrage hängt am Token und benennt ihre Ablehnung."""

    client = Mock()
    client.get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401",
        request=httpx.Request("GET", INFOMANIAK_PRODUKT_URL),
        response=httpx.Response(401),
    )

    with pytest.raises(AnbieterLehntAb, match="Token"):
        InfomaniakVerzeichnis(client).basis_url(Naht.SPRACHMODELL)


def test_infomaniak_leitet_fuer_eine_naht_ohne_gestalt_nichts_ab() -> None:
    """Ohne bekannte Gestalt gibt es keine Wurzel und keinen Netzaufruf."""

    client = _client(_produktliste(_produkt()))

    assert InfomaniakVerzeichnis(client).basis_url("bildmodell") == ""

    client.get.assert_not_called()


def test_openrouter_leitet_keine_wurzel_ab() -> None:
    """Dort ist die Basis-URL optional und hat eine Vorgabe am Anbieterprofil."""

    client = _client(_liste())

    assert OpenRouterVerzeichnis(client).basis_url(Naht.SPRACHMODELL) == ""

    client.get.assert_not_called()

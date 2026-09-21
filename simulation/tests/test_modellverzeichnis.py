"""Das Modellverzeichnis an seiner austauschbaren Anbieter-Naht."""

from typing import Any
from unittest.mock import Mock

import httpx
import pytest

from simulation.models import Anbieter
from simulation.modellverzeichnis import (
    OPENROUTER_MODELLE_URL,
    AnbieterAntwortetFormwidrig,
    AnbieterLehntAb,
    AnbieterNichtErreichbar,
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
        OpenRouterVerzeichnis(client).vorschlaege("transkription")

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

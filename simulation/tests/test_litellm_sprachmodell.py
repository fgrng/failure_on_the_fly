"""Strukturelle Tests des echten LiteLLM-Adapters ohne Netz."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from litellm import ContentPolicyViolationError

from simulation import antwort_versuchen
from simulation.models import Anbieter, ModellKonfiguration, Simulationskern
from simulation.sprachmodell import (
    AUSGABE_SCHEMA,
    Antwort,
    ContentFilter,
    Formatbruch,
    LiteLLMSprachmodell,
)
from vignetten.models import Vignette


def test_litellm_adapter_reicht_konfiguration_und_schema_durch() -> None:
    """Der Modell-String routet LiteLLM, ohne dass ein Anbieterzweig entsteht."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}'
                    )
                )
            ]
        )
    )

    antwort = LiteLLMSprachmodell(
        "anthropic/claude-opus-4-8", {"temperature": 0.2}, completion
    ).antworten("System", "Kontext", [], "Eingabe", AUSGABE_SCHEMA)

    assert antwort.denkspur == "Ich addiere."
    assert antwort.aeusserung == "2/5."
    completion.assert_called_once_with(
        model="anthropic/claude-opus-4-8",
        messages=[
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Kontext"},
            {"role": "user", "content": "Eingabe"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "simulation_antwort",
                "schema": AUSGABE_SCHEMA,
                "strict": True,
            },
        },
        temperature=0.2,
    )


def test_litellm_adapter_uebergibt_den_verlauf_als_konversationsnachrichten() -> None:
    """Beide Gesprächsseiten reisen als native Rollen, nicht als Prompt-Anhang."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}'
                    )
                )
            ]
        )
    )

    LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
        "System",
        "Kontext",
        [
            ("Wie rechnest du?", "Ich addiere alles."),
            ("Und warum so?", "Weil es so passt."),
        ],
        "Stimmt das denn?",
        AUSGABE_SCHEMA,
    )

    assert completion.call_args.kwargs["messages"] == [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Kontext"},
        {"role": "user", "content": "Wie rechnest du?"},
        {"role": "assistant", "content": "Ich addiere alles."},
        {"role": "user", "content": "Und warum so?"},
        {"role": "assistant", "content": "Weil es so passt."},
        {"role": "user", "content": "Stimmt das denn?"},
    ]


@pytest.mark.parametrize("feldname", ["reasoning_content", "thinking"])
def test_litellm_adapter_uebergeht_native_reasoning_felder(feldname: str) -> None:
    """Native Reasoning-Felder des Anbieters bleiben folgenlos: Sie werden nicht gelesen."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}',
                        **{feldname: "native Reasoning-Spur"},
                    )
                )
            ]
        )
    )

    antwort = LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
        "System", "Kontext", [], "Eingabe", AUSGABE_SCHEMA
    )

    assert antwort == Antwort(denkspur="Ich addiere.", aeusserung="2/5.")


def test_antwort_versuchen_bildet_litellm_adapter_aus_modell_konfiguration() -> None:
    """Jeder LiteLLM-Modell-String wird ohne einen Anbieterzweig weitergereicht."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}'
                    )
                )
            ]
        )
    )

    with patch("simulation.sprachmodell.litellm.completion", completion):
        antwortversuch = antwort_versuchen(
            Vignette(lernauftrag_text="Addiere zwei Brüche."),
            Simulationskern(user_prompt_vorlage="$lernauftrag"),
            ModellKonfiguration(
                anbieter=Anbieter.OPENROUTER,
                sprachmodell="openrouter/openai/gpt-test",
                anbieter_token="sk-or-geheim",
                parameter={"max_tokens": 100},
            ),
            verlauf=[],
            eingabe="Wie hast du gerechnet?",
        )

    assert antwortversuch.antwort is not None
    assert completion.call_args.kwargs["model"] == "openrouter/openai/gpt-test"
    assert completion.call_args.kwargs["max_tokens"] == 100


def test_litellm_adapter_kennzeichnet_content_filter() -> None:
    """Eine gefilterte LiteLLM-Antwort bleibt ein Filter, kein Anbieterfehler."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="content_filter",
                    message=SimpleNamespace(content="Gefilterte Rohantwort"),
                )
            ]
        )
    )

    with pytest.raises(ContentFilter) as exc_info:
        LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
            "System", "Kontext", [], "Eingabe", AUSGABE_SCHEMA
        )

    assert exc_info.value.rohantwort == "Gefilterte Rohantwort"


def test_litellm_adapter_kennzeichnet_content_policy_exception_als_filter() -> None:
    """Auch ein von LiteLLM ausgelöster Inhaltsfilter bleibt unterscheidbar."""

    completion = Mock(
        side_effect=ContentPolicyViolationError(
            "Gefiltert", model="gpt-test", llm_provider="openai"
        )
    )

    with pytest.raises(ContentFilter):
        LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
            "System", "Kontext", [], "Eingabe", AUSGABE_SCHEMA
        )


def test_litellm_adapter_kennzeichnet_fehlende_antworthuelle_als_formatbruch() -> None:
    """Eine unvollständige LiteLLM-Antwort wird vom Simulationskern wiederholt."""

    completion = Mock(return_value=SimpleNamespace(choices=[]))

    with pytest.raises(Formatbruch):
        LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
            "System", "Kontext", [], "Eingabe", AUSGABE_SCHEMA
        )


def test_litellm_adapter_kennzeichnet_zusaetzliches_feld_als_formatbruch() -> None:
    """Die gelieferte Antwort muss vollständig dem festen Schema entsprechen."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"denkspur": "Ich addiere.", "aeusserung": "2/5.", '
                            '"extra": true}'
                        )
                    )
                )
            ]
        )
    )

    with pytest.raises(Formatbruch):
        LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
            "System", "Kontext", [], "Eingabe", AUSGABE_SCHEMA
        )


def _geglueckte_completion() -> Mock:
    # Liefert eine schemakonforme Modellantwort, ohne das Netz zu berühren.

    return Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}'
                    )
                )
            ]
        )
    )


def test_antwort_versuchen_reicht_token_und_basis_url_an_den_aufruf_durch() -> None:
    """Die Zugangsdaten kommen aus den Feldern, nicht aus der Umgebung."""

    completion: Mock = _geglueckte_completion()

    with patch("simulation.sprachmodell.litellm.completion", completion):
        antwort_versuchen(
            Vignette(lernauftrag_text="Addiere zwei Brüche."),
            Simulationskern(user_prompt_vorlage="$lernauftrag"),
            ModellKonfiguration(
                anbieter=Anbieter.INFOMANIAK,
                sprachmodell="openai/mistral24b",
                anbieter_basis_url="https://api.infomaniak.com/1/ai/4711/openai",
                anbieter_token="infomaniak-geheim",
            ),
            verlauf=[],
            eingabe="Wie hast du gerechnet?",
        )

    assert completion.call_args.kwargs["api_key"] == "infomaniak-geheim"
    assert completion.call_args.kwargs["api_base"] == (
        "https://api.infomaniak.com/1/ai/4711/openai"
    )


def test_antwort_versuchen_setzt_den_provider_filter_bei_openrouter() -> None:
    """Die datenschutzrechtliche Zusage steht in keiner Konfiguration."""

    completion: Mock = _geglueckte_completion()

    with patch("simulation.sprachmodell.litellm.completion", completion):
        antwort_versuchen(
            Vignette(lernauftrag_text="Addiere zwei Brüche."),
            Simulationskern(user_prompt_vorlage="$lernauftrag"),
            ModellKonfiguration(
                anbieter=Anbieter.OPENROUTER,
                sprachmodell="openrouter/anthropic/claude-opus-4-8",
                anbieter_token="sk-or-geheim",
            ),
            verlauf=[],
            eingabe="Wie hast du gerechnet?",
        )

    assert completion.call_args.kwargs["extra_body"] == {
        "provider": {
            "require_parameters": True,
            "data_collection": "deny",
            "zdr": True,
        }
    }


def test_antwort_versuchen_waehlt_den_fake_adapter_ueber_das_anbieterfeld() -> None:
    """Der deterministische Adapter hängt am Feld, nicht am Modellnamen."""

    completion: Mock = _geglueckte_completion()

    with patch("simulation.sprachmodell.litellm.completion", completion):
        antwortversuch = antwort_versuchen(
            Vignette(lernauftrag_text="Addiere zwei Brüche."),
            Simulationskern(user_prompt_vorlage="$lernauftrag"),
            ModellKonfiguration(
                anbieter=Anbieter.FAKE,
                sprachmodell="fake",
                parameter={
                    "skript": [{"denkspur": "Ich addiere.", "aeusserung": "2/5."}]
                },
            ),
            verlauf=[],
            eingabe="Wie hast du gerechnet?",
        )

    assert antwortversuch.antwort is not None
    completion.assert_not_called()

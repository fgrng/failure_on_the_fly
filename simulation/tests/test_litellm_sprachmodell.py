"""Strukturelle Tests des echten LiteLLM-Adapters ohne Netz."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from litellm import ContentPolicyViolationError

from simulation import antwort_versuchen
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.sprachmodell import (
    AUSGABE_SCHEMA,
    ContentFilter,
    Formatbruch,
    LiteLLMSprachmodell,
)
from vignetten.models import Vignette


def test_litellm_adapter_reicht_konfiguration_schema_und_native_reasoning_spur_durch(
) -> None:
    """Der Modell-String routet LiteLLM, ohne dass ein Anbieterzweig entsteht."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}',
                        reasoning_content="native Reasoning-Spur",
                    )
                )
            ]
        )
    )

    antwort, native_reasoning_spur = LiteLLMSprachmodell(
        "anthropic/claude-opus-4-8", {"temperature": 0.2}, completion
    ).antworten("System", "Eingabe", AUSGABE_SCHEMA)

    assert antwort.denkspur == "Ich addiere."
    assert antwort.aeusserung == "2/5."
    assert native_reasoning_spur == "native Reasoning-Spur"
    completion.assert_called_once_with(
        model="anthropic/claude-opus-4-8",
        messages=[
            {"role": "system", "content": "System"},
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


def test_litellm_adapter_zieht_native_reasoning_spur_aus_thinking() -> None:
    """Auch eine als `thinking` gelieferte native Reasoning-Spur wird erkannt."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}',
                        reasoning_content=None,
                        thinking="native Reasoning-Spur",
                    )
                )
            ]
        )
    )

    _, native_reasoning_spur = LiteLLMSprachmodell(
        "openai/gpt-test", {}, completion
    ).antworten("System", "Eingabe", AUSGABE_SCHEMA)

    assert native_reasoning_spur == "native Reasoning-Spur"


def test_antwort_versuchen_bildet_litellm_adapter_aus_modell_konfiguration() -> None:
    """Jeder LiteLLM-Modell-String wird ohne einen Anbieterzweig weitergereicht."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"denkspur": "Ich addiere.", "aeusserung": "2/5."}',
                        reasoning_content="native Reasoning-Spur",
                    )
                )
            ]
        )
    )

    with patch("simulation.sprachmodell.litellm.completion", completion):
        antwortversuch = antwort_versuchen(
            Vignette(lernauftrag="Addiere zwei Brüche."),
            Simulationskern(user_prompt_vorlage="$lernauftrag"),
            ModellKonfiguration(
                sprachmodell="openai/gpt-test", parameter={"max_tokens": 100}
            ),
            verlauf=[],
            eingabe="Wie hast du gerechnet?",
        )

    assert antwortversuch.antwort is not None
    assert antwortversuch.native_reasoning_spur == "native Reasoning-Spur"
    assert completion.call_args.kwargs["model"] == "openai/gpt-test"
    assert completion.call_args.kwargs["max_tokens"] == 100


def test_litellm_adapter_kennzeichnet_content_filter() -> None:
    """Eine gefilterte LiteLLM-Antwort bleibt ein Filter, kein Anbieterfehler."""

    completion = Mock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(finish_reason="content_filter")]
        )
    )

    with pytest.raises(ContentFilter):
        LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
            "System", "Eingabe", AUSGABE_SCHEMA
        )


def test_litellm_adapter_kennzeichnet_content_policy_exception_als_filter() -> None:
    """Auch ein von LiteLLM ausgelöster Inhaltsfilter bleibt unterscheidbar."""

    completion = Mock(
        side_effect=ContentPolicyViolationError(
            "Gefiltert", model="gpt-test", llm_provider="openai"
        )
    )

    with pytest.raises(ContentFilter):
        LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
            "System", "Eingabe", AUSGABE_SCHEMA
        )


def test_litellm_adapter_kennzeichnet_fehlende_antworthuelle_als_formatbruch() -> None:
    """Eine unvollständige LiteLLM-Antwort wird vom Simulationskern wiederholt."""

    completion = Mock(return_value=SimpleNamespace(choices=[]))

    with pytest.raises(Formatbruch):
        LiteLLMSprachmodell("openai/gpt-test", {}, completion).antworten(
            "System", "Eingabe", AUSGABE_SCHEMA
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
            "System", "Eingabe", AUSGABE_SCHEMA
        )

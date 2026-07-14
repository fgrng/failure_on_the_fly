"""Naht zum Sprachmodell und ihr deterministischer Testadapter."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import litellm


AUSGABE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "denkspur": {"type": "string"},
        "aeusserung": {"type": "string"},
    },
    "required": ["denkspur", "aeusserung"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Antwort:
    """Das strukturierte Ergebnis eines geglückten Modellaufrufs."""

    denkspur: str
    aeusserung: str


class Formatbruch(Exception):
    """Die strukturierte Ausgabe des Sprachmodells ist ungültig."""

    def __init__(self, rohantwort: str = "") -> None:
        self.rohantwort: str = rohantwort


class Anbieterfehler(Exception):
    """Der Anbieter konnte keine Modellantwort liefern."""

    def __init__(self, rohantwort: str = "") -> None:
        self.rohantwort: str = rohantwort


class ContentFilter(Exception):
    """Der Anbieter hat die Modellantwort gefiltert."""

    def __init__(self, rohantwort: str = "") -> None:
        self.rohantwort: str = rohantwort


class Sprachmodell(Protocol):
    """Die einzige austauschbare Naht des Simulationskerns."""

    def antworten(
        self,
        system_prompt: str,
        user_prompt: str,
        ausgabe_schema: Mapping[str, object],
    ) -> tuple[Antwort, str | None]:
        """Liefert eine strukturierte Antwort und optionale native Reasoning-Spur."""


class FakeSprachmodell:
    """Spielt konfigurierte Antworten und maschinelle Fehler deterministisch ab."""

    letzte_anfragen: list[tuple[str, str, Mapping[str, object]]] = []

    def __init__(self, skript: Sequence[Mapping[str, Any]]) -> None:
        self.skript: list[Mapping[str, Any]] = list(skript)

    def antworten(
        self,
        system_prompt: str,
        user_prompt: str,
        ausgabe_schema: Mapping[str, object],
    ) -> tuple[Antwort, str | None]:
        """Verbraucht genau einen Eintrag des Fake-Skripts."""

        type(self).letzte_anfragen.append((system_prompt, user_prompt, ausgabe_schema))
        eintrag: Mapping[str, Any] = self.skript.pop(0)
        if (fehler := eintrag.get("fehler")) == "formatbruch":
            raise Formatbruch(str(eintrag.get("rohantwort", "")))
        if fehler == "anbieterfehler":
            raise Anbieterfehler(str(eintrag.get("rohantwort", "")))
        if fehler == "content_filter":
            raise ContentFilter(str(eintrag.get("rohantwort", "")))
        try:
            antwort: Antwort = Antwort(
                denkspur=eintrag["denkspur"],
                aeusserung=eintrag["aeusserung"],
            )
        except KeyError as exc:
            raise Formatbruch(str(eintrag.get("rohantwort", ""))) from exc
        if not isinstance(antwort.denkspur, str) or not isinstance(antwort.aeusserung, str):
            raise Formatbruch(str(eintrag.get("rohantwort", "")))
        native_reasoning_spur: object = eintrag.get("native_reasoning_spur")
        if native_reasoning_spur is not None and not isinstance(
            native_reasoning_spur, str
        ):
            raise Formatbruch(str(eintrag.get("rohantwort", "")))
        return antwort, native_reasoning_spur


class LiteLLMSprachmodell:
    """Routet den konfigurierten Modell-String über LiteLLM."""

    def __init__(
        self,
        modell: str,
        parameter: Mapping[str, Any],
        completion: Callable[..., Any] | None = None,
    ) -> None:
        self.modell: str = modell
        self.parameter: dict[str, Any] = dict(parameter)
        self.completion: Callable[..., Any] = completion or litellm.completion

    def antworten(
        self,
        system_prompt: str,
        user_prompt: str,
        ausgabe_schema: Mapping[str, object],
    ) -> tuple[Antwort, str | None]:
        """Fordert eine JSON-Ausgabe an und trennt die native Reasoning-Spur ab."""

        try:
            modellantwort = self.completion(
                model=self.modell,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "simulation_antwort",
                        "schema": ausgabe_schema,
                        "strict": True,
                    },
                },
                **self.parameter,
            )
        except litellm.ContentPolicyViolationError as exc:
            raise ContentFilter from exc
        except Exception as exc:
            raise Anbieterfehler from exc

        rohantwort: str = ""
        try:
            auswahl: Any = modellantwort.choices[0]
            nachricht: Any = getattr(auswahl, "message", None)
            rohantwort = str(getattr(nachricht, "content", ""))
            if getattr(auswahl, "finish_reason", None) == "content_filter":
                raise ContentFilter(rohantwort)
            inhalt: object = json.loads(rohantwort)
            if not isinstance(inhalt, dict) or set(inhalt) != {
                "denkspur",
                "aeusserung",
            }:
                raise Formatbruch(rohantwort)
            antwort: Antwort = Antwort(
                denkspur=inhalt["denkspur"], aeusserung=inhalt["aeusserung"]
            )
        except ContentFilter:
            raise
        except (AttributeError, IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise Formatbruch(rohantwort) from exc
        if not isinstance(antwort.denkspur, str) or not isinstance(antwort.aeusserung, str):
            raise Formatbruch(rohantwort)

        native_reasoning_spur: object = getattr(nachricht, "reasoning_content", None)
        if native_reasoning_spur is None:
            native_reasoning_spur = getattr(nachricht, "thinking", None)
        if native_reasoning_spur is not None and not isinstance(native_reasoning_spur, str):
            raise Formatbruch(rohantwort)
        return antwort, native_reasoning_spur

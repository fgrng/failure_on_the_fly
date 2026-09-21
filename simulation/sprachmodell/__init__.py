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


def nachrichten_bauen(
    system_prompt: str,
    user_prompt: str,
    verlauf: Sequence[tuple[str, str]],
    eingabe: str,
) -> list[dict[str, str]]:
    """Baut den Gesprächsverlauf als native Konversationsnachrichten.

    Die Rolle und der Arbeitskontext stehen einmal am Anfang; danach wechseln
    sich Eingaben der Teilnehmer:in und sichtbare Äußerungen der simulierten
    Schüler:in ab. Die Denkspur erreicht keinen Eintrag (ADR-0005).
    """

    nachrichten: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    for frage, aeusserung in verlauf:
        nachrichten.append({"role": "user", "content": frage})
        nachrichten.append({"role": "assistant", "content": aeusserung})
    nachrichten.append({"role": "user", "content": eingabe})
    return nachrichten


@dataclass(frozen=True)
class Antwort:
    """Das strukturierte Ergebnis eines geglückten Modellaufrufs."""

    denkspur: str
    aeusserung: str


class _Modellantwortfehler(Exception):
    """Ein verworfener Modellaufruf mit seiner Rohantwort."""

    def __init__(self, rohantwort: str = "") -> None:
        self.rohantwort: str = rohantwort


class Formatbruch(_Modellantwortfehler):
    """Die strukturierte Ausgabe des Sprachmodells ist ungültig."""


class Anbieterfehler(_Modellantwortfehler):
    """Der Anbieter konnte keine Modellantwort liefern."""


class ContentFilter(_Modellantwortfehler):
    """Der Anbieter hat die Modellantwort gefiltert."""


class Sprachmodell(Protocol):
    """Die einzige austauschbare Naht des Simulationskerns."""

    def antworten(
        self,
        system_prompt: str,
        user_prompt: str,
        verlauf: Sequence[tuple[str, str]],
        eingabe: str,
        ausgabe_schema: Mapping[str, object],
        timeout: float,
    ) -> Antwort:
        """Liefert die geparste Antwort: Nichts reist am Ausgabeschema vorbei.

        `timeout` ist die Restzeit der Frist, die sich alle Versuche eines
        Gesprächsschritts teilen; der Aufrufer rechnet sie aus.
        """


class FakeSprachmodell:
    """Spielt konfigurierte Antworten und maschinelle Fehler deterministisch ab."""

    letzte_anfragen: list[tuple[list[dict[str, str]], Mapping[str, object]]] = []

    def __init__(self, skript: Sequence[Mapping[str, Any]]) -> None:
        self.skript: list[Mapping[str, Any]] = list(skript)

    def antworten(
        self,
        system_prompt: str,
        user_prompt: str,
        verlauf: Sequence[tuple[str, str]],
        eingabe: str,
        ausgabe_schema: Mapping[str, object],
        timeout: float,
    ) -> Antwort:
        """Verbraucht genau einen Eintrag des Fake-Skripts.

        Der Fake antwortet sofort; `timeout` bleibt hier ohne Wirkung.
        """

        type(self).letzte_anfragen.append(
            (
                nachrichten_bauen(system_prompt, user_prompt, verlauf, eingabe),
                ausgabe_schema,
            )
        )
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
        if not isinstance(antwort.denkspur, str) or not isinstance(
            antwort.aeusserung, str
        ):
            raise Formatbruch(str(eintrag.get("rohantwort", "")))
        return antwort


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
        verlauf: Sequence[tuple[str, str]],
        eingabe: str,
        ausgabe_schema: Mapping[str, object],
        timeout: float,
    ) -> Antwort:
        """Fordert eine JSON-Ausgabe an und gibt allein die geparste Antwort zurück."""

        # Die Frist ist eine Zusage dieser Naht: `timeout` steht nicht in der
        # Allowlist der Mikro-Stellschrauben und überschreibt einen dort
        # dennoch gelandeten Wert.
        aufrufparameter: dict[str, Any] = {**self.parameter, "timeout": timeout}

        try:
            modellantwort = self.completion(
                model=self.modell,
                messages=nachrichten_bauen(
                    system_prompt, user_prompt, verlauf, eingabe
                ),
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "simulation_antwort",
                        "schema": ausgabe_schema,
                        "strict": True,
                    },
                },
                **aufrufparameter,
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
        except (
            AttributeError,
            IndexError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            raise Formatbruch(rohantwort) from exc
        if not isinstance(antwort.denkspur, str) or not isinstance(
            antwort.aeusserung, str
        ):
            raise Formatbruch(rohantwort)
        return antwort

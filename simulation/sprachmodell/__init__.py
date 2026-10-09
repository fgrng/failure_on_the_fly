"""Naht zum Sprachmodell und ihr deterministischer Testadapter."""

import json
import time
from collections.abc import Mapping, Sequence
from typing import Any, Callable, Protocol

import litellm


SCHUELERIN_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "denkspur": {"type": "string"},
        "aeusserung": {"type": "string"},
    },
    "required": ["denkspur", "aeusserung"],
    "additionalProperties": False,
}

LEHRPERSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"aeusserung": {"type": "string"}},
    "required": ["aeusserung"],
    "additionalProperties": False,
}

# Die Begründung steht vor dem Urteil, damit das Modell erst abwägt und dann
# entscheidet — wie die Denkspur vor der Äußerung (ADR-0005).
BEWERTER_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "begruendung": {"type": "string"},
        "erfuellt": {"type": "boolean"},
    },
    "required": ["begruendung", "erfuellt"],
    "additionalProperties": False,
}

# Die JSON-Typen, die in den Ausgabeschemas vorkommen.
_JSON_TYPEN: dict[str, type] = {"string": str, "boolean": bool}


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


def _ausgabe_pruefen(
    inhalt: object, ausgabe_schema: Mapping[str, Any], rohantwort: str
) -> dict[str, object]:
    """Gibt den Inhalt zurück, wenn er genau dem Ausgabeschema entspricht.

    Fehlende, zusätzliche oder falsch typisierte Felder sind ein Formatbruch.
    """

    eigenschaften: Mapping[str, Mapping[str, str]] = ausgabe_schema["properties"]
    if not isinstance(inhalt, dict) or set(inhalt) != set(eigenschaften):
        raise Formatbruch(rohantwort)
    for name, eigenschaft in eigenschaften.items():
        if not isinstance(inhalt[name], _JSON_TYPEN[eigenschaft["type"]]):
            raise Formatbruch(rohantwort)
    return inhalt


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
    ) -> dict[str, object]:
        """Liefert das geparste Objekt des Schemas: Nichts reist an ihm vorbei.

        `timeout` ist die Restzeit der Frist, die sich alle Versuche eines
        Gesprächsschritts teilen; der Aufrufer rechnet sie aus.
        """


class FakeSprachmodell:
    """Spielt konfigurierte Antworten und maschinelle Fehler deterministisch ab."""

    def __init__(
        self, skript: Sequence[Mapping[str, Any]], verzoegerung: float = 0.0
    ) -> None:
        """Übernimmt das Skript, dessen Einträge der Reihe nach verbraucht werden.

        `verzoegerung` lässt jeden Aufruf so viele Sekunden warten, wie ein
        langsames Modell, etwa um einen Prozessneustart mitten im Evallauf
        durchzuspielen.
        """

        self.skript: list[Mapping[str, Any]] = list(skript)
        self.verzoegerung: float = verzoegerung

    def antworten(
        self,
        system_prompt: str,
        user_prompt: str,
        verlauf: Sequence[tuple[str, str]],
        eingabe: str,
        ausgabe_schema: Mapping[str, object],
        timeout: float,
    ) -> dict[str, object]:
        """Verbraucht genau einen Eintrag des Fake-Skripts.

        Der Fake antwortet nach seiner Verzögerung; `timeout` bleibt hier
        ohne Wirkung.
        """

        if self.verzoegerung:
            time.sleep(self.verzoegerung)
        eintrag: Mapping[str, Any] = self.skript.pop(0)
        rohantwort: str = str(eintrag.get("rohantwort", ""))
        if (fehler := eintrag.get("fehler")) == "formatbruch":
            raise Formatbruch(rohantwort)
        if fehler == "anbieterfehler":
            raise Anbieterfehler(rohantwort)
        if fehler == "content_filter":
            raise ContentFilter(rohantwort)
        inhalt: dict[str, object] = {
            name: wert for name, wert in eintrag.items() if name != "rohantwort"
        }
        return _ausgabe_pruefen(inhalt, ausgabe_schema, rohantwort)


class LiteLLMSprachmodell:
    """Routet den konfigurierten Modell-String über LiteLLM."""

    def __init__(
        self,
        modell: str,
        parameter: Mapping[str, Any],
        completion: Callable[..., Any] | None = None,
    ) -> None:
        """Bindet Modell und Parameter; `completion` ersetzt den LiteLLM-Aufruf."""

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
    ) -> dict[str, object]:
        """Fordert eine JSON-Ausgabe an und gibt allein das geparste Objekt zurück."""

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
        except (AttributeError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise Formatbruch(rohantwort) from exc
        return _ausgabe_pruefen(inhalt, ausgabe_schema, rohantwort)

"""Modelle und Abläufe der Simulation."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from string import Template
from typing import TYPE_CHECKING

from simulation.sprachmodell import (
    AUSGABE_SCHEMA,
    Anbieterfehler,
    Antwort,
    ContentFilter,
    FakeSprachmodell,
    Formatbruch,
    LiteLLMSprachmodell,
    Sprachmodell,
)

if TYPE_CHECKING:
    from simulation.models import ModellKonfiguration, Simulationskern
    from vignetten.models import Vignette


MAX_VERSUCHE: int = 3

# Die datenschutzrechtliche Zusage aus ADR-0026 steht in keiner Konfiguration:
# Ein Tor, das im selben Formular abschaltbar wäre, in dem man den Anbieter
# wählt, ist keins.
OPENROUTER_PROVIDER_FILTER: dict[str, object] = {
    "require_parameters": True,
    "data_collection": "deny",
    "zdr": True,
}


@dataclass(frozen=True)
class Fehlversuch:
    """Ein maschinell verworfener Modellaufruf."""

    grund: str
    rohantwort: str


@dataclass(frozen=True)
class Antwortversuch:
    """Das flüchtige Ergebnis von höchstens drei Modellaufrufen."""

    antwort: Antwort | None
    native_reasoning_spur: str | None
    fehlversuche: list[Fehlversuch]


def render(vorlage_text: str, mapping: Mapping[str, str]) -> str:
    """Füllt eine Vorlage mit genau ihren vereinbarten Platzhaltern."""

    vorlage: Template = Template(vorlage_text)
    ueberzaehlige_platzhalter: set[str] = set(mapping) - set(vorlage.get_identifiers())
    if ueberzaehlige_platzhalter:
        raise ValueError(
            f"Überzählige Platzhalter: {', '.join(sorted(ueberzaehlige_platzhalter))}."
        )
    return vorlage.substitute(mapping)


def vorlage_rendern(vorlage_text: str, platzhalter: Mapping[str, str]) -> str:
    """Übergibt dem strikten Renderer nur die in der Vorlage benutzten Platzhalter."""

    vorlage: Template = Template(vorlage_text)
    return render(
        vorlage_text,
        {name: platzhalter[name] for name in vorlage.get_identifiers()},
    )


def antwort_versuchen(
    vignette: "Vignette",
    kern: "Simulationskern",
    modell_konfiguration: "ModellKonfiguration",
    verlauf: Sequence[tuple[str, str]],
    eingabe: str,
) -> Antwortversuch:
    """Erzeugt schreibfrei eine Antwort der simulierten Schüler:in."""

    from vignetten.models import prompt_platzhalter

    platzhalter: dict[str, str] = prompt_platzhalter(vignette)
    system_prompt: str = vorlage_rendern(kern.system_prompt_vorlage, platzhalter)
    user_prompt: str = vorlage_rendern(kern.user_prompt_vorlage, platzhalter)
    sprachmodell: Sprachmodell = _sprachmodell_aus(modell_konfiguration)
    fehlversuche: list[Fehlversuch] = []

    for _ in range(MAX_VERSUCHE):
        try:
            antwort, native_reasoning_spur = sprachmodell.antworten(
                system_prompt,
                user_prompt,
                verlauf,
                eingabe,
                AUSGABE_SCHEMA,
            )
        except Formatbruch as exc:
            fehlversuche.append(Fehlversuch("Formatbruch", exc.rohantwort))
        except Anbieterfehler as exc:
            fehlversuche.append(Fehlversuch("Anbieterfehler", exc.rohantwort))
        except ContentFilter as exc:
            fehlversuche.append(Fehlversuch("Content-Filter", exc.rohantwort))
        else:
            return Antwortversuch(antwort, native_reasoning_spur, fehlversuche)
    return Antwortversuch(None, None, fehlversuche)


def _sprachmodell_aus(modell_konfiguration: "ModellKonfiguration") -> Sprachmodell:
    """Bildet den in der Konfiguration gewählten Adapter."""

    from simulation.models import Anbieter

    if modell_konfiguration.anbieter == Anbieter.FAKE:
        return FakeSprachmodell(modell_konfiguration.parameter.get("skript", []))
    aufrufparameter: dict[str, object] = dict(modell_konfiguration.parameter)
    aufrufparameter["api_key"] = modell_konfiguration.anbieter_token
    if modell_konfiguration.anbieter_basis_url:
        aufrufparameter["api_base"] = modell_konfiguration.anbieter_basis_url
    if modell_konfiguration.anbieter == Anbieter.OPENROUTER:
        aufrufparameter["extra_body"] = {"provider": OPENROUTER_PROVIDER_FILTER}
    return LiteLLMSprachmodell(modell_konfiguration.sprachmodell, aufrufparameter)

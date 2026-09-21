"""Modelle und Abläufe der Simulation."""

import time
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

# Wie lange ein Gesprächsschritt höchstens auf das Sprachmodell warten darf —
# alle Versuche eines Schritts teilen sich diese Frist, jeder einzelne Aufruf
# bekommt die verbliebene Restzeit als Timeout. Das ist nicht das
# Gesprächsbudget der Vignette (ADR-0012), sondern eine Zusage dieser Naht.
#
# Nach oben begrenzt der Worker: 90 s lassen dem Deployment-Timeout (180 s,
# README) Luft, auch wenn mehrere Versuche in dieselbe Anfrage fallen und der
# Endpunkt danach noch schreibt. Nach unten begrenzt die Denkspur, die das
# Ausgabeschema vor der Äußerung erzwingt (ADR-0005): Ein Reasoning-Modell
# liefert legitim erst nach 20-60 s. 90 s ist der schlechte Fall, nicht der
# Normalfall.
SPRACHMODELL_FRIST_SEKUNDEN: float = 90.0

# Ein Aufruf, dessen Frist schon aufgebraucht ist, bekommt noch diese Zeit,
# damit er sauber scheitert, statt mit einem Timeout von null zu hängen.
SPRACHMODELL_MINDEST_ANFRAGEFRIST_SEKUNDEN: float = 1.0

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
    # Die Frist steht einmal je Gesprächsschritt und gilt für alle Versuche
    # zusammen; ein hängender Anbieter frisst sie selbst auf, die Wiederholung
    # entfällt damit von allein.
    frist: float = time.monotonic() + SPRACHMODELL_FRIST_SEKUNDEN

    for _ in range(MAX_VERSUCHE):
        if time.monotonic() >= frist:
            fehlversuche.append(
                Fehlversuch(
                    "Anbieterfehler",
                    "Die Frist des Gesprächsschritts war vor dem Versuch erschöpft.",
                )
            )
            break
        try:
            antwort: Antwort = sprachmodell.antworten(
                system_prompt,
                user_prompt,
                verlauf,
                eingabe,
                AUSGABE_SCHEMA,
                _restzeit(frist),
            )
        except Formatbruch as exc:
            fehlversuche.append(Fehlversuch("Formatbruch", exc.rohantwort))
        except Anbieterfehler as exc:
            fehlversuche.append(Fehlversuch("Anbieterfehler", exc.rohantwort))
        except ContentFilter as exc:
            fehlversuche.append(Fehlversuch("Content-Filter", exc.rohantwort))
        else:
            return Antwortversuch(antwort, fehlversuche)
    return Antwortversuch(None, fehlversuche)


def _restzeit(frist: float) -> float:
    """Begrenzt einen einzelnen Aufruf auf das, was von der Frist übrig ist."""

    return max(frist - time.monotonic(), SPRACHMODELL_MINDEST_ANFRAGEFRIST_SEKUNDEN)


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

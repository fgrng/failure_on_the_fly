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
    Sprachmodell,
)

if TYPE_CHECKING:
    from simulation.models import ModellKonfiguration, Simulationskern
    from vignetten.models import Vignette


MAX_VERSUCHE: int = 3


@dataclass(frozen=True)
class Fehlversuch:
    """Ein maschinell verworfener Modellaufruf."""

    grund: str


@dataclass(frozen=True)
class Antwortversuch:
    """Das flüchtige Ergebnis von höchstens drei Modellaufrufen."""

    antwort: Antwort | None
    native_reasoning_spur: str | None
    fehlversuche: list[Fehlversuch]

    @property
    def endgueltig_gescheitert(self) -> bool:
        """Kennzeichnet, dass kein verwertbares Ergebnis entstanden ist."""

        return self.antwort is None


def render(vorlage_text: str, mapping: Mapping[str, str]) -> str:
    """Füllt eine Vorlage mit genau ihren vereinbarten Platzhaltern."""

    vorlage: Template = Template(vorlage_text)
    ueberzaehlige_platzhalter: set[str] = set(mapping) - set(
        vorlage.get_identifiers()
    )
    if ueberzaehlige_platzhalter:
        raise ValueError(
            "Überzählige Platzhalter: "
            f"{', '.join(sorted(ueberzaehlige_platzhalter))}."
        )
    return vorlage.substitute(mapping)


def antwort_versuchen(
    vignette: "Vignette",
    kern: "Simulationskern",
    modell_konfiguration: "ModellKonfiguration",
    verlauf: Sequence[str],
    eingabe: str,
) -> Antwortversuch:
    """Erzeugt schreibfrei eine Antwort der simulierten Schüler:in."""

    from vignetten.models import prompt_platzhalter

    platzhalter: dict[str, str] = prompt_platzhalter(vignette)
    system_prompt: str = _prompt_rendern(kern.system_prompt_vorlage, platzhalter)
    user_prompt: str = _prompt_rendern(kern.user_prompt_vorlage, platzhalter)
    user_prompt = f"{user_prompt}\n\nVerlauf:\n{'\n'.join(verlauf)}\n\nEingabe:\n{eingabe}"
    sprachmodell: Sprachmodell = _sprachmodell_aus(modell_konfiguration)
    fehlversuche: list[Fehlversuch] = []

    for _ in range(MAX_VERSUCHE):
        try:
            antwort, native_reasoning_spur = sprachmodell.antworten(
                system_prompt,
                user_prompt,
                AUSGABE_SCHEMA,
            )
        except Formatbruch:
            fehlversuche.append(Fehlversuch("Formatbruch"))
        except Anbieterfehler:
            fehlversuche.append(Fehlversuch("Anbieterfehler"))
        except ContentFilter:
            fehlversuche.append(Fehlversuch("Content-Filter"))
        else:
            return Antwortversuch(antwort, native_reasoning_spur, fehlversuche)
    return Antwortversuch(None, None, fehlversuche)


def _sprachmodell_aus(modell_konfiguration: "ModellKonfiguration") -> Sprachmodell:
    """Bildet den in der Konfiguration gewählten Adapter."""

    if modell_konfiguration.sprachmodell != "fake":
        raise ValueError("Unbekanntes Sprachmodell.")
    return FakeSprachmodell(modell_konfiguration.parameter.get("skript", []))


def _prompt_rendern(vorlage_text: str, platzhalter: Mapping[str, str]) -> str:
    """Übergibt dem strikten Renderer nur die in der Vorlage verwendeten Werte."""

    vorlage: Template = Template(vorlage_text)
    return render(
        vorlage_text,
        {name: platzhalter[name] for name in vorlage.get_identifiers()},
    )

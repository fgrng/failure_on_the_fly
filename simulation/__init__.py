"""Modelle und Abläufe der Simulation."""

from collections.abc import Mapping
from string import Template


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

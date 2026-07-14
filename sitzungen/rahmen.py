"""Gemeinsames Rendern der Sitzungsrahmenhandlung."""

from string import Template

from simulation import render as simulation_render
from vignetten.models import Vignette, rahmen_platzhalter


def rahmen_rendern(vorlage: str, vignette: Vignette) -> str:
    """Übergibt dem strikten Renderer nur die benutzten Rahmenplatzhalter."""

    platzhalter: dict[str, str] = rahmen_platzhalter(vignette)
    namen: list[str] = Template(vorlage).get_identifiers()
    return simulation_render(vorlage, {name: platzhalter[name] for name in namen})

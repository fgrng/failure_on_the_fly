"""Vertragstest für die Prompt-Platzhalter und die Liste ihrer Umgebungen."""

import pytest

from simulation import vorlage_rendern
from simulation.models import (
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_RAHMEN,
    Simulationskern,
)
from sitzungen.durchlauf import rahmenhandlung_rendern
from vignetten.models import Vignette, prompt_platzhalter


def _vorlage(vertrag: frozenset[str]) -> str:
    """Benutzt jeden Namen des Vertrags genau einmal."""

    return " ".join(f"${name}" for name in sorted(vertrag))


@pytest.mark.django_db
def test_jeder_vertragsname_hat_einen_wert() -> None:
    """Ein Kern, der alle Vertragsnamen benutzt, ist gültig und rendert vollständig.

    Fehlt einem Namen der Wert, scheitert erst das Rendern in der Sitzung.
    """

    kern: Simulationskern = Simulationskern.objects.anlegen(
        system_prompt_vorlage=_vorlage(VERTRAG_PROMPT),
        rahmenhandlung_einleitung=_vorlage(VERTRAG_RAHMEN),
    )
    kern.full_clean()
    vignette: Vignette = Vignette(
        schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
        lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
    )

    prompt: str = vorlage_rendern(
        kern.system_prompt_vorlage, prompt_platzhalter(vignette)
    )
    rahmen: str = rahmenhandlung_rendern(kern.rahmenhandlung_einleitung, vignette)

    assert "$" not in prompt
    assert "$" not in rahmen


def test_platzhalter_mit_umgebung_deckt_sich_mit_der_erzeugten_ausgabe() -> None:
    """Die Kennzeichnung in der Kern-Ansicht darf nicht von den Werten driften."""

    vollstaendig: Vignette = Vignette(
        fehlermuster_beschreibung="Das Gleichheitszeichen gilt als Aufforderung.",
        lernauftrag_text="Setze die passende Zahl ein:\n[bild]",
        lernauftrag_bild="vignettenbilder/auftrag.gif",
        lernauftrag_bildbeschreibung="Arbeitsblatt mit einer Platzhalteraufgabe.",
        lernauftrag_simulationshinweise="Lukas ignoriert den Term rechts der Lücke.",
        arbeitsheft_text="8 + 4 = 12\n[bild]",
        arbeitsheft_bild="vignettenbilder/heft.gif",
        arbeitsheft_bildbeschreibung="Heftseite mit der Rechnung 8 + 4 = 12.",
        arbeitsheft_simulationshinweise="Auf Nachfragen beharrt Lukas auf der 12.",
        schuelerin_name="Lukas",
        schuelerin_geschlecht=Vignette.Geschlecht.MAENNLICH,
        fach="Mathematik",
        thema="Gleichungen",
        klassenstufe="4",
    )

    platzhalter: dict[str, str] = prompt_platzhalter(vollstaendig)
    mit_umgebung: set[str] = {
        name
        for name, wert in platzhalter.items()
        if wert.startswith(f"<{name}>") and wert.endswith(f"</{name}>")
    }

    assert mit_umgebung == set(PROMPT_PLATZHALTER_MIT_UMGEBUNG)
    assert PROMPT_PLATZHALTER_MIT_UMGEBUNG <= VERTRAG_PROMPT

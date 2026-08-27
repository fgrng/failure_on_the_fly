"""Vertragstest für die Liste der umgebungserzeugenden Prompt-Platzhalter."""

from simulation.models import PROMPT_PLATZHALTER_MIT_UMGEBUNG, VERTRAG_PROMPT
from vignetten.models import Vignette, prompt_platzhalter


def test_platzhalter_mit_umgebung_deckt_sich_mit_der_erzeugten_ausgabe() -> None:
    """Die Kennzeichnung in der Kern-Ansicht darf nicht von den Werten driften."""

    vollstaendig: Vignette = Vignette(
        fehlermuster_beschreibung="Das Gleichheitszeichen gilt als Aufforderung.",
        lernauftrag_text="Setze die passende Zahl ein: [bild]",
        lernauftrag_bild="vignettenbilder/auftrag.gif",
        lernauftrag_bildbeschreibung="Arbeitsblatt mit einer Platzhalteraufgabe.",
        lernauftrag_simulationshinweise="Lukas ignoriert den Term rechts der Lücke.",
        arbeitsheft_text="8 + 4 = 12 [bild]",
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

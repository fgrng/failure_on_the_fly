"""Prompt-Platzhalter einer Vignette, ohne Django.

Die Funktionen lesen nur gleichnamige Attribute der Vignettenfelder; sie
nehmen eine `Vignette` ebenso wie jedes andere Objekt mit diesen Feldern,
etwa die Vignette aus einer Markdown-Datei in `scripts/simulieren.py`.
"""

import re
from dataclasses import dataclass
from typing import Any


# Der Marker zählt nur allein auf seiner Zeile; die ganze Zeile samt Umbruch fällt weg.
_POSITIONSMARKER: re.Pattern[str] = re.compile(
    r"^[^\S\r\n]*\[bild\][^\S\r\n]*(?:\r?\n|\Z)", re.IGNORECASE | re.MULTILINE
)


def _am_positionsmarker_zerlegen(text: str, bild: object) -> tuple[str, str]:
    # Teilt einen Aufgabenkontext am ersten Positionsmarker und entfernt alle.

    textteile: list[str] = _POSITIONSMARKER.split(text)
    vor_bild: str = textteile[0]
    nach_bild: str = "".join(textteile[1:])
    if not bild:
        return vor_bild + nach_bild, ""
    return vor_bild, nach_bild


@dataclass(frozen=True)
class Aufgabenkontextteil:
    """Ein Teil des Aufgabenkontexts — Lernauftrag oder Arbeitsheft."""

    name: str
    label: str
    artikel: str
    text_vor_bild: str
    bild: object
    bildbeschreibung: str
    text_nach_bild: str
    simulationshinweise: str

    @property
    def text(self) -> str:
        """Liefert den Text des Teils ohne Positionsmarker."""
        return self.text_vor_bild + self.text_nach_bild


def aufgabenkontextteil(
    vignette: Any, name: str, label: str, artikel: str
) -> Aufgabenkontextteil:
    """Baut einen Teil des Aufgabenkontexts aus den gleichnamigen Feldern."""

    bild: object = getattr(vignette, f"{name}_bild")
    vor_bild, nach_bild = _am_positionsmarker_zerlegen(
        getattr(vignette, f"{name}_text"), bild
    )
    return Aufgabenkontextteil(
        name=name,
        label=label,
        artikel=artikel,
        text_vor_bild=vor_bild,
        bild=bild,
        bildbeschreibung=getattr(vignette, f"{name}_bildbeschreibung"),
        text_nach_bild=nach_bild,
        simulationshinweise=getattr(vignette, f"{name}_simulationshinweise"),
    )


def lernauftrag(vignette: Any) -> Aufgabenkontextteil:
    """Liefert den Lernauftrag als Teil des Aufgabenkontexts."""
    return aufgabenkontextteil(vignette, "lernauftrag", "Lernauftrag", "der")


def arbeitsheft(vignette: Any) -> Aufgabenkontextteil:
    """Liefert das Arbeitsheft als Teil des Aufgabenkontexts."""
    return aufgabenkontextteil(vignette, "arbeitsheft", "Arbeitsheft", "das")


def _umgebung(tag: str, inhalt: str) -> str:
    # Fasst einen nichtleeren Wert in eine einzeilige XML-artige Umgebung ein.

    return f"<{tag}>{inhalt}</{tag}>" if inhalt else ""


def _huelle(tag: str, inhalt: str) -> str:
    # Fasst einen nichtleeren Wert in eine mehrzeilige XML-artige Umgebung ein.

    return f"<{tag}>\n{inhalt}\n</{tag}>" if inhalt else ""


# Die Schlüssel sind die Werte von `Vignette.Geschlecht`.
_ANREDEN: dict[str, str] = {
    "weiblich": "Frau",
    "männlich": "Herr",
}


def prompt_platzhalter(vignette: Any) -> dict[str, str]:
    """Liefert die Vignettenwerte für Prompt-Vorlagen."""

    return {
        "fehlermuster_beschreibung": _huelle(
            "fehlermuster_beschreibung", vignette.fehlermuster_beschreibung
        ),
        "lernauftrag": _aufgabenkontext_prompt(lernauftrag(vignette)),
        "arbeitsheft": _aufgabenkontext_prompt(arbeitsheft(vignette)),
        "lernauftrag_simulationshinweise": _huelle(
            "lernauftrag_simulationshinweise",
            vignette.lernauftrag_simulationshinweise,
        ),
        "arbeitsheft_simulationshinweise": _huelle(
            "arbeitsheft_simulationshinweise",
            vignette.arbeitsheft_simulationshinweise,
        ),
        "schuelerin_name": vignette.schuelerin_name,
        "schuelerin_geschlecht": vignette.schuelerin_geschlecht,
        "lehrperson_name": vignette.lehrperson_name,
        "lehrperson_anrede": _ANREDEN[vignette.lehrperson_geschlecht],
        "fach": vignette.fach,
        "thema": vignette.thema,
        "klassenstufe": vignette.klassenstufe,
    }


def _aufgabenkontext_prompt(teil: Aufgabenkontextteil) -> str:
    # Fasst Text und Bildbeschreibung eines Teils in sichtbarer Reihenfolge zusammen.

    name: str = teil.name
    if teil.bild and teil.bildbeschreibung:
        stuecke: tuple[tuple[str, str], ...] = (
            (f"{name}_text", teil.text_vor_bild),
            (f"{name}_bildbeschreibung", teil.bildbeschreibung),
            (f"{name}_text", teil.text_nach_bild),
        )
    else:
        stuecke = ((f"{name}_text", teil.text),)
    inhalt: str = "\n".join(
        umgebung for tag, wert in stuecke if (umgebung := _umgebung(tag, wert))
    )
    return _huelle(name, inhalt)


def rahmen_platzhalter(vignette: Any) -> dict[str, str]:
    """Liefert die Rohwerte und Grammatikformen für die Rahmenhandlung."""
    # Die Schlüssel sind die Werte von `Vignette.Geschlecht`.
    pronomen_und_possessiv: dict[str, tuple[str, str]] = {
        "weiblich": ("sie", "ihr"),
        "männlich": ("er", "sein"),
    }
    schuelerin_geschlecht: str = vignette.schuelerin_geschlecht
    lehrperson_geschlecht: str = vignette.lehrperson_geschlecht
    schuelerin_pronomen, schuelerin_possessiv = pronomen_und_possessiv[
        schuelerin_geschlecht
    ]
    lehrperson_pronomen, lehrperson_possessiv = pronomen_und_possessiv[
        lehrperson_geschlecht
    ]
    return {
        "schuelerin_name": vignette.schuelerin_name,
        "schuelerin_geschlecht": schuelerin_geschlecht,
        "lehrperson_name": vignette.lehrperson_name,
        "lehrperson_geschlecht": lehrperson_geschlecht,
        "fach": vignette.fach,
        "thema": vignette.thema,
        "klassenstufe": vignette.klassenstufe,
        "schuelerin_pronomen": schuelerin_pronomen,
        "schuelerin_possessiv": schuelerin_possessiv,
        "lehrperson_pronomen": lehrperson_pronomen,
        "lehrperson_possessiv": lehrperson_possessiv,
        "lehrperson_anrede": _ANREDEN[lehrperson_geschlecht],
    }

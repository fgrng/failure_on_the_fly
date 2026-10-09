"""Antwortversuche gegen den deterministischen Sprachmodell-Fake."""

from simulation import antwort_versuchen
from simulation.models import ModellKonfiguration, Simulationskern
from vignetten.models import Vignette


def test_antwort_versuchen_liefert_denkspur_und_aeusserung_des_fakes() -> None:
    """Ein geglückter Modellaufruf wird als Antwortversuch zurückgegeben."""

    antwortversuch = antwort_versuchen(
        Vignette(
            fehlermuster_beschreibung="Brüche werden addiert.",
            lernauftrag_text="Addiere zwei Brüche.",
            arbeitsheft_bildbeschreibung="1/2 + 1/3 = 2/5",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            fach="Mathematik",
            thema="Brüche",
            klassenstufe="5",
        ),
        Simulationskern(
            system_prompt_vorlage="$fehlermuster_beschreibung",
            user_prompt_vorlage="$lernauftrag",
        ),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"denkspur": "Ich addiere Zähler und Nenner.", "aeusserung": "2/5."}
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort.denkspur == "Ich addiere Zähler und Nenner."
    assert antwortversuch.antwort.aeusserung == "2/5."
    assert antwortversuch.fehlversuche == []


def test_antwort_versuchen_haelt_formatbruch_neben_der_antwort_fest() -> None:
    """Ein Formatbruch wird verworfen und der nächste Versuch wird genutzt."""

    antwortversuch = antwort_versuchen(
        Vignette(lernauftrag_text="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"fehler": "formatbruch", "rohantwort": "keine JSON-Antwort"},
                    {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort is not None
    assert antwortversuch.fehlversuche[0].grund == "Formatbruch"
    assert antwortversuch.fehlversuche[0].rohantwort == "keine JSON-Antwort"


def test_antwort_versuchen_haelt_anbieterfehler_neben_der_antwort_fest() -> None:
    """Ein Anbieterfehler wird verworfen und der nächste Versuch wird genutzt."""

    antwortversuch = antwort_versuchen(
        Vignette(lernauftrag_text="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"fehler": "anbieterfehler"},
                    {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort is not None
    assert antwortversuch.fehlversuche[0].grund == "Anbieterfehler"


def test_antwort_versuchen_kennzeichnet_drei_verworfene_versuche() -> None:
    """Nach dem begrenzten Wiederholen bleibt kein halber Gesprächsschritt zurück."""

    antwortversuch = antwort_versuchen(
        Vignette(lernauftrag_text="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={"skript": [{"fehler": "anbieterfehler"}] * 4},
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort is None
    assert [fehlversuch.grund for fehlversuch in antwortversuch.fehlversuche] == [
        "Anbieterfehler",
        "Anbieterfehler",
        "Anbieterfehler",
    ]

"""Antwortversuche gegen den deterministischen Sprachmodell-Fake."""

import pytest

from simulation import MAX_VERSUCHE, antwort_versuchen
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.sprachmodell import AUSGABE_SCHEMA, FakeSprachmodell
from vignetten.models import Vignette


def test_antwort_versuchen_liefert_denkspur_und_aeusserung_des_fakes() -> None:
    """Ein geglückter Modellaufruf wird als Antwortversuch zurückgegeben."""

    antwortversuch = antwort_versuchen(
        Vignette(
            fehlermuster_beschreibung="Brüche werden addiert.",
            lernauftrag="Addiere zwei Brüche.",
            arbeitsheft_beschreibung="1/2 + 1/3 = 2/5",
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
    assert antwortversuch.native_reasoning_spur is None
    assert antwortversuch.fehlversuche == []


def test_antwort_versuchen_haelt_formatbruch_neben_der_antwort_fest() -> None:
    """Ein Formatbruch wird verworfen und der nächste Versuch wird genutzt."""

    antwortversuch = antwort_versuchen(
        Vignette(lernauftrag="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"fehler": "formatbruch"},
                    {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort is not None
    assert antwortversuch.fehlversuche[0].grund == "Formatbruch"


def test_antwort_versuchen_haelt_anbieterfehler_neben_der_antwort_fest() -> None:
    """Ein Anbieterfehler wird verworfen und der nächste Versuch wird genutzt."""

    antwortversuch = antwort_versuchen(
        Vignette(lernauftrag="Addiere zwei Brüche."),
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
        Vignette(lernauftrag="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={"skript": [{"fehler": "anbieterfehler"}] * MAX_VERSUCHE},
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.endgueltig_gescheitert
    assert antwortversuch.antwort is None
    assert [fehlversuch.grund for fehlversuch in antwortversuch.fehlversuche] == [
        "Anbieterfehler"
    ] * MAX_VERSUCHE


def test_antwort_versuchen_gibt_native_reasoning_spur_durch() -> None:
    """Native Anbieter-Spuren bleiben von der Denkspur getrennt."""

    antwortversuch = antwort_versuchen(
        Vignette(lernauftrag="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Ich addiere.",
                        "aeusserung": "2/5.",
                        "native_reasoning_spur": "native Spur",
                    }
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.native_reasoning_spur == "native Spur"


def test_antwort_versuchen_gibt_dem_fake_nur_sichtbaren_verlauf() -> None:
    """Die Denkspur erreicht keinen späteren Modellaufruf."""

    FakeSprachmodell.letzte_anfragen.clear()
    vorheriger_versuch = antwort_versuchen(
        Vignette(lernauftrag="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Die geheime Denkspur.",
                        "aeusserung": "Sichtbare Äußerung",
                    }
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )
    antwort_versuchen(
        Vignette(lernauftrag="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={"skript": [{"denkspur": "x", "aeusserung": "2/5."}]},
        ),
        verlauf=[vorheriger_versuch.antwort.aeusserung],
        eingabe="Wie hast du gerechnet?",
    )

    assert "Sichtbare Äußerung" in FakeSprachmodell.letzte_anfragen[1][1]
    assert "Die geheime Denkspur." not in FakeSprachmodell.letzte_anfragen[1][1]


def test_ausgabe_schema_fuehrt_denkspur_vor_aeusserung() -> None:
    """Die normativ geordnete strukturierte Ausgabe erzeugt die Denkspur zuerst."""

    assert list(AUSGABE_SCHEMA["properties"]) == ["denkspur", "aeusserung"]


@pytest.mark.django_db
def test_antwort_versuchen_persistiert_nichts() -> None:
    """Der Funktionsaufruf verändert keine Modell-Konfiguration."""

    konfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake",
        parameter={"skript": [{"denkspur": "Ich addiere.", "aeusserung": "2/5."}]},
    )

    antwort_versuchen(
        Vignette(lernauftrag="Addiere zwei Brüche."),
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        konfiguration,
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert ModellKonfiguration.objects.count() == 1

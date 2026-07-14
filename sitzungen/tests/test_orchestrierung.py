"""Tests der schreibfreien Spielorchestrierung über dem Scratch-Sink."""

from django.contrib.sessions.backends.db import SessionStore

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.orchestrierung import gespraechsschritt_ausfuehren, sitzung_starten
from sitzungen.sink import ScratchSink
from vignetten.models import Vignette


def test_scratch_sink_haelt_erfolgreichen_schritt_mit_fehlversuchen_in_db_form() -> None:
    """Der schreibfreie Sink bewahrt jeden Zug in der späteren Persistenzform auf."""

    session: SessionStore = SessionStore()
    sink: ScratchSink = ScratchSink(session)
    vignette: Vignette = Vignette(lernauftrag="Addiere zwei Brüche.")
    kern: Simulationskern = Simulationskern(user_prompt_vorlage="$lernauftrag")
    konfiguration: ModellKonfiguration = ModellKonfiguration(
        sprachmodell="fake",
        parameter={
            "skript": [
                {"fehler": "formatbruch", "rohantwort": "keine JSON-Antwort"},
                {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
            ]
        },
    )

    sitzung_starten(sink, vignette, kern, konfiguration)
    gespraechsschritt_ausfuehren(
        sink,
        vignette,
        kern,
        konfiguration,
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert session["probelauf"]["gespraechsschritte"] == [
        {
            "reihenfolge": 1,
            "eingabe": "Wie hast du gerechnet?",
            "denkspur": "Ich addiere.",
            "aeusserung": "2/5.",
            "native_reasoning_spur": None,
            "fehlversuche": [
                {"grund": "Formatbruch", "rohantwort": "keine JSON-Antwort"}
            ],
        }
    ]


def test_scratch_sink_haelt_den_answerless_schritt_und_gescheiterten_status() -> None:
    """Ein endgültig verworfener Antwortversuch beendet die schreibfreie Sitzung."""

    session: SessionStore = SessionStore()
    sink: ScratchSink = ScratchSink(session)
    vignette: Vignette = Vignette(lernauftrag="Addiere zwei Brüche.")
    kern: Simulationskern = Simulationskern(user_prompt_vorlage="$lernauftrag")
    konfiguration: ModellKonfiguration = ModellKonfiguration(
        sprachmodell="fake",
        parameter={"skript": [{"fehler": "anbieterfehler"}] * 3},
    )

    sitzung_starten(sink, vignette, kern, konfiguration)
    gespraechsschritt_ausfuehren(
        sink,
        vignette,
        kern,
        konfiguration,
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert session["probelauf"]["gespraechsschritte"] == [
        {
            "reihenfolge": 1,
            "eingabe": "Wie hast du gerechnet?",
            "denkspur": None,
            "aeusserung": None,
            "native_reasoning_spur": None,
            "fehlversuche": [
                {"grund": "Anbieterfehler", "rohantwort": ""},
                {"grund": "Anbieterfehler", "rohantwort": ""},
                {"grund": "Anbieterfehler", "rohantwort": ""},
            ],
        }
    ]
    assert session["probelauf"]["status"] == "gescheitert"

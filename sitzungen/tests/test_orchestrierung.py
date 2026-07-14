"""Tests der Spielorchestrierung über ihren beiden Sinks."""

import pytest
from django.contrib.sessions.backends.db import SessionStore

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
)
from sitzungen.orchestrierung import gespraechsschritt_ausfuehren, sitzung_starten
from sitzungen.sink import DBSink, ScratchSink
from vignetten.models import Vignette


def _persistierbares_tripel(
    skript: list[dict[str, str]],
) -> tuple[Vignette, Simulationskern, ModellKonfiguration]:
    # Legt das minimale, vom Fake ausführbare Sitzungs-Tripel an.

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    return (
        Vignette.objects.anlegen(Konto.objects.create_user(username="ada")),
        kern,
        ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={"skript": skript},
        ),
    )


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


@pytest.mark.django_db
def test_db_sink_persistiert_einen_erfolgreichen_gespraechsschritt() -> None:
    """Ein geglückter Zug steht sofort samt Denk- und nativer Reasoning-Spur in der DB."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [
            {
                "denkspur": "Ich addiere Zähler und Nenner.",
                "aeusserung": "2/5.",
                "native_reasoning_spur": "Native Spur.",
            }
        ]
    )
    sink: DBSink = DBSink(Teilnahme.objects.create())

    sitzung_starten(sink, vignette, kern, konfiguration)
    assert Sitzung.objects.count() == 1
    gespraechsschritt_ausfuehren(
        sink,
        vignette,
        kern,
        konfiguration,
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    sitzung: Sitzung = Sitzung.objects.get()
    assert sitzung.status == Sitzung.Status.LAUFEND
    assert list(
        Gespraechsschritt.objects.filter(sitzung=sitzung).values(
            "reihenfolge",
            "eingabe",
            "denkspur",
            "aeusserung",
            "native_reasoning_spur",
        )
    ) == [
        {
            "reihenfolge": 1,
            "eingabe": "Wie hast du gerechnet?",
            "denkspur": "Ich addiere Zähler und Nenner.",
            "aeusserung": "2/5.",
            "native_reasoning_spur": "Native Spur.",
        }
    ]


@pytest.mark.django_db
def test_db_sink_haengt_fehlversuche_neben_den_erfolgreichen_schritt() -> None:
    """Ein verworfener Versuch bleibt am geglückten Schritt außerhalb des Transkripts."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [
            {"fehler": "formatbruch", "rohantwort": "Kein JSON."},
            {"denkspur": "Meine Regel.", "aeusserung": "2/5."},
        ]
    )
    sink: DBSink = DBSink(Teilnahme.objects.create())

    sitzung_starten(sink, vignette, kern, konfiguration)
    gespraechsschritt_ausfuehren(
        sink, vignette, kern, konfiguration, verlauf=[], eingabe="Warum?"
    )

    schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
    assert schritt.aeusserung == "2/5."
    assert list(
        Fehlversuch.objects.filter(gespraechsschritt=schritt).values(
            "grund", "rohantwort"
        )
    ) == [{"grund": "Formatbruch", "rohantwort": "Kein JSON."}]


@pytest.mark.django_db
def test_db_sink_persistiert_answerless_schritt_und_gescheiterten_status() -> None:
    """Drei Fehlversuche bleiben als antwortloser Abbruchschritt erhalten."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"fehler": "anbieterfehler"}] * 3
    )
    sink: DBSink = DBSink(Teilnahme.objects.create())

    sitzung_starten(sink, vignette, kern, konfiguration)
    gespraechsschritt_ausfuehren(
        sink, vignette, kern, konfiguration, verlauf=[], eingabe="Warum?"
    )

    sitzung: Sitzung = Sitzung.objects.get()
    schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
    assert sitzung.status == Sitzung.Status.GESCHEITERT
    assert (schritt.denkspur, schritt.aeusserung) == (None, None)
    assert Fehlversuch.objects.filter(gespraechsschritt=schritt).count() == 3


@pytest.mark.django_db
def test_db_sink_diagnose_schliesst_die_sitzung_ab() -> None:
    """Die gesetzte Diagnose vollzieht den Abschlussübergang der Sitzung."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    sink: DBSink = DBSink(Teilnahme.objects.create())

    sitzung_starten(sink, vignette, kern, konfiguration)
    sink.diagnose_setzen("Zähler und Nenner werden addiert.")

    sitzung: Sitzung = Sitzung.objects.get()
    assert sitzung.status == Sitzung.Status.ABGESCHLOSSEN
    assert (
        Diagnose.objects.get(sitzung=sitzung).text
        == "Zähler und Nenner werden addiert."
    )


@pytest.mark.django_db
def test_db_sink_aktives_abbrechen_setzt_den_eigenen_status() -> None:
    """Ein gewollter Abbruch ist von einem technischen Fehlschlag unterscheidbar."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    sink: DBSink = DBSink(Teilnahme.objects.create())

    sitzung_starten(sink, vignette, kern, konfiguration)
    sink.status_setzen(Sitzung.Status.ABGEBROCHEN)

    assert Sitzung.objects.get().status == Sitzung.Status.ABGEBROCHEN
    assert not Diagnose.objects.exists()


@pytest.mark.django_db
def test_scratch_und_db_sink_tragen_dieselbe_gespraechsschritt_struktur() -> None:
    """Der gemeinsame Orchestrierungsdurchlauf unterscheidet sich nur im Speicherziel."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [
            {"fehler": "formatbruch", "rohantwort": "Kein JSON."},
            {
                "denkspur": "Meine Regel.",
                "aeusserung": "2/5.",
                "native_reasoning_spur": "Native Spur.",
            },
        ]
    )
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, verlauf=[], eingabe="Warum?"
        )

    db_schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
    db_struktur = [
        {
            "reihenfolge": db_schritt.reihenfolge,
            "eingabe": db_schritt.eingabe,
            "denkspur": db_schritt.denkspur,
            "aeusserung": db_schritt.aeusserung,
            "native_reasoning_spur": db_schritt.native_reasoning_spur,
            "fehlversuche": list(
                Fehlversuch.objects.filter(gespraechsschritt=db_schritt).values(
                    "grund", "rohantwort"
                )
            ),
        }
    ]

    assert scratch.gespraechsschritte == db_struktur

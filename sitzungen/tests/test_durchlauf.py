"""Tests des Sitzungslaufs über seinen beiden Sinks."""

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
from sitzungen.durchlauf import (
    gespraechsschritt_ausfuehren,
    modellverlauf,
    sitzung_abbrechen,
    sitzung_beenden,
    sitzung_starten,
)
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


def test_scratch_sink_haelt_erfolgreichen_schritt_mit_fehlversuchen_in_db_form() -> (
    None
):
    """Der schreibfreie Sink bewahrt jeden Zug in der späteren Persistenzform auf."""

    session: SessionStore = SessionStore()
    sink: ScratchSink = ScratchSink(session)
    vignette: Vignette = Vignette(lernauftrag_text="Addiere zwei Brüche.")
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
    vignette: Vignette = Vignette(lernauftrag_text="Addiere zwei Brüche.")
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
    """Ein geglückter Gesprächsschritt steht sofort samt Denk- und nativer Reasoning-Spur in der DB."""

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
    gespraechsschritt_ausfuehren(sink, vignette, kern, konfiguration, eingabe="Warum?")

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
    gespraechsschritt_ausfuehren(sink, vignette, kern, konfiguration, eingabe="Warum?")

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
def test_scratch_und_db_sink_schliessen_mit_diagnose_gleich_ab() -> None:
    """Eine Diagnose vollzieht an beiden Sink-Zielen denselben Abschlussübergang."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        sink.diagnose_setzen("Zähler und Nenner werden addiert.")

    assert scratch.session["probelauf"]["status"] == Sitzung.Status.ABGESCHLOSSEN
    assert Sitzung.objects.get().status == Sitzung.Status.ABGESCHLOSSEN


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
            sink, vignette, kern, konfiguration, eingabe="Warum?"
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


@pytest.mark.django_db
def test_scratch_und_db_sink_pausieren_und_messen_zeit_paritaetisch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Beide Sink-Adapter führen die unsichtbare Uhr und messen dieselbe Zeit."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 10
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    for sink in (
        ScratchSink(SessionStore()),
        DBSink(Teilnahme.objects.create(), session=SessionStore()),
    ):
        zeiten = iter([100.0, 105.0, 120.0, 125.0])
        monkeypatch.setattr("sitzungen.sink.monotonic", lambda: next(zeiten))

        sitzung_starten(sink, vignette, kern, konfiguration)

        sink.zeitbudget_fortsetzen()
        sink.zeitbudget_anhalten()
        assert sink.verbrauchte_zeit == 5.0

        # Die Pause zwischen 105.0 und 120.0 zählt nicht zum Verbrauch.
        sink.zeitbudget_fortsetzen()
        sink.zeitbudget_anhalten()
        assert sink.verbrauchte_zeit == 10.0


@pytest.mark.django_db
def test_scratch_und_db_sink_pruefen_budget_paritaetisch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Beide Sink-Adapter prüfen Schritt- und Zeitbudget nach denselben Regeln."""

    vignette_schritte, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "Denken", "aeusserung": "Antwort"}] * 2
    )
    vignette_schritte.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette_schritte.budget_wert = 1
    vignette_schritte.save(update_fields=["budget_typ", "budget_wert"])

    vignette_zeit = Vignette.objects.anlegen(
        Konto.objects.create_user(username="grace")
    )
    vignette_zeit.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette_zeit.budget_wert = 5
    vignette_zeit.save(update_fields=["budget_typ", "budget_wert"])

    vignette_ohne_budget = Vignette.objects.anlegen(
        Konto.objects.create_user(username="ada_ohne_budget")
    )
    vignette_ohne_budget.budget_wert = None
    vignette_ohne_budget.save(update_fields=["budget_wert"])

    for sink in (
        ScratchSink(SessionStore()),
        DBSink(Teilnahme.objects.create(), session=SessionStore()),
    ):
        sitzung_starten(sink, vignette_schritte, kern, konfiguration)
        assert not sink.budget_erschoepft(vignette_schritte)
        assert not sink.budget_erschoepft(vignette_ohne_budget)

        gespraechsschritt_ausfuehren(
            sink, vignette_schritte, kern, konfiguration, eingabe="Warum?"
        )
        assert sink.budget_erschoepft(vignette_schritte)
        assert not sink.budget_erschoepft(vignette_ohne_budget)

    for sink in (
        ScratchSink(SessionStore()),
        DBSink(Teilnahme.objects.create(), session=SessionStore()),
    ):
        zeiten = iter([100.0, 105.0])
        monkeypatch.setattr("sitzungen.sink.monotonic", lambda: next(zeiten))

        sitzung_starten(sink, vignette_zeit, kern, konfiguration)
        assert not sink.budget_erschoepft(vignette_zeit)

        sink.zeitbudget_fortsetzen()
        sink.zeitbudget_anhalten()
        assert sink.budget_erschoepft(vignette_zeit)


@pytest.mark.django_db
def test_sitzung_beenden_haelt_das_zeitbudget_an(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Das Beenden einer Sitzung stoppt die laufende Uhr beider Sinks."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 10
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    for sink in (
        ScratchSink(SessionStore()),
        DBSink(Teilnahme.objects.create(), session=SessionStore()),
    ):
        zeiten = iter([100.0, 107.0])
        monkeypatch.setattr("sitzungen.sink.monotonic", lambda: next(zeiten))

        sitzung_starten(sink, vignette, kern, konfiguration)
        sink.zeitbudget_fortsetzen()
        sitzung_beenden(sink)

        assert sink.verbrauchte_zeit == 7.0


@pytest.mark.django_db
def test_sitzung_abbrechen_haelt_die_uhr_an_und_setzt_status_abgebrochen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Das Abbrechen hält die Uhr an und markiert die Sitzung als abgebrochen."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 10
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    sink: DBSink = DBSink(Teilnahme.objects.create(), session=SessionStore())
    zeiten = iter([100.0, 103.0])
    monkeypatch.setattr("sitzungen.sink.monotonic", lambda: next(zeiten))

    sitzung_starten(sink, vignette, kern, konfiguration)
    sink.zeitbudget_fortsetzen()
    sitzung_abbrechen(sink)

    assert sink.verbrauchte_zeit == 3.0
    assert Sitzung.objects.get().status == Sitzung.Status.ABGEBROCHEN


@pytest.mark.django_db
def test_modellverlauf_ist_fuer_beide_sinks_derselbe() -> None:
    """Probelauf und persistierte Sitzung reichen dem Modell denselben Verlauf."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "Ich addiere alles.", "aeusserung": "2/5."}]
    )
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Warum?"
        )
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Und dann?"
        )

    erwartet: list[tuple[str, str]] = [
        ("Warum?", "2/5."),
        ("Und dann?", "2/5."),
    ]
    assert modellverlauf(scratch) == erwartet
    assert modellverlauf(datenbank) == erwartet


@pytest.mark.django_db
def test_modellverlauf_laesst_die_denkspur_draussen() -> None:
    """Die Denkspur fließt in keinem der beiden Pfade in den Kontext zurück (ADR-0005)."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [
            {
                "denkspur": "Ich addiere Zähler und Nenner.",
                "aeusserung": "2/5.",
                "native_reasoning_spur": "Native Spur.",
            }
        ]
    )
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Warum?"
        )

        gesagtes: str = " ".join(teil for paar in modellverlauf(sink) for teil in paar)
        assert "Ich addiere Zähler und Nenner." not in gesagtes
        assert "Native Spur." not in gesagtes
        assert "2/5." in gesagtes


@pytest.mark.django_db
def test_modellverlauf_laesst_schritt_ohne_aeusserung_draussen() -> None:
    """Ein antwortloser Schritt bleibt aus dem Verlauf, aber im Transkript (ADR-0011)."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"fehler": "anbieterfehler"}] * 3
    )
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Warum?"
        )

        assert modellverlauf(sink) == []
        assert len(list(sink.gespraechsschritte)) == 1

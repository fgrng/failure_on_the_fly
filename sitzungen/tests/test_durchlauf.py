"""Tests des Sitzungslaufs über seinen beiden Sinks."""

from datetime import UTC, datetime

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
    Ausgang,
    gespraechsschritt_ausfuehren,
    modellverlauf,
    sitzung_abbrechen,
    sitzung_beenden,
    sitzung_starten,
)
from sitzungen.sink import Budgetstand, DBSink, ScratchSink
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


def _verbrauchte_zeit(sink: ScratchSink | DBSink, session: SessionStore) -> float:
    # Liest den Speichervertrag beider Adapter für die Uhrenparität.

    if isinstance(sink, ScratchSink):
        return session["probelauf"]["verbrauchte_zeit"]
    return session[f"sitzung_{sink.sitzung.pk}_verbrauchte_zeit"]


def test_budgetstand_bucht_nur_die_offene_spanne_und_prueft_budget() -> None:
    """Der Budgetstand zählt Züge und Zeit unabhängig von seinem Speicherort."""

    beginn: datetime = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)
    budgetstand: Budgetstand = Budgetstand()

    budgetstand.zug_beginnen(beginn)
    budgetstand.zug_beenden(datetime(2026, 9, 22, 10, 0, 4, tzinfo=UTC))
    budgetstand.gespraechsschritt_anhaengen()

    assert budgetstand.verbrauchte_zeit == 4.0
    assert budgetstand.ist_erschoepft(Vignette.BudgetTyp.ZEIT, 4)
    assert budgetstand.ist_erschoepft(Vignette.BudgetTyp.SCHRITTE, 1)


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
            "eingabemodus": "getippt",
            "denkspur": "Ich addiere.",
            "aeusserung": "2/5.",
            "fehlversuche": [
                {"grund": "Formatbruch", "rohantwort": "keine JSON-Antwort"}
            ],
        }
    ]


@pytest.mark.django_db
def test_db_sink_persistiert_einen_erfolgreichen_gespraechsschritt() -> None:
    """Ein geglückter Gesprächsschritt steht sofort samt seiner Denkspur in der DB."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [
            {
                "denkspur": "Ich addiere Zähler und Nenner.",
                "aeusserung": "2/5.",
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
        )
    ) == [
        {
            "reihenfolge": 1,
            "eingabe": "Wie hast du gerechnet?",
            "denkspur": "Ich addiere Zähler und Nenner.",
            "aeusserung": "2/5.",
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
            },
        ]
    )
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        gespraechsschritt_ausfuehren(
            sink,
            vignette,
            kern,
            konfiguration,
            eingabe="Warum?",
            eingabemodus="transkribiert",
        )

    db_schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
    db_struktur = [
        {
            "reihenfolge": db_schritt.reihenfolge,
            "eingabe": db_schritt.eingabe,
            "eingabemodus": db_schritt.eingabemodus,
            "denkspur": db_schritt.denkspur,
            "aeusserung": db_schritt.aeusserung,
            "fehlversuche": list(
                Fehlversuch.objects.filter(gespraechsschritt=db_schritt).values(
                    "grund", "rohantwort"
                )
            ),
        }
    ]

    assert scratch.gespraechsschritte == db_struktur


@pytest.mark.django_db
def test_scratch_und_db_sink_messen_zeit_paritaetisch() -> None:
    """Beide Sink-Adapter führen denselben Budgetstand über explizite Zeitpunkte."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 10
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    for sink, session in (
        (ScratchSink(SessionStore()), SessionStore()),
        (DBSink(Teilnahme.objects.create()), SessionStore()),
    ):
        sink.session = session
        sitzung_starten(sink, vignette, kern, konfiguration)

        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 5, tzinfo=UTC))
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 1, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 1, 5, tzinfo=UTC))

        assert sink.gespraechsschritt_anhaengen(
            eingabe="Warum?",
            eingabemodus="getippt",
            denkspur="",
            aeusserung="",
            fehlversuche=[],
        )
        assert _verbrauchte_zeit(sink, session) == 10.0


@pytest.mark.django_db
def test_erneutes_anzeigen_setzt_die_offene_spanne_in_beiden_sinks_neu_an() -> None:
    """Beim Reload bleibt der Verbrauch erhalten, die zuvor offene Zeit aber ungebucht."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 3
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    for sink, session in (
        (ScratchSink(SessionStore()), SessionStore()),
        (DBSink(Teilnahme.objects.create()), SessionStore()),
    ):
        sink.session = session
        sitzung_starten(sink, vignette, kern, konfiguration)
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 1, tzinfo=UTC))
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, 10, tzinfo=UTC))
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, 20, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 22, tzinfo=UTC))

        assert sink.gespraechsschritt_anhaengen(
            eingabe="Warum?",
            eingabemodus="getippt",
            denkspur="",
            aeusserung="",
            fehlversuche=[],
        )
        assert _verbrauchte_zeit(sink, session) == 3.0


@pytest.mark.django_db
def test_scratch_und_db_sink_pruefen_schrittbudget_paritaetisch() -> None:
    """Der Rückgabewert nach einem Schritt meldet die Erschöpfung beider Sinks."""

    vignette_schritte, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "Denken", "aeusserung": "Antwort"}] * 2
    )
    vignette_schritte.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette_schritte.budget_wert = 1
    vignette_schritte.save(update_fields=["budget_typ", "budget_wert"])

    for sink in (
        ScratchSink(SessionStore()),
        DBSink(Teilnahme.objects.create(), session=SessionStore()),
    ):
        sitzung_starten(sink, vignette_schritte, kern, konfiguration)
        assert sink.gespraechsschritt_anhaengen(
            eingabe="Warum?",
            eingabemodus="getippt",
            denkspur="",
            aeusserung="",
            fehlversuche=[],
        )


@pytest.mark.django_db
def test_sitzung_beenden_beendet_die_offene_spanne(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Das Beenden delegiert das Buchen an den Sink."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 10
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    monkeypatch.setattr(
        "sitzungen.durchlauf._jetzt",
        lambda: datetime(2026, 9, 22, 10, 0, 7, tzinfo=UTC),
    )
    for sink, session in (
        (ScratchSink(SessionStore()), SessionStore()),
        (DBSink(Teilnahme.objects.create()), SessionStore()),
    ):
        sink.session = session
        sitzung_starten(sink, vignette, kern, konfiguration)
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sitzung_beenden(sink)
        assert _verbrauchte_zeit(sink, session) == 7.0


@pytest.mark.django_db
def test_sitzung_abbrechen_beendet_die_offene_spanne_und_setzt_status_abgebrochen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Das Abbrechen hält die Uhr an und markiert die Sitzung als abgebrochen."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 10
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    session: SessionStore = SessionStore()
    sink: DBSink = DBSink(Teilnahme.objects.create(), session=session)
    monkeypatch.setattr(
        "sitzungen.durchlauf._jetzt",
        lambda: datetime(2026, 9, 22, 10, 0, 3, tzinfo=UTC),
    )
    sitzung_starten(sink, vignette, kern, konfiguration)
    sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
    sitzung_abbrechen(sink)

    assert _verbrauchte_zeit(sink, session) == 3.0
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

    assert len(list(datenbank.gespraechsschritte)) == 1


@pytest.mark.django_db
def test_gespraechsschritt_meldet_fortgesetztes_gespraech_fuer_beide_sinks() -> None:
    """Ein geglückter Schritt im Budget hält das Gespräch für beide Sinks offen."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "Meine Regel.", "aeusserung": "2/5."}]
    )

    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create(), session=SessionStore())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)

        ausgang: Ausgang = gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Warum?"
        )

        assert ausgang is Ausgang.FORTGESETZT


@pytest.mark.django_db
def test_gescheiterter_schritt_meldet_denselben_ausgang_und_wird_je_sink_behandelt() -> (
    None
):
    """Der Probelauf verwirft den gescheiterten Schritt, die Sitzung behält ihn (ADR-0011)."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"fehler": "anbieterfehler"}] * 3
    )
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create(), session=SessionStore())

    ausgaenge: list[Ausgang] = []
    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        ausgaenge.append(
            gespraechsschritt_ausfuehren(
                sink, vignette, kern, konfiguration, eingabe="Warum?"
            )
        )

    assert ausgaenge == [Ausgang.GESCHEITERT, Ausgang.GESCHEITERT]
    assert scratch.gespraechsschritte == []
    assert Sitzung.objects.get().status == Sitzung.Status.GESCHEITERT
    assert Gespraechsschritt.objects.get().aeusserung is None


@pytest.mark.django_db
def test_erschoepftes_budget_meldet_seinen_ausgang_und_schliesst_nur_den_probelauf_ab() -> (
    None
):
    """Das Budget beendet das Gespräch; die persistierte Sitzung schließt erst die Diagnose ab."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "Meine Regel.", "aeusserung": "2/5."}] * 2
    )
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 1
    vignette.save(update_fields=["budget_typ", "budget_wert"])
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create(), session=SessionStore())

    ausgaenge: list[Ausgang] = []
    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, kern, konfiguration)
        ausgaenge.append(
            gespraechsschritt_ausfuehren(
                sink, vignette, kern, konfiguration, eingabe="Warum?"
            )
        )

    assert ausgaenge == [Ausgang.BUDGET_ERSCHOEPFT, Ausgang.BUDGET_ERSCHOEPFT]
    assert scratch.ist_beendet
    assert Sitzung.objects.get().status == Sitzung.Status.LAUFEND

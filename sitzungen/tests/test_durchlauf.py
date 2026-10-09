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
    rahmenhandlung_rendern,
    sitzung_abbrechen,
    sitzung_beenden,
    sitzung_starten,
)
from sitzungen.sink import (
    Budgetstand,
    DBSink,
    FluechtigerSink,
    GeruestSink,
    ScratchSink,
    SitzungSink,
)
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
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={"skript": skript},
        ),
    )


def _senken() -> list[ScratchSink | DBSink | FluechtigerSink]:
    # Je eine frische Senke jeder Art für die Paritätstests.

    return [
        ScratchSink(SessionStore()),
        DBSink(Teilnahme.objects.create()),
        FluechtigerSink(Teilnahme.objects.create(), SessionStore()),
    ]


def _verbrauchte_zeit(sink: GeruestSink) -> float:
    # Liest den exportierten Budgetstand der Sitzungszeile.

    sitzung: Sitzung = Sitzung.objects.get(teilnahme=sink.teilnahme)
    return sitzung.verbrauchte_zeit


def _leeren_schritt_anhaengen(sink: SitzungSink) -> bool:
    # Hängt einen geglückten Schritt an und meldet die Budgeterschöpfung.

    return sink.gespraechsschritt_anhaengen(
        eingabe="Warum?",
        eingabemodus="getippt",
        denkspur="",
        aeusserung="",
        fehlversuche=[],
    )


@pytest.mark.django_db
def test_sitzung_starten_lehnt_vignette_ohne_gepinnten_kern_ab() -> None:
    """Ohne Pin entsteht keine persistierte Sitzung."""

    vignette, _, konfiguration = _persistierbares_tripel([])
    vignette.gepinnter_kern = None
    vignette.save(update_fields=["gepinnter_kern"])

    with pytest.raises(RuntimeError, match="gepinnten Simulationskern"):
        sitzung_starten(DBSink(Teilnahme.objects.create()), vignette, konfiguration)

    assert not Sitzung.objects.exists()


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
    kern: Simulationskern = Simulationskern(user_prompt_vorlage="$lernauftrag")
    vignette: Vignette = Vignette(
        lernauftrag_text="Addiere zwei Brüche.", gepinnter_kern=kern
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration(
        sprachmodell="fake",
        parameter={
            "skript": [
                {"fehler": "formatbruch", "rohantwort": "keine JSON-Antwort"},
                {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
            ]
        },
    )

    sitzung_starten(sink, vignette, konfiguration)
    gespraechsschritt_ausfuehren(
        sink,
        vignette,
        kern,
        konfiguration,
        eingabe="Wie hast du gerechnet?",
    )

    assert sink.gespraechsschritte == [
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

    sitzung_starten(sink, vignette, konfiguration)
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

    sitzung_starten(sink, vignette, konfiguration)
    gespraechsschritt_ausfuehren(sink, vignette, kern, konfiguration, eingabe="Warum?")

    schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
    assert schritt.aeusserung == "2/5."
    assert list(
        Fehlversuch.objects.filter(gespraechsschritt=schritt).values(
            "grund", "rohantwort"
        )
    ) == [{"grund": "Formatbruch", "rohantwort": "Kein JSON."}]


@pytest.mark.django_db
def test_db_sink_diagnose_schliesst_die_sitzung_ab() -> None:
    """Die gesetzte Diagnose vollzieht den Abschlussübergang der Sitzung."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    sink: DBSink = DBSink(Teilnahme.objects.create())

    sitzung_starten(sink, vignette, konfiguration)
    sink.diagnose_setzen("Zähler und Nenner werden addiert.")

    sitzung: Sitzung = Sitzung.objects.get()
    assert sitzung.status == Sitzung.Status.ABGESCHLOSSEN
    assert (
        Diagnose.objects.get(sitzung=sitzung).text
        == "Zähler und Nenner werden addiert."
    )


@pytest.mark.django_db
def test_scratch_sink_schliesst_mit_diagnose_ab() -> None:
    """Auch der Probelauf ist nach der Diagnose beendet."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    scratch: ScratchSink = ScratchSink(SessionStore())

    sitzung_starten(scratch, vignette, konfiguration)
    scratch.diagnose_setzen("Zähler und Nenner werden addiert.")

    assert scratch.ist_beendet


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
        sitzung_starten(sink, vignette, konfiguration)
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
def test_zeitbudget_ist_von_jeder_anderen_sitzung_getrennt() -> None:
    """Der Zeitstand hängt an seiner Sitzungszeile und an keiner zweiten."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    sink: DBSink = DBSink(Teilnahme.objects.create())
    anderer_sink: DBSink = DBSink(Teilnahme.objects.create())
    sitzung_starten(sink, vignette, konfiguration)
    sitzung_starten(anderer_sink, vignette, konfiguration)

    sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
    sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 4, tzinfo=UTC))

    assert _verbrauchte_zeit(sink) == 4.0
    assert _verbrauchte_zeit(anderer_sink) == 0.0


@pytest.mark.django_db
@pytest.mark.parametrize(("budget", "erschoepft"), [(10, True), (11, False)])
def test_scratch_und_db_sink_messen_zeit_paritaetisch(
    budget: int, erschoepft: bool
) -> None:
    """Alle Senken führen denselben Budgetstand über explizite Zeitpunkte."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = budget
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    for sink in _senken():
        sitzung_starten(sink, vignette, konfiguration)

        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 5, tzinfo=UTC))
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 1, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 1, 5, tzinfo=UTC))

        assert _leeren_schritt_anhaengen(sink) is erschoepft
        if isinstance(sink, GeruestSink):
            assert _verbrauchte_zeit(sink) == 10.0


@pytest.mark.django_db
def test_schrittbudget_laesst_die_uhr_in_beiden_sinks_stehen() -> None:
    """Ein schrittbasiertes Budget zählt Schritte, es bucht keine Sekunden."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 3
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    for sink in (
        DBSink(Teilnahme.objects.create()),
        FluechtigerSink(Teilnahme.objects.create(), SessionStore()),
    ):
        sitzung_starten(sink, vignette, konfiguration)

        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 5, tzinfo=UTC))

        assert _verbrauchte_zeit(sink) == 0.0


@pytest.mark.django_db
def test_erneutes_anzeigen_setzt_die_offene_spanne_in_beiden_sinks_neu_an() -> None:
    """Beim Reload bleibt der Verbrauch erhalten, die zuvor offene Zeit aber ungebucht."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 4
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    for sink in _senken():
        sitzung_starten(sink, vignette, konfiguration)
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 1, tzinfo=UTC))
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, 10, tzinfo=UTC))
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, 20, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 22, tzinfo=UTC))

        assert not _leeren_schritt_anhaengen(sink)
        if isinstance(sink, GeruestSink):
            assert _verbrauchte_zeit(sink) == 3.0


@pytest.mark.django_db
def test_sitzung_beenden_beendet_die_offene_spanne(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Das Beenden delegiert das Buchen an den Sink."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 7
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    monkeypatch.setattr(
        "sitzungen.durchlauf.jetzt",
        lambda: datetime(2026, 9, 22, 10, 0, 7, tzinfo=UTC),
    )
    datenbank: DBSink = DBSink(Teilnahme.objects.create())
    for sink in (ScratchSink(SessionStore()), datenbank):
        sitzung_starten(sink, vignette, konfiguration)
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sitzung_beenden(sink)
        assert _leeren_schritt_anhaengen(sink)
    assert _verbrauchte_zeit(datenbank) == 7.0


@pytest.mark.django_db
def test_sitzung_abbrechen_beendet_die_offene_spanne_und_setzt_status_abgebrochen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Das Abbrechen hält die Uhr an und markiert die Sitzung als abgebrochen."""

    vignette, kern, konfiguration = _persistierbares_tripel([])
    vignette.budget_typ = Vignette.BudgetTyp.ZEIT
    vignette.budget_wert = 10
    vignette.save(update_fields=["budget_typ", "budget_wert"])

    sink: DBSink = DBSink(Teilnahme.objects.create())
    monkeypatch.setattr(
        "sitzungen.durchlauf.jetzt",
        lambda: datetime(2026, 9, 22, 10, 0, 3, tzinfo=UTC),
    )
    sitzung_starten(sink, vignette, konfiguration)
    sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
    sitzung_abbrechen(sink)

    assert _verbrauchte_zeit(sink) == 3.0
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
        sitzung_starten(sink, vignette, konfiguration)
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
def test_modellverlauf_laesst_schritt_ohne_aeusserung_draussen() -> None:
    """Ein antwortloser Schritt bleibt aus dem Verlauf, aber im Transkript (ADR-0011)."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"fehler": "anbieterfehler"}] * 3
    )
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, konfiguration)
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Warum?"
        )

        assert modellverlauf(sink) == []

    assert len(list(datenbank.gespraechsschritte)) == 1


@pytest.mark.django_db
def test_leere_aeusserung_bleibt_im_modellverlauf() -> None:
    """Auch eine leere sichtbare Äußerung ist Teil des Verlaufs."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "still", "aeusserung": ""}]
    )

    for sink in _senken():
        sitzung_starten(sink, vignette, konfiguration)
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Erster Schritt"
        )

        assert modellverlauf(sink) == [("Erster Schritt", "")]


@pytest.mark.django_db
def test_gespraechsschritt_meldet_fortgesetztes_gespraech_fuer_beide_sinks() -> None:
    """Ein geglückter Schritt im Budget hält das Gespräch für beide Sinks offen."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "Meine Regel.", "aeusserung": "2/5."}]
    )

    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, konfiguration)

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
    datenbank: DBSink = DBSink(Teilnahme.objects.create())

    ausgaenge: list[Ausgang] = []
    for sink in (scratch, datenbank):
        sitzung_starten(sink, vignette, konfiguration)
        ausgaenge.append(
            gespraechsschritt_ausfuehren(
                sink, vignette, kern, konfiguration, eingabe="Warum?"
            )
        )

    assert ausgaenge == [Ausgang.GESCHEITERT, Ausgang.GESCHEITERT]
    assert scratch.gespraechsschritte == []
    assert Sitzung.objects.get().status == Sitzung.Status.GESCHEITERT
    schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
    assert (schritt.denkspur, schritt.aeusserung) == (None, None)
    assert Fehlversuch.objects.filter(gespraechsschritt=schritt).count() == 3


@pytest.mark.django_db
def test_erschoepftes_budget_meldet_seinen_ausgang_und_schliesst_nur_den_probelauf_ab() -> (
    None
):
    """Das Budget beendet das Gespräch; die persistierte Sitzung schließt erst die Diagnose ab."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"denkspur": "Meine Regel.", "aeusserung": "2/5."}] * 3
    )
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 1
    vignette.save(update_fields=["budget_typ", "budget_wert"])
    scratch: ScratchSink = ScratchSink(SessionStore())
    datenbank: DBSink = DBSink(Teilnahme.objects.create())
    fluechtig: FluechtigerSink = FluechtigerSink(
        Teilnahme.objects.create(), SessionStore()
    )

    ausgaenge: list[Ausgang] = []
    for sink in (scratch, datenbank, fluechtig):
        sitzung_starten(sink, vignette, konfiguration)
        ausgaenge.append(
            gespraechsschritt_ausfuehren(
                sink, vignette, kern, konfiguration, eingabe="Warum?"
            )
        )

    assert ausgaenge == [Ausgang.BUDGET_ERSCHOEPFT] * 3
    assert scratch.ist_beendet
    assert list(Sitzung.objects.values_list("status", flat=True)) == [
        Sitzung.Status.LAUFEND,
        Sitzung.Status.LAUFEND,
    ]


@pytest.mark.django_db
def test_fluechtiger_sink_haelt_den_verlauf_nur_in_der_session() -> None:
    """Die Sitzung steht mit Status in der DB, ihr Gespräch nur in der Session."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [
            {"fehler": "formatbruch", "rohantwort": "Kein JSON."},
            {"denkspur": "Meine Regel.", "aeusserung": "2/5."},
        ]
    )
    session: SessionStore = SessionStore()
    sink: FluechtigerSink = FluechtigerSink(Teilnahme.objects.create(), session)

    sitzung_starten(sink, vignette, konfiguration)
    gespraechsschritt_ausfuehren(
        sink,
        vignette,
        kern,
        konfiguration,
        eingabe="Warum?",
        eingabemodus="transkribiert",
    )
    sink.diagnose_setzen("Zähler und Nenner werden addiert.")

    assert not Gespraechsschritt.objects.exists()
    assert not Fehlversuch.objects.exists()
    assert not Diagnose.objects.exists()
    sitzung: Sitzung = Sitzung.objects.get()
    assert sitzung.status == Sitzung.Status.ABGESCHLOSSEN
    wiederhergestellt: FluechtigerSink = FluechtigerSink.fuer_sitzung(sitzung, session)
    assert wiederhergestellt.gespraechsschritte == [
        {
            "reihenfolge": 1,
            "eingabe": "Warum?",
            "eingabemodus": "transkribiert",
            "denkspur": "Meine Regel.",
            "aeusserung": "2/5.",
            "fehlversuche": [{"grund": "Formatbruch", "rohantwort": "Kein JSON."}],
        }
    ]
    assert wiederhergestellt.abgegebene_diagnose == "Zähler und Nenner werden addiert."


@pytest.mark.django_db
def test_fluechtiger_sink_haelt_den_gescheiterten_schritt_nur_in_der_session() -> None:
    """Der Abbruchschritt steht im Verlauf der Session, der Status in der DB."""

    vignette, kern, konfiguration = _persistierbares_tripel(
        [{"fehler": "anbieterfehler"}] * 3
    )
    session: SessionStore = SessionStore()
    sink: FluechtigerSink = FluechtigerSink(Teilnahme.objects.create(), session)

    sitzung_starten(sink, vignette, konfiguration)
    ausgang: Ausgang = gespraechsschritt_ausfuehren(
        sink, vignette, kern, konfiguration, eingabe="Warum?"
    )

    assert ausgang is Ausgang.GESCHEITERT
    assert not Gespraechsschritt.objects.exists()
    assert not Fehlversuch.objects.exists()
    assert Sitzung.objects.get().status == Sitzung.Status.GESCHEITERT
    [schritt] = FluechtigerSink.fuer_sitzung(
        Sitzung.objects.get(), session
    ).gespraechsschritte
    assert (schritt["eingabe"], schritt["aeusserung"]) == ("Warum?", None)
    assert len(schritt["fehlversuche"]) == 3


@pytest.mark.django_db
def test_rahmenhandlung_escaped_vignettenwerte_und_rendert_das_markdown_des_kerns() -> (
    None
):
    """Nur das Markdown des Kerns wirkt, Vignettenwerte erscheinen wörtlich."""

    vignette, _, _ = _persistierbares_tripel([])
    vignette.thema = "*Brüche* _kürzen_"
    vignette.fach = "[Mathe](https://example.org)"

    html: str = rahmenhandlung_rendern(
        "# Hospitation\n\nThema: **$thema**\nFach: $fach", vignette
    )

    assert "<h3>Hospitation</h3>" in html
    assert "<strong>*Brüche* _kürzen_</strong>" in html
    assert "Fach: [Mathe](https://example.org)</p>" in html
    assert "<a " not in html


@pytest.mark.django_db
def test_rahmenhandlung_link_syntax_des_kerns_bleibt_woertlich() -> None:
    """Die Rahmenhandlung ist Szenentext: Links des Kerns entstehen nicht."""

    vignette, _, _ = _persistierbares_tripel([])
    vignette.thema = "Brüche"

    html: str = rahmenhandlung_rendern("[$thema](https://example.org)", vignette)

    assert html == "<p>[Brüche](https://example.org)</p>\n"

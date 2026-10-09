"""Lebenszyklus und Vertrag des Evalkatalogs (ADR-0046, ADR-0035, ADR-0010)."""

from collections.abc import Callable

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction

from simulation.models import (
    Eval,
    Evalkatalog,
    Evalinput,
    Evalkriterium,
    Inputschritt,
    UebergreifendesKriterium,
)
from simulation.tests.evalkatalog_bau import (
    FUELLTEXT,
    vervollstaendigen,
    vollstaendiger_katalog,
)


@pytest.mark.django_db
def test_anlegen_legt_einen_leeren_entwurf_mit_k_drei_an() -> None:
    """Der erste Katalog beginnt als Entwurf ohne Vorlagen; *k* startet bei 3."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()

    assert katalog.zustand == Evalkatalog.Zustand.ENTWURF
    assert katalog.k == 3
    assert katalog.lehrperson_vorlage == ""
    assert katalog.bewerter_vorlage == ""


@pytest.mark.django_db
def test_anlegen_lehnt_einen_zweiten_entwurf_ab() -> None:
    """Solange die Linie eine Fassung trägt, entsteht keine zweite erste."""

    Evalkatalog.objects.anlegen()

    with pytest.raises(
        ValidationError, match="Der Evalkatalog wurde bereits angelegt."
    ):
        Evalkatalog.objects.anlegen()
    assert Evalkatalog.objects.count() == 1


@pytest.mark.django_db
def test_anlegen_ist_nach_dem_verwerfen_wieder_moeglich() -> None:
    """Ein verworfener Entwurf hinterlässt eine leere Linie."""

    Evalkatalog.objects.anlegen().delete()

    Evalkatalog.objects.anlegen()

    assert Evalkatalog.objects.count() == 1


@pytest.mark.django_db
def test_direktes_anlegen_wird_abgelehnt() -> None:
    """Fassungen entstehen nur über die Anlege-Naht."""

    with pytest.raises(RuntimeError, match="Evalkatalog-Fassungen"):
        Evalkatalog.objects.create()


@pytest.mark.django_db
def test_linie_hat_hoechstens_einen_entwurf() -> None:
    """Auch am Lebenszyklus vorbei duldet die Datenbank keinen zweiten Entwurf."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()

    with pytest.raises(IntegrityError), transaction.atomic():
        models.QuerySet(model=Evalkatalog).bulk_create(
            [Evalkatalog(historie=katalog.historie)]
        )


@pytest.mark.django_db
def test_kriterien_stehen_in_der_reihenfolge_des_anlegens() -> None:
    """Ein neues übergreifendes Kriterium reiht sich am Ende ein."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    katalog.kriterium_anlegen("Rollentreue")
    katalog.kriterium_anlegen("Kein Verraten der Regel")

    assert [k.text for k in katalog.uebergreifende_kriterien.all()] == [
        "Rollentreue",
        "Kein Verraten der Regel",
    ]


@pytest.mark.django_db
def test_verschieben_tauscht_mit_der_nachbarin_und_bleibt_gespeichert() -> None:
    """Hoch und Runter tauschen die Plätze; am Rand bleibt alles, wie es ist."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    erstes: UebergreifendesKriterium = katalog.kriterium_anlegen("A")
    katalog.kriterium_anlegen("B")
    drittes: UebergreifendesKriterium = katalog.kriterium_anlegen("C")

    drittes.verschieben(-1)
    erstes.verschieben(-1)

    assert [k.text for k in katalog.uebergreifende_kriterien.all()] == ["A", "C", "B"]


@pytest.mark.django_db
def test_kriterien_einer_finalen_fassung_sind_unveraenderlich() -> None:
    """Nur am Entwurf lassen sich Kriterien ändern, anlegen oder löschen."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    kriterium: UebergreifendesKriterium = katalog.kriterium_anlegen("Rollentreue")
    vervollstaendigen(katalog).finalisieren()

    kriterium.text = "geändert"
    with pytest.raises(ValidationError, match="Entwurf"):
        kriterium.save()
    with pytest.raises(ValidationError, match="Entwurf"):
        kriterium.delete()
    with pytest.raises(ValidationError, match="Entwurf"):
        katalog.kriterium_anlegen("neu")


@pytest.mark.django_db
def test_neuer_entwurf_uebernimmt_die_kriterien_ohne_die_vorgaengerin_zu_beruehren() -> (
    None
):
    """Die Tiefenkopie trägt die Kriterien in gleicher Reihenfolge weiter."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    katalog.kriterium_anlegen("A")
    katalog.kriterium_anlegen("B")
    vervollstaendigen(katalog).finalisieren()

    entwurf: Evalkatalog = katalog.bearbeiten()
    kopie: UebergreifendesKriterium = entwurf.uebergreifende_kriterien.first()
    kopie.text = "A2"
    kopie.save()

    assert [k.text for k in entwurf.uebergreifende_kriterien.all()] == ["A2", "B"]
    assert [k.text for k in katalog.uebergreifende_kriterien.all()] == ["A", "B"]


@pytest.mark.django_db
def test_kriterien_einer_finalen_fassung_widerstehen_massenaenderungen() -> None:
    """Auch gesammelt lassen sich Kriterien einer finalen Fassung nicht ändern."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    katalog.kriterium_anlegen("Rollentreue")
    vervollstaendigen(katalog).finalisieren()

    with pytest.raises(RuntimeError, match="Entwurf"):
        UebergreifendesKriterium.objects.filter(katalog=katalog).update(text="x")
    with pytest.raises(ValidationError, match="Entwurf"):
        UebergreifendesKriterium.objects.filter(katalog=katalog).delete()


@pytest.mark.django_db
def test_kriterium_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf() -> None:
    """Das Umhängen nähme der finalen Fassung ein Kriterium weg."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    kriterium: UebergreifendesKriterium = katalog.kriterium_anlegen("Rollentreue")
    vervollstaendigen(katalog).finalisieren()
    kriterium.katalog = katalog.bearbeiten()
    kriterium.position = 99

    with pytest.raises(ValidationError, match="Entwurf"):
        kriterium.save()


@pytest.mark.django_db
def test_evals_stehen_in_der_reihenfolge_des_anlegens_und_lassen_sich_umordnen() -> (
    None
):
    """Ein neues Eval reiht sich am Ende ein; Hoch und Runter tauschen Plätze."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    katalog.eval_anlegen("A")
    katalog.eval_anlegen("B")
    drittes: Eval = katalog.eval_anlegen("C")

    drittes.verschieben(-1)

    assert [e.name for e in katalog.evals.all()] == ["A", "C", "B"]


@pytest.mark.django_db
def test_evalkriterien_haengen_am_eval_und_lassen_sich_umordnen() -> None:
    """Jedes Eval ordnet seine eigenen Kriterien, unabhängig von den anderen."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    eval_: Eval = katalog.eval_anlegen("Muster")
    anderes: Eval = katalog.eval_anlegen("Andere")
    erstes: Evalkriterium = eval_.kriterium_anlegen("A")
    eval_.kriterium_anlegen("B")
    anderes.kriterium_anlegen("X")

    erstes.verschieben(1)

    assert [k.text for k in eval_.kriterien.all()] == ["B", "A"]
    assert [k.text for k in anderes.kriterien.all()] == ["X"]


@pytest.mark.django_db
def test_geloeschtes_eval_nimmt_seine_kriterien_mit() -> None:
    """Evalkriterien gibt es nur an ihrem Eval."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    eval_: Eval = katalog.eval_anlegen("Muster")
    eval_.kriterium_anlegen("A")

    eval_.delete()

    assert not Evalkriterium.objects.exists()


@pytest.mark.django_db
def test_evals_und_evalkriterien_einer_finalen_fassung_sind_unveraenderlich() -> None:
    """Evals und ihre Kriterien teilen die Schreibsperre der Fassung."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    eval_: Eval = katalog.eval_anlegen("Muster")
    kriterium: Evalkriterium = eval_.kriterium_anlegen("A")
    vervollstaendigen(katalog).finalisieren()

    eval_.name = "geändert"
    kriterium.text = "geändert"
    for versuch in (
        eval_.save,
        eval_.delete,
        kriterium.save,
        kriterium.delete,
        lambda: katalog.eval_anlegen("neu"),
        lambda: eval_.kriterium_anlegen("neu"),
        lambda: Eval.objects.filter(katalog=katalog).delete(),
        lambda: Evalkriterium.objects.filter(eval=eval_).delete(),
    ):
        with pytest.raises(ValidationError, match="Entwurf"):
            versuch()
    for massenupdate in (
        lambda: Eval.objects.filter(katalog=katalog).update(name="x"),
        lambda: Evalkriterium.objects.filter(eval=eval_).update(text="x"),
    ):
        with pytest.raises(RuntimeError, match="Entwurf"):
            massenupdate()


@pytest.mark.django_db
def test_evalkriterium_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf() -> (
    None
):
    """Auch über das Eval hinweg nimmt das Umhängen der Fassung nichts weg."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    kriterium: Evalkriterium = katalog.eval_anlegen("Muster").kriterium_anlegen("A")
    vervollstaendigen(katalog).finalisieren()
    kriterium.eval = katalog.bearbeiten().evals.get()
    kriterium.position = 99

    with pytest.raises(ValidationError, match="Entwurf"):
        kriterium.save()


@pytest.mark.django_db
def test_neuer_entwurf_uebernimmt_evals_und_evalkriterien() -> None:
    """Die Tiefenkopie trägt Evals samt Kriterien in gleicher Reihenfolge weiter."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    erstes: Eval = katalog.eval_anlegen("Muster")
    erstes.kriterium_anlegen("A")
    erstes.kriterium_anlegen("B")
    katalog.eval_anlegen("Rolle").kriterium_anlegen("C")
    vervollstaendigen(katalog).finalisieren()

    entwurf: Evalkatalog = katalog.bearbeiten()
    kopie: Evalkriterium = entwurf.evals.first().kriterien.first()
    kopie.text = "A2"
    kopie.save()

    def baum(fassung: Evalkatalog) -> list[tuple[str, list[str]]]:
        # Liefert die Evals einer Fassung samt Kriterientexten in Reihenfolge.
        return [
            (e.name, [k.text for k in e.kriterien.all()]) for e in fassung.evals.all()
        ]

    assert baum(entwurf) == [("Muster", ["A2", "B"]), ("Rolle", ["C"])]
    assert baum(katalog) == [("Muster", ["A", "B"]), ("Rolle", ["C"])]


@pytest.mark.django_db
def test_neuer_evalinput_startet_mit_drei_leeren_festen_inputschritten() -> None:
    """Der übliche Fall muss nicht zusammengeklickt werden; ein Eval hat mehrere."""

    eval_: Eval = Evalkatalog.objects.anlegen().eval_anlegen("Muster")
    erster: Evalinput = eval_.input_anlegen()
    zweiter: Evalinput = eval_.input_anlegen()

    assert list(eval_.inputs.all()) == [erster, zweiter]
    assert [(s.art, s.text) for s in erster.schritte.all()] == [
        (Inputschritt.Art.FEST, ""),
    ] * 3


@pytest.mark.django_db
def test_inputschritte_lassen_sich_umordnen_und_tragen_ihre_art() -> None:
    """Hoch und Runter ordnen die Schritte; die Kürzel folgen Art und Reihenfolge."""

    evalinput: Evalinput = (
        Evalkatalog.objects.anlegen().eval_anlegen("Muster").input_anlegen()
    )
    gelenkt: Inputschritt = evalinput.schritt_anlegen(
        Inputschritt.Art.GELENKT, "Nennt sie die Lösung, äußere Zweifel."
    )

    gelenkt.verschieben(-1)

    assert [s.art for s in evalinput.schritte.all()] == [
        Inputschritt.Art.FEST,
        Inputschritt.Art.FEST,
        Inputschritt.Art.GELENKT,
        Inputschritt.Art.FEST,
    ]
    assert evalinput.kuerzel == "FFGF"


@pytest.mark.django_db
def test_geloeschtes_eval_nimmt_seine_evalinputs_mit() -> None:
    """Evalinputs und Inputschritte gibt es nur an ihrem Eval."""

    eval_: Eval = Evalkatalog.objects.anlegen().eval_anlegen("Muster")
    eval_.input_anlegen()

    eval_.delete()

    assert not Evalinput.objects.exists()
    assert not Inputschritt.objects.exists()


@pytest.mark.django_db
def test_geloeschter_evalinput_nimmt_seine_schritte_mit() -> None:
    """Inputschritte gibt es nur an ihrem Evalinput."""

    eval_: Eval = Evalkatalog.objects.anlegen().eval_anlegen("Muster")
    eval_.input_anlegen().delete()

    assert not Inputschritt.objects.exists()


@pytest.mark.django_db
def test_evalinputs_und_inputschritte_einer_finalen_fassung_sind_unveraenderlich() -> (
    None
):
    """Evalinputs und Inputschritte teilen die Schreibsperre der Fassung."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    eval_: Eval = katalog.eval_anlegen("Muster")
    evalinput: Evalinput = eval_.input_anlegen()
    schritt: Inputschritt = evalinput.schritte.first()
    vervollstaendigen(katalog).finalisieren()

    schritt.text = "geändert"
    for versuch in (
        evalinput.save,
        evalinput.delete,
        schritt.save,
        schritt.delete,
        eval_.input_anlegen,
        evalinput.schritt_anlegen,
        lambda: schritt.verschieben(1),
        lambda: Evalinput.objects.filter(eval=eval_).delete(),
        lambda: Inputschritt.objects.filter(evalinput=evalinput).delete(),
    ):
        with pytest.raises(ValidationError, match="Entwurf"):
            versuch()
    with pytest.raises(RuntimeError, match="Entwurf"):
        Inputschritt.objects.filter(evalinput=evalinput).update(text="x")


@pytest.mark.django_db
def test_inputschritt_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf() -> (
    None
):
    """Auch über Evalinput und Eval hinweg nimmt das Umhängen nichts weg."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    schritt: Inputschritt = (
        katalog.eval_anlegen("Muster").input_anlegen().schritte.first()
    )
    vervollstaendigen(katalog).finalisieren()
    schritt.evalinput = katalog.bearbeiten().evals.get().inputs.get()
    schritt.position = 99

    with pytest.raises(ValidationError, match="Entwurf"):
        schritt.save()


@pytest.mark.django_db
def test_neuer_entwurf_uebernimmt_evalinputs_samt_inputschritten() -> None:
    """Die Tiefenkopie trägt jeden Evalinput mit Art und Text seiner Schritte weiter."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    eval_: Eval = katalog.eval_anlegen("Muster")
    eval_.input_anlegen().schritt_anlegen(Inputschritt.Art.GELENKT, "Zweifle")
    eval_.input_anlegen().schritte.first().delete()
    vervollstaendigen(katalog).finalisieren()

    entwurf: Evalkatalog = katalog.bearbeiten()
    kopie: Inputschritt = entwurf.evals.get().inputs.first().schritte.last()
    kopie.text = "Zweifle laut"
    kopie.save()

    def inputs(fassung: Evalkatalog) -> list[list[tuple[str, str]]]:
        # Liefert die Inputschritte jedes Evalinputs des einzigen Evals.
        return [
            [(s.art, s.text) for s in i.schritte.all()]
            for i in fassung.evals.get().inputs.all()
        ]

    # Leere Schritte füllt das Vervollständigen vor dem Finalisieren.
    fest: tuple[str, str] = (Inputschritt.Art.FEST, FUELLTEXT)
    assert inputs(entwurf) == [
        [fest, fest, fest, (Inputschritt.Art.GELENKT, "Zweifle laut")],
        [fest, fest],
    ]
    assert inputs(katalog) == [
        [fest, fest, fest, (Inputschritt.Art.GELENKT, "Zweifle")],
        [fest, fest],
    ]


@pytest.mark.django_db
def test_vollstaendiger_entwurf_wird_final_und_ueberholt_die_vorgaengerin() -> None:
    """Finalisieren lässt genau eine finale Fassung; die bisherige ist überholt."""

    erste: Evalkatalog = vollstaendiger_katalog()
    erste.finalisieren()
    zweite: Evalkatalog = erste.bearbeiten()

    zweite.finalisieren()

    erste.refresh_from_db()
    assert erste.zustand == Evalkatalog.Zustand.ARCHIVIERT
    assert zweite.zustand == Evalkatalog.Zustand.FINAL
    assert Evalkatalog.objects.finale_fassung() == zweite


@pytest.mark.django_db
def test_finalisieren_in_zweitem_tab_lehnt_den_uebergang_ab() -> None:
    """Ein inzwischen finalisierter Entwurf meldet den abgelehnten Übergang."""

    erster_tab: Evalkatalog = vollstaendiger_katalog()
    zweiter_tab: Evalkatalog = Evalkatalog.objects.get(pk=erster_tab.pk)
    zweiter_tab.k = 7
    erster_tab.finalisieren()

    with pytest.raises(ValidationError, match="Nur Entwürfe können finalisiert"):
        zweiter_tab.finalisieren()
    erster_tab.refresh_from_db()
    assert erster_tab.zustand == Evalkatalog.Zustand.FINAL
    assert erster_tab.k == 3


@pytest.mark.django_db
def test_finalisieren_schreibt_den_geprueften_inhalt_mit() -> None:
    """Ungespeicherte Eingaben gehen mit dem Zustandswechsel in die Fassung."""

    katalog: Evalkatalog = vollstaendiger_katalog()
    katalog.k = 5

    katalog.finalisieren()

    katalog.refresh_from_db()
    assert katalog.k == 5


@pytest.mark.django_db
def test_finale_fassung_fehlt_ohne_finalisierten_katalog() -> None:
    """Ohne finale Fassung meldet die Abfrage für andere Apps „keine“."""

    assert Evalkatalog.objects.finale_fassung() is None
    vollstaendiger_katalog()

    assert Evalkatalog.objects.finale_fassung() is None


@pytest.mark.django_db
def test_uebergreifende_kriterien_duerfen_fehlen() -> None:
    """Ein Katalog ohne übergreifende Kriterien ist vollständig."""

    katalog: Evalkatalog = vollstaendiger_katalog()

    katalog.finalisieren()

    assert not katalog.uebergreifende_kriterien.exists()
    assert katalog.zustand == Evalkatalog.Zustand.FINAL


def _ohne_eval(katalog: Evalkatalog) -> None:
    # Löscht das einzige Eval.

    katalog.evals.get().delete()


def _eval_ohne_evalinput(katalog: Evalkatalog) -> None:
    # Löscht den einzigen Evalinput des Evals.

    katalog.evals.get().inputs.get().delete()


def _eval_ohne_evalkriterium(katalog: Evalkatalog) -> None:
    # Löscht das einzige Evalkriterium des Evals.

    katalog.evals.get().kriterien.get().delete()


def _evalinput_ohne_inputschritt(katalog: Evalkatalog) -> None:
    # Löscht alle Inputschritte des Evalinputs.

    for schritt in katalog.evals.get().inputs.get().schritte.all():
        schritt.delete()


def _leerer_inputschritt(katalog: Evalkatalog) -> None:
    # Leert den letzten Inputschritt bis auf Leerraum.

    schritt: Inputschritt = katalog.evals.get().inputs.get().schritte.last()
    schritt.text = "   "
    schritt.save()


def _leeres_evalkriterium(katalog: Evalkatalog) -> None:
    # Hängt ein leeres zweites Evalkriterium an.

    katalog.evals.get().kriterium_anlegen("")


def _leeres_uebergreifendes_kriterium(katalog: Evalkatalog) -> None:
    # Hängt hinter ein gefülltes ein leeres übergreifendes Kriterium.

    katalog.kriterium_anlegen("Rollentreue")
    katalog.kriterium_anlegen("")


def _feld_setzen(feld: str, wert: object) -> Callable[[Evalkatalog], None]:
    # Eine Lücke, die ein Feld der Fassung auf einen untauglichen Wert setzt.

    def setzen(katalog: Evalkatalog) -> None:
        setattr(katalog, feld, wert)
        katalog.save()

    return setzen


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("luecke", "meldung"),
    [
        (_ohne_eval, "Der Evalkatalog hat kein Eval."),
        (_eval_ohne_evalinput, "Eval „Ergänzt“ hat keinen Evalinput."),
        (_eval_ohne_evalkriterium, "Eval „Ergänzt“ hat kein Evalkriterium."),
        (
            _evalinput_ohne_inputschritt,
            "Evalinput 1 von Eval „Ergänzt“ hat keinen Inputschritt.",
        ),
        (
            _leerer_inputschritt,
            "Inputschritt 3 in Evalinput 1 von Eval „Ergänzt“ ist leer.",
        ),
        (_leeres_evalkriterium, "Evalkriterium 2 von Eval „Ergänzt“ ist leer."),
        (_leeres_uebergreifendes_kriterium, "Übergreifendes Kriterium 2 ist leer."),
        (_feld_setzen("k", 0), "k muss mindestens 1 sein."),
        (_feld_setzen("lehrperson_vorlage", ""), "Die Lehrperson-Vorlage ist leer."),
        (_feld_setzen("bewerter_vorlage", " \n"), "Die Bewerter-Vorlage ist leer."),
    ],
)
def test_unvollstaendiger_entwurf_wird_nicht_final(
    luecke: Callable[[Evalkatalog], None], meldung: str
) -> None:
    """Jede Strukturregel lehnt einzeln ab, und die Meldung nennt die Lücke."""

    katalog: Evalkatalog = vollstaendiger_katalog()
    luecke(katalog)

    with pytest.raises(ValidationError) as abgelehnt:
        katalog.finalisieren()

    assert abgelehnt.value.messages == [meldung]
    katalog.refresh_from_db()
    assert katalog.zustand == Evalkatalog.Zustand.ENTWURF


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("feld", "vorlage", "meldung"),
    [
        (
            "lehrperson_vorlage",
            "Prüfe $kriterium.",
            "Die Lehrperson-Vorlage enthält Platzhalter außerhalb ihres Vertrags: "
            "$kriterium.",
        ),
        (
            "bewerter_vorlage",
            "Lenke nach $inputstrategie.",
            "Die Bewerter-Vorlage enthält Platzhalter außerhalb ihres Vertrags: "
            "$inputstrategie.",
        ),
        (
            "bewerter_vorlage",
            "$kriterium für $unbekannt und ${lehrperson_name}",
            "Die Bewerter-Vorlage enthält Platzhalter außerhalb ihres Vertrags: "
            "$lehrperson_name, $unbekannt.",
        ),
        (
            "lehrperson_vorlage",
            "Kostet 5 $ pro Lauf.",
            "Die Lehrperson-Vorlage enthält einen ungültigen Platzhalter.",
        ),
    ],
)
def test_vorlage_ausserhalb_ihres_vertrags_wird_nicht_final(
    feld: str, vorlage: str, meldung: str
) -> None:
    """Teilmengen-Test plus Gültigkeit je Vorlage, ohne Modellaufruf."""

    katalog: Evalkatalog = vollstaendiger_katalog()
    setattr(katalog, feld, vorlage)
    katalog.save()

    with pytest.raises(ValidationError) as abgelehnt:
        katalog.finalisieren()

    assert abgelehnt.value.messages == [meldung]


@pytest.mark.django_db
def test_promptvertrag_und_verlauf_sind_in_beiden_vorlagen_erlaubt() -> None:
    """Die Prompt-Spalte aus ADR-0010 und `$verlauf` passen in beide Vorlagen."""

    gemeinsam: str = (
        "$fehlermuster_beschreibung $lernauftrag $arbeitsheft"
        " $lernauftrag_simulationshinweise $arbeitsheft_simulationshinweise"
        " $schuelerin_name $schuelerin_geschlecht $fach $thema $klassenstufe"
        " $verlauf"
    )
    katalog: Evalkatalog = vollstaendiger_katalog()
    katalog.lehrperson_vorlage = f"{gemeinsam} $inputstrategie"
    katalog.bewerter_vorlage = f"{gemeinsam} $kriterium"
    katalog.save()

    katalog.finalisieren()

    assert katalog.zustand == Evalkatalog.Zustand.FINAL


@pytest.mark.django_db
def test_meldung_nennt_ein_namenloses_eval_unbenannt() -> None:
    """Auch ein Eval ohne Namen bleibt in der Meldung erkennbar."""

    katalog: Evalkatalog = vollstaendiger_katalog()
    katalog.eval_anlegen("")

    with pytest.raises(ValidationError) as abgelehnt:
        katalog.finalisieren()

    assert abgelehnt.value.messages == [
        "Eval „Unbenanntes Eval“ hat kein Evalkriterium.",
        "Eval „Unbenanntes Eval“ hat keinen Evalinput.",
    ]


@pytest.mark.django_db
def test_meldungen_nennen_alle_luecken_auf_einmal() -> None:
    """Wer finalisiert, erfährt alle Lücken, nicht nur die erste."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()

    with pytest.raises(ValidationError) as abgelehnt:
        katalog.finalisieren()

    assert abgelehnt.value.messages == [
        "Die Lehrperson-Vorlage ist leer.",
        "Die Bewerter-Vorlage ist leer.",
        "Der Evalkatalog hat kein Eval.",
    ]

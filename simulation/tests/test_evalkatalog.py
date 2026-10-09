"""Lebenszyklus und Vertrag des Evalkatalogs (ADR-0046, ADR-0035, ADR-0010)."""

import pytest
from django.db import IntegrityError, models, transaction

from simulation.models import (
    VERTRAG_BEWERTER,
    VERTRAG_EVAL,
    VERTRAG_LEHRPERSON,
    VERTRAG_PROMPT,
    Eval,
    Evalkatalog,
    Evalinput,
    Evalkriterium,
    Inputschritt,
    UebergreifendesKriterium,
)


def test_vertrag_eval_erweitert_den_promptvertrag_um_die_drei_evalwerte() -> None:
    """`VERTRAG_EVAL` ist `VERTRAG_PROMPT` plus die drei Werte des Evallaufs."""

    assert VERTRAG_EVAL == VERTRAG_PROMPT | {"inputstrategie", "kriterium", "verlauf"}


def test_jede_vorlage_erlaubt_nur_ihren_eigenen_evalwert() -> None:
    """Die Lehrperson sieht die Inputstrategie, der Bewerter das Kriterium."""

    assert VERTRAG_LEHRPERSON == VERTRAG_PROMPT | {"inputstrategie", "verlauf"}
    assert VERTRAG_BEWERTER == VERTRAG_PROMPT | {"kriterium", "verlauf"}


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

    with pytest.raises(ValueError, match="Der Evalkatalog wurde bereits angelegt."):
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
def test_entwurf_uebernimmt_gespeicherte_werte() -> None:
    """Ein Entwurf ist änderbar; gespeichert bleibt, was eingetragen wurde."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    katalog.k = 5
    katalog.lehrperson_vorlage = "$inputstrategie"
    katalog.bewerter_vorlage = "$kriterium"
    katalog.save()

    katalog.refresh_from_db()
    assert (katalog.k, katalog.lehrperson_vorlage, katalog.bewerter_vorlage) == (
        5,
        "$inputstrategie",
        "$kriterium",
    )


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
    katalog.finalisieren()

    kriterium.text = "geändert"
    with pytest.raises(RuntimeError, match="Entwurf"):
        kriterium.save()
    with pytest.raises(RuntimeError, match="Entwurf"):
        kriterium.delete()
    with pytest.raises(RuntimeError, match="Entwurf"):
        katalog.kriterium_anlegen("neu")


@pytest.mark.django_db
def test_neuer_entwurf_uebernimmt_die_kriterien_ohne_die_vorgaengerin_zu_beruehren() -> (
    None
):
    """Die Tiefenkopie trägt die Kriterien in gleicher Reihenfolge weiter."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    katalog.kriterium_anlegen("A")
    katalog.kriterium_anlegen("B")
    katalog.finalisieren()

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
    katalog.finalisieren()

    with pytest.raises(RuntimeError, match="Entwurf"):
        UebergreifendesKriterium.objects.filter(katalog=katalog).update(text="x")
    with pytest.raises(RuntimeError, match="Entwurf"):
        UebergreifendesKriterium.objects.filter(katalog=katalog).delete()


@pytest.mark.django_db
def test_kriterium_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf() -> None:
    """Das Umhängen nähme der finalen Fassung ein Kriterium weg."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    kriterium: UebergreifendesKriterium = katalog.kriterium_anlegen("Rollentreue")
    katalog.finalisieren()
    kriterium.katalog = katalog.bearbeiten()
    kriterium.position = 99

    with pytest.raises(RuntimeError, match="Entwurf"):
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
    katalog.finalisieren()

    eval_.name = "geändert"
    kriterium.text = "geändert"
    for versuch in (
        eval_.save,
        eval_.delete,
        kriterium.save,
        kriterium.delete,
        lambda: katalog.eval_anlegen("neu"),
        lambda: eval_.kriterium_anlegen("neu"),
        lambda: Eval.objects.filter(katalog=katalog).update(name="x"),
        lambda: Eval.objects.filter(katalog=katalog).delete(),
        lambda: Evalkriterium.objects.filter(eval=eval_).update(text="x"),
        lambda: Evalkriterium.objects.filter(eval=eval_).delete(),
    ):
        with pytest.raises(RuntimeError, match="Entwurf"):
            versuch()


@pytest.mark.django_db
def test_evalkriterium_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf() -> (
    None
):
    """Auch über das Eval hinweg nimmt das Umhängen der Fassung nichts weg."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    kriterium: Evalkriterium = katalog.eval_anlegen("Muster").kriterium_anlegen("A")
    katalog.finalisieren()
    kriterium.eval = katalog.bearbeiten().evals.get()
    kriterium.position = 99

    with pytest.raises(RuntimeError, match="Entwurf"):
        kriterium.save()


@pytest.mark.django_db
def test_neuer_entwurf_uebernimmt_evals_und_evalkriterien() -> None:
    """Die Tiefenkopie trägt Evals samt Kriterien in gleicher Reihenfolge weiter."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    erstes: Eval = katalog.eval_anlegen("Muster")
    erstes.kriterium_anlegen("A")
    erstes.kriterium_anlegen("B")
    katalog.eval_anlegen("Rolle").kriterium_anlegen("C")
    katalog.finalisieren()

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
def test_evalinputs_und_inputschritte_einer_finalen_fassung_sind_unveraenderlich() -> (
    None
):
    """Evalinputs und Inputschritte teilen die Schreibsperre der Fassung."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    eval_: Eval = katalog.eval_anlegen("Muster")
    evalinput: Evalinput = eval_.input_anlegen()
    schritt: Inputschritt = evalinput.schritte.first()
    katalog.finalisieren()

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
        lambda: Inputschritt.objects.filter(evalinput=evalinput).update(text="x"),
        lambda: Inputschritt.objects.filter(evalinput=evalinput).delete(),
    ):
        with pytest.raises(RuntimeError, match="Entwurf"):
            versuch()


@pytest.mark.django_db
def test_inputschritt_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf() -> (
    None
):
    """Auch über Evalinput und Eval hinweg nimmt das Umhängen nichts weg."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    schritt: Inputschritt = (
        katalog.eval_anlegen("Muster").input_anlegen().schritte.first()
    )
    katalog.finalisieren()
    schritt.evalinput = katalog.bearbeiten().evals.get().inputs.get()
    schritt.position = 99

    with pytest.raises(RuntimeError, match="Entwurf"):
        schritt.save()


@pytest.mark.django_db
def test_neuer_entwurf_uebernimmt_evalinputs_samt_inputschritten() -> None:
    """Die Tiefenkopie trägt jeden Evalinput mit Art und Text seiner Schritte weiter."""

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    eval_: Eval = katalog.eval_anlegen("Muster")
    eval_.input_anlegen().schritt_anlegen(Inputschritt.Art.GELENKT, "Zweifle")
    eval_.input_anlegen().schritte.first().delete()
    katalog.finalisieren()

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

    fest: tuple[str, str] = (Inputschritt.Art.FEST, "")
    assert inputs(entwurf) == [
        [fest, fest, fest, (Inputschritt.Art.GELENKT, "Zweifle laut")],
        [fest, fest],
    ]
    assert inputs(katalog) == [
        [fest, fest, fest, (Inputschritt.Art.GELENKT, "Zweifle")],
        [fest, fest],
    ]

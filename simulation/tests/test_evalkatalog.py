"""Lebenszyklus und Vertrag des Evalkatalogs (ADR-0046, ADR-0035, ADR-0010)."""

import pytest
from django.db import IntegrityError, models, transaction

from simulation.models import (
    VERTRAG_BEWERTER,
    VERTRAG_EVAL,
    VERTRAG_LEHRPERSON,
    VERTRAG_PROMPT,
    Evalkatalog,
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

"""Lebenszyklus und Vertrag des Evalkatalogs (ADR-0046, ADR-0035, ADR-0010)."""

import pytest
from django.db import IntegrityError, models, transaction

from simulation.models import (
    VERTRAG_BEWERTER,
    VERTRAG_EVAL,
    VERTRAG_LEHRPERSON,
    VERTRAG_PROMPT,
    Evalkatalog,
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

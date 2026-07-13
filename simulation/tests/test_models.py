"""Datenbankinvarianten des Simulationskerns."""

from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from simulation.models import KernHistorie, Simulationskern


@pytest.mark.django_db
def test_vertragsfremder_prompt_platzhalter_wird_abgelehnt() -> None:
    """Prompt-Vorlagen dürfen nur die vereinbarten Vignettenfelder ansprechen."""

    kern: Simulationskern = Simulationskern(system_prompt_vorlage="$lehrperson_name")

    with pytest.raises(ValidationError):
        kern.full_clean(exclude=["historie"])


@pytest.mark.django_db
def test_ungueltige_vorlagen_syntax_wird_abgelehnt() -> None:
    """Eine Vorlage muss ein gültiges string.Template sein."""

    kern: Simulationskern = Simulationskern(system_prompt_vorlage="$")

    with pytest.raises(ValidationError):
        kern.full_clean(exclude=["historie"])


@pytest.mark.django_db
def test_vertragstreue_teilmengen_und_leere_vorlagen_werden_akzeptiert() -> None:
    """Alle vier Vorlagen dürfen ihren Vertrag auch nur teilweise ausschöpfen."""

    kern: Simulationskern = Simulationskern(
        system_prompt_vorlage="$fehlermuster_beschreibung",
        rahmenhandlung_einleitung="$lehrperson_anrede $lehrperson_name",
    )

    kern.full_clean(exclude=["historie"])


@pytest.mark.django_db
def test_kern_historie_ist_ein_singleton() -> None:
    """Eine abweichende ID kann keine zweite Kern-Historie erzeugen."""

    KernHistorie.objects.create()

    with pytest.raises(IntegrityError), transaction.atomic():
        KernHistorie.objects.create(id=2)


@pytest.mark.django_db
def test_historie_hat_hoechstens_einen_entwurf() -> None:
    """Eine Kern-Historie nimmt keinen zweiten Entwurf an."""

    historie: KernHistorie = KernHistorie.objects.create()
    Simulationskern.objects.create(historie=historie)

    with pytest.raises(IntegrityError), transaction.atomic():
        Simulationskern.objects.create(historie=historie)


@pytest.mark.django_db
def test_entarchivieren_zu_einer_schwester_wird_verhindert() -> None:
    """Eine archivierte Schwester kann nicht wieder final werden."""

    historie: KernHistorie = KernHistorie.objects.create()
    finalisiert_am: datetime = timezone.now()
    vorgaengerin: Simulationskern = Simulationskern.objects.create(
        historie=historie,
        zustand=Simulationskern.Zustand.FINAL,
        finalisiert_am=finalisiert_am,
    )
    Simulationskern.objects.create(
        historie=historie,
        vorgaengerin=vorgaengerin,
        zustand=Simulationskern.Zustand.FINAL,
        finalisiert_am=finalisiert_am,
    )
    archivierte_schwester: Simulationskern = Simulationskern.objects.create(
        historie=historie,
        vorgaengerin=vorgaengerin,
        zustand=Simulationskern.Zustand.ARCHIVIERT,
        finalisiert_am=finalisiert_am,
    )
    archivierte_schwester.zustand = Simulationskern.Zustand.FINAL

    with pytest.raises(IntegrityError), transaction.atomic():
        archivierte_schwester.save()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("zustand", "finalisiert_am"),
    [
        (Simulationskern.Zustand.ENTWURF, timezone.now()),
        (Simulationskern.Zustand.FINAL, None),
    ],
)
def test_finalisiert_am_muss_genau_dem_zustand_entsprechen(
    zustand: str,
    finalisiert_am: datetime | None,
) -> None:
    """Entwürfe und finalisierte Fassungen tragen passende Zeitstempel."""

    historie: KernHistorie = KernHistorie.objects.create()

    with pytest.raises(IntegrityError), transaction.atomic():
        Simulationskern.objects.create(
            historie=historie,
            zustand=zustand,
            finalisiert_am=finalisiert_am,
        )

"""Datenbankinvarianten des Simulationskerns."""

from datetime import datetime

import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from simulation.models import KernHistorie, ModellKonfiguration, Simulationskern


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


@pytest.mark.django_db
def test_aktivieren_bewegt_den_zeiger_ohne_zweite_aktive_konfiguration() -> None:
    """Erneutes Aktivieren ersetzt die aktive Konfiguration statt sie zu ergänzen."""

    erste: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={},
    )
    zweite: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="zweites-modell",
        parameter={},
    )

    ModellKonfiguration.objects.aktivieren(erste)
    ModellKonfiguration.objects.aktivieren(zweite)

    assert ModellKonfiguration.objects.aktive() == zweite


@pytest.mark.django_db
def test_modell_konfiguration_ist_nach_dem_anlegen_unveraenderlich() -> None:
    """Eine angelegte Modell-Konfiguration bleibt unveränderlich."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={"temperatur": 0.2},
    )
    konfiguration.sprachmodell = "zweites-modell"

    with pytest.raises(RuntimeError, match="append-only"):
        konfiguration.save()


@pytest.mark.django_db
def test_modell_konfiguration_kann_nicht_per_queryset_mutiert_werden() -> None:
    """Die Append-only-Garantie gilt auch für die QuerySet-Schreibroute."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={},
    )

    with pytest.raises(RuntimeError, match="append-only"):
        ModellKonfiguration.objects.filter(pk=konfiguration.pk).update(
            sprachmodell="zweites-modell",
        )


@pytest.mark.django_db
def test_aktive_modell_konfiguration_kann_nicht_geloescht_werden() -> None:
    """Der aktive Zeiger schützt seine Konfiguration vor dem Löschen."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={},
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)

    with pytest.raises(ProtectedError):
        konfiguration.delete()

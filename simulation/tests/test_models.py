import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from simulation.models import KernHistorie, Simulationskern


@pytest.mark.django_db
def test_kern_historie_ist_ein_singleton():
    KernHistorie.objects.create()

    with pytest.raises(IntegrityError), transaction.atomic():
        KernHistorie.objects.create()


@pytest.mark.django_db
def test_historie_can_have_only_one_entwurf():
    historie = KernHistorie.objects.create()
    Simulationskern.objects.create(historie=historie)

    with pytest.raises(IntegrityError), transaction.atomic():
        Simulationskern.objects.create(historie=historie)


@pytest.mark.django_db
def test_entarchivieren_zu_einer_schwester_wird_verhindert():
    historie = KernHistorie.objects.create()
    finalisiert_am = timezone.now()
    vorgaengerin = Simulationskern.objects.create(
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
    archivierte_schwester = Simulationskern.objects.create(
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
    zustand, finalisiert_am
):
    historie = KernHistorie.objects.create()

    with pytest.raises(IntegrityError), transaction.atomic():
        Simulationskern.objects.create(
            historie=historie,
            zustand=zustand,
            finalisiert_am=finalisiert_am,
        )

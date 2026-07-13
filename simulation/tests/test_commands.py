"""Management-Commands der Simulation."""

import pytest
from django.core.management import call_command

from simulation.models import Simulationskern


@pytest.mark.django_db
def test_kern_initialisieren_legt_eine_finale_platzhalter_fassung_an() -> None:
    """Der Command befüllt eine frische Instanz über den Lebenszyklus."""

    call_command("kern_initialisieren")

    kern: Simulationskern = Simulationskern.objects.get()
    assert kern.zustand == Simulationskern.Zustand.FINAL


@pytest.mark.django_db
def test_kern_initialisieren_ist_idempotent() -> None:
    """Ein zweiter Lauf erzeugt keine weitere Kern-Linie."""

    call_command("kern_initialisieren")
    call_command("kern_initialisieren")

    assert Simulationskern.objects.count() == 1

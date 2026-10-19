"""Migrationstest des Pins laufender Sitzungen; die Abschlussphase streicht ihn (ADR-0031).

Die Migration ändert nur Daten. Vor und nach ihr ist das Schema gleich, die
Tests legen ihren Bestand deshalb über die heutigen Modelle an.
"""

from collections.abc import Callable

import pytest

from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from config.tests.aufbau import transkriptions_fassung
from simulation.models import TranskriptionsKonfiguration
from sitzungen.models import Sitzung, Teilnahme
from sitzungen.tests.test_models import sitzungen_anlegen

VORHER: list[tuple[str, str]] = [
    ("sitzungen", "0017_sitzung_transkriptions_konfiguration")
]
NACHHER: list[tuple[str, str]] = [("sitzungen", "0018_laufende_sitzungen_pinnen")]


def _migrieren(bestand_anlegen: Callable[[], None]) -> None:
    """Geht vor die Migration, legt den Bestand an und migriert wieder vor."""

    ziel: list[tuple[str, str]] = MigrationExecutor(
        connection
    ).loader.graph.leaf_nodes()
    MigrationExecutor(connection).migrate(VORHER)
    try:
        bestand_anlegen()
        MigrationExecutor(connection).migrate(NACHHER)
    finally:
        MigrationExecutor(connection).migrate(ziel)


def _wie(vorlage: Sitzung, **felder: object) -> Sitzung:
    # Legt eine Sitzung mit Vignette, Kern und Modell-Konfiguration der Vorlage an.
    return Sitzung.objects.create(
        teilnahme=Teilnahme.objects.create(),
        vignette=vorlage.vignette,
        simulationskern=vorlage.simulationskern,
        modell_konfiguration=vorlage.modell_konfiguration,
        **felder,
    )


@pytest.mark.django_db(transaction=True)
def test_migration_pinnt_nur_laufende_sitzungen_ohne_pin() -> None:
    """Laufende Sitzungen ohne Pin bekommen die aktive Fassung, sonst bleibt alles."""

    bestand: dict[str, Sitzung] = {}
    fassungen: dict[str, TranskriptionsKonfiguration] = {}

    def anlegen() -> None:
        fassungen["aktive"] = TranskriptionsKonfiguration.objects.aktive()
        fassungen["fruehere"] = transkriptions_fassung()
        laufend: Sitzung = sitzungen_anlegen(Teilnahme.objects.create(), 1)[0]
        bestand["laufend"] = laufend
        bestand["gepinnt"] = _wie(
            laufend, transkriptions_konfiguration=fassungen["fruehere"]
        )
        for status in (
            Sitzung.Status.ABGESCHLOSSEN,
            Sitzung.Status.ABGEBROCHEN,
            Sitzung.Status.GESCHEITERT,
        ):
            bestand[status] = _wie(laufend, status=status)

    _migrieren(anlegen)

    pins: dict[str, int | None] = {
        name: Sitzung.objects.get(pk=sitzung.pk).transkriptions_konfiguration_id
        for name, sitzung in bestand.items()
    }
    assert pins == {
        "laufend": fassungen["aktive"].pk,
        "gepinnt": fassungen["fruehere"].pk,
        "abgeschlossen": None,
        "abgebrochen": None,
        "gescheitert": None,
    }


@pytest.mark.django_db(transaction=True)
def test_migration_ohne_aktive_fassung_aendert_nichts() -> None:
    """Ohne Zeiger bleibt die laufende Sitzung ohne Pin, und es entsteht keine Fassung."""

    bestand: list[Sitzung] = []

    def anlegen() -> None:
        bestand.extend(sitzungen_anlegen(Teilnahme.objects.create(), 1))

    _migrieren(anlegen)

    assert Sitzung.objects.get(pk=bestand[0].pk).transkriptions_konfiguration is None
    assert not TranskriptionsKonfiguration.objects.exists()

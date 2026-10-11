"""Migrationstest der Teilnahmekennung; die Abschlussphase streicht ihn (ADR-0031)."""

import re

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

VORHER: list[tuple[str, str]] = [("sitzungen", "0013_teilnahme_drei_einwilligungen")]
NACHHER: list[tuple[str, str]] = [("sitzungen", "0014_teilnahme_kennung")]


@pytest.mark.django_db(transaction=True)
def test_migration_vergibt_bestehenden_teilnahmen_je_eine_zufaellige_kennung() -> None:
    """Jede bestehende Teilnahme erhält ihre eigene Kennung aus acht Hexzeichen."""

    ziel: list[tuple[str, str]] = MigrationExecutor(
        connection
    ).loader.graph.leaf_nodes()
    executor: MigrationExecutor = MigrationExecutor(connection)
    executor.migrate(VORHER)
    try:
        TeilnahmeVorher = executor.loader.project_state(VORHER).apps.get_model(
            "sitzungen", "Teilnahme"
        )
        pks: list[int] = [TeilnahmeVorher.objects.create().pk for _ in range(3)]

        executor = MigrationExecutor(connection)
        executor.migrate(NACHHER)
        TeilnahmeNachher = executor.loader.project_state(NACHHER).apps.get_model(
            "sitzungen", "Teilnahme"
        )
        kennungen: list[str] = list(
            TeilnahmeNachher.objects.filter(pk__in=pks).values_list(
                "kennung", flat=True
            )
        )

        executor = MigrationExecutor(connection)
        executor.migrate(VORHER)
    finally:
        MigrationExecutor(connection).migrate(ziel)

    assert len(set(kennungen)) == 3
    assert all(re.fullmatch(r"[0-9a-f]{8}", kennung) for kennung in kennungen)

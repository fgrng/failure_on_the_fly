"""Migrationstest der Transkriptions-Fassungen; die Abschlussphase streicht ihn (ADR-0031)."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

VORHER: list[tuple[str, str]] = [("simulation", "0016_zero_retention_widerruf")]
NACHHER: list[tuple[str, str]] = [
    ("simulation", "0017_transkriptions_konfiguration_fassungen")
]
WERTE: dict[str, str] = {
    "anbieter": "infomaniak",
    "anbieter_basis_url": "https://api.infomaniak.com/1/ai/42/openai",
    "anbieter_token": "ik-supergeheim1234",
    "transkriptionsmodell": "whisper",
    "sprache": "fr",
}


@pytest.mark.django_db(transaction=True)
def test_migration_macht_die_einzelzeile_zur_einzigen_aktiven_fassung() -> None:
    """Die bisherige Zeile wird mit unveränderten Werten zur aktiven Fassung."""

    ziel: list[tuple[str, str]] = MigrationExecutor(
        connection
    ).loader.graph.leaf_nodes()
    executor: MigrationExecutor = MigrationExecutor(connection)
    executor.migrate(VORHER)
    try:
        KonfigurationVorher = executor.loader.project_state(VORHER).apps.get_model(
            "simulation", "TranskriptionsKonfiguration"
        )
        KonfigurationVorher.objects.all().delete()
        KonfigurationVorher.objects.create(pk=1, **WERTE)

        executor = MigrationExecutor(connection)
        executor.migrate(NACHHER)
        apps = executor.loader.project_state(NACHHER).apps
        fassungen: list[dict[str, object]] = list(
            apps.get_model("simulation", "TranskriptionsKonfiguration").objects.values()
        )
        aktive_pk: int = (
            apps.get_model("simulation", "AktiveTranskriptionsKonfiguration")
            .objects.get()
            .konfiguration_id
        )
    finally:
        MigrationExecutor(connection).migrate(ziel)

    assert fassungen == [{"id": 1, **WERTE, "angelegt_am": None}]
    assert aktive_pk == 1

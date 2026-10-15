"""Die Transkriptions-Konfiguration wird append-only, mit Zeiger auf die aktive.

Die bisherige Einzelzeile wird zur ersten, aktiven Fassung, mit unveränderten
Werten und ohne Anlagedatum (#499).
"""

import django.db.models.deletion
from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def einzelzeile_aktivieren(
    apps: Apps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    """Richtet den Zeiger auf die bisherige Einzelzeile, sofern es sie gibt."""

    konfiguration = apps.get_model("simulation", "TranskriptionsKonfiguration")
    zeiger = apps.get_model("simulation", "AktiveTranskriptionsKonfiguration")
    einzelzeile = konfiguration.objects.order_by("pk").first()
    if einzelzeile is not None:
        zeiger.objects.create(pk=1, konfiguration=einzelzeile)


class Migration(migrations.Migration):
    """Macht aus der Einzelzeile die erste Fassung und führt den Zeiger ein."""

    dependencies = [
        ("simulation", "0016_zero_retention_widerruf"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="transkriptionskonfiguration",
            name="simulation_transkriptions_konfiguration_ist_singleton",
        ),
        migrations.AlterField(
            model_name="transkriptionskonfiguration",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        # Erst ohne auto_now_add: Sonst stempelte AddField die Einzelzeile mit
        # dem Migrationszeitpunkt.
        migrations.AddField(
            model_name="transkriptionskonfiguration",
            name="angelegt_am",
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name="transkriptionskonfiguration",
            name="angelegt_am",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.CreateModel(
            name="AktiveTranskriptionsKonfiguration",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "konfiguration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="simulation.transkriptionskonfiguration",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("id", 1)),
                        name="simulation_aktive_transkriptions_konfiguration_ist_singleton",
                    )
                ],
            },
        ),
        migrations.RunPython(einzelzeile_aktivieren, migrations.RunPython.noop),
    ]

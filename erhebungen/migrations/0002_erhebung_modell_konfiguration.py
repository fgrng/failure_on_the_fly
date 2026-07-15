"""Speichert den Modell-Pin finaler Erhebungen."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Ergänzt den bei Finalisierung gesetzten Modell-Pin."""

    dependencies = [
        ("erhebungen", "0001_initial"),
        ("simulation", "0003_simulationskern_rahmenhandlung_gespraechseinleitung"),
    ]

    operations = [
        migrations.AddField(
            model_name="erhebung",
            name="modell_konfiguration",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="simulation.modellkonfiguration",
            ),
        ),
    ]

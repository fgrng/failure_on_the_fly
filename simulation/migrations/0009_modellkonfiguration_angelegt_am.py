"""Anlagedatum an der Modell-Konfiguration.

Bestandszeilen bleiben leer, statt den Migrationszeitpunkt als Datum zu
erfinden.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Führt das Anlagedatum ein."""

    dependencies = [
        ("simulation", "0008_aktivemodellkonfiguration_verwendung"),
    ]

    # Erst ohne auto_now_add: Sonst stempelte AddField den Bestand mit dem
    # Migrationszeitpunkt.
    operations = [
        migrations.AddField(
            model_name="modellkonfiguration",
            name="angelegt_am",
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name="modellkonfiguration",
            name="angelegt_am",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]

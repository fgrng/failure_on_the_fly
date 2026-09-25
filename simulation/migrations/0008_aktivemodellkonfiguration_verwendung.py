"""Ein Aktiv-Zeiger je Verwendung statt eines einzigen.

Der bestehende Zeiger wird zur Verwendung Schüler:in; Lehrperson und
Bewerter bleiben unbelegt (ADR-0013).
"""

from django.db import migrations, models

_VERWENDUNGEN = [
    ("schuelerin", "Schüler:in"),
    ("lehrperson", "Lehrperson"),
    ("bewerter", "Bewerter"),
]


class Migration(migrations.Migration):
    """Ersetzt die Singleton-Spalte durch eine eindeutige Verwendung."""

    dependencies = [
        ("simulation", "0007_modellkonfiguration_bezeichnung"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="aktivemodellkonfiguration",
            name="simulation_aktive_modell_konfiguration_ist_singleton",
        ),
        migrations.RemoveField(
            model_name="aktivemodellkonfiguration",
            name="singleton",
        ),
        # Der Default überführt die höchstens eine Bestandszeile in Schüler:in.
        migrations.AddField(
            model_name="aktivemodellkonfiguration",
            name="verwendung",
            field=models.CharField(
                choices=_VERWENDUNGEN, default="schuelerin", max_length=10
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="aktivemodellkonfiguration",
            name="verwendung",
            field=models.CharField(choices=_VERWENDUNGEN, max_length=10, unique=True),
        ),
    ]

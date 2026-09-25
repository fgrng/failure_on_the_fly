"""Bezeichnung an der Modell-Konfiguration.

Bestandszeilen bekommen eine aus Sprachmodell und Nummer abgeleitete
Bezeichnung (ADR-0013).
"""

from django.db import migrations, models


def bezeichnungen_ableiten(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Benennt jede Bestandskonfiguration nach Sprachmodell und Nummer."""

    ModellKonfiguration = apps.get_model("simulation", "ModellKonfiguration")
    for konfiguration in ModellKonfiguration.objects.all():
        ModellKonfiguration.objects.filter(pk=konfiguration.pk).update(
            bezeichnung=f"{konfiguration.sprachmodell} (Nr. {konfiguration.pk})"
        )


class Migration(migrations.Migration):
    """Führt die Bezeichnung ein und benennt den Bestand."""

    dependencies = [
        ("simulation", "0006_transkriptionskonfiguration"),
    ]

    operations = [
        migrations.AddField(
            model_name="modellkonfiguration",
            name="bezeichnung",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.RunPython(bezeichnungen_ableiten, migrations.RunPython.noop),
    ]

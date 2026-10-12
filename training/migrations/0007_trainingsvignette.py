"""Führt die Trainingsvignette mit empfohlener Position ein.

Der automatische Zwischentisch weicht der Trainingsvignette; bestehende
Trainings erhalten ihre Positionen in Aufnahme-Reihenfolge.
"""

from importlib import import_module

import django.db.models.deletion
from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

from training.reihenfolge import positionen_in_aufnahmereihenfolge

_ALTER_TRIGGER_SQL = import_module(
    "vignetten.migrations.0006_vignette_arbeitsheft_simulationshinweise_and_more"
)._TRAINING_TRIGGER_SQL

# Die aktuelle Fassung des Triggers; Migrationen, die die Vignettentabelle
# umbauen, löschen ihn vorher und legen ihn mit diesem SQL neu an.
_TRAINING_TRIGGER_SQL = """
    CREATE TRIGGER training_nur_finale_vignetten_einbinden
    BEFORE INSERT ON training_trainingsvignette
    FOR EACH ROW
    WHEN (
        SELECT zustand FROM vignetten_vignette
        WHERE id = NEW.vignette_id
    ) != 'final'
    BEGIN
        SELECT RAISE(
            ABORT,
            'Trainings können nur finale Vignetten einbinden.'
        );
    END;
"""
_TRIGGER_LOESCHEN_SQL = "DROP TRIGGER training_nur_finale_vignetten_einbinden;"


def positionen_uebernehmen(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Überträgt den Zwischentisch in Aufnahme-Reihenfolge."""
    Training = apps.get_model("training", "Training")
    Trainingsvignette = apps.get_model("training", "Trainingsvignette")
    aufnahmen = Training.vignetten.through.objects.order_by("pk").values_list(
        "training_id", "vignette_id"
    )
    Trainingsvignette.objects.bulk_create(
        Trainingsvignette(
            training_id=training_id, vignette_id=vignette_id, position=position
        )
        for training_id, vignette_id, position in positionen_in_aufnahmereihenfolge(
            aufnahmen
        )
    )


def positionen_zurueckgeben(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Legt den Zwischentisch in der empfohlenen Reihenfolge wieder an."""
    Training = apps.get_model("training", "Training")
    Trainingsvignette = apps.get_model("training", "Trainingsvignette")
    Training.vignetten.through.objects.bulk_create(
        Training.vignetten.through(
            training_id=eintrag.training_id, vignette_id=eintrag.vignette_id
        )
        for eintrag in Trainingsvignette.objects.order_by("training_id", "position")
    )


class Migration(migrations.Migration):
    """Ersetzt den Zwischentisch der Trainingsvignetten."""

    dependencies = [
        ("training", "0006_abschrift_freigabe"),
        ("vignetten", "0011_vignette_geaendert_am"),
    ]

    operations = [
        migrations.CreateModel(
            name="Trainingsvignette",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("position", models.PositiveIntegerField()),
                (
                    "training",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vignettenzugehoerigkeiten",
                        to="training.training",
                    ),
                ),
                (
                    "vignette",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="vignetten.vignette",
                    ),
                ),
            ],
            options={
                "ordering": ["position"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("training", "vignette"),
                        name="training_vignette_ist_je_training_eindeutig",
                    ),
                    models.UniqueConstraint(
                        fields=("training", "position"),
                        name="training_vignettenposition_ist_eindeutig",
                    ),
                ],
            },
        ),
        migrations.RunPython(positionen_uebernehmen, positionen_zurueckgeben),
        migrations.RunSQL(_TRIGGER_LOESCHEN_SQL, _ALTER_TRIGGER_SQL),
        migrations.RemoveField(model_name="training", name="vignetten"),
        migrations.AddField(
            model_name="training",
            name="vignetten",
            field=models.ManyToManyField(
                through="training.Trainingsvignette", to="vignetten.vignette"
            ),
        ),
        migrations.RunSQL(_TRAINING_TRIGGER_SQL, _TRIGGER_LOESCHEN_SQL),
    ]

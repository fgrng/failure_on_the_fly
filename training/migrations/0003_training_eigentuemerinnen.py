"""Überführt die einzelne Trainingseigentümerin in einen Eigentümerinnen-Kreis."""

from django.db import migrations, models


def eigentuemerinnen_uebernehmen(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Übernimmt jede bisherige Eigentümerin als erste Eigentümerin ihres Trainings."""
    Training = apps.get_model("training", "Training")
    for training in Training.objects.all():
        training.eigentuemerinnen.add(training.eigentuemerin_id)


class Migration(migrations.Migration):
    """Migriert Trainings von einer Eigentümerin zu einem Eigentümerinnen-Kreis."""

    dependencies = [
        ("training", "0002_trainingsbindung_training_bindung_ist_je_konto_eindeutig"),
    ]

    operations = [
        migrations.AddField(
            model_name="training",
            name="eigentuemerinnen",
            field=models.ManyToManyField(to="konten.konto"),
        ),
        migrations.RunPython(eigentuemerinnen_uebernehmen, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="training",
            name="eigentuemerin",
        ),
    ]

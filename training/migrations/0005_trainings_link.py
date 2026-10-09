"""Gibt jedem Training einen Trainings-Link und einen sperrbaren Beitritt."""

from uuid import uuid4

from django.db import migrations, models


def trainings_links_setzen(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Gibt auch bestehenden Trainings jeweils einen eigenen Trainings-Link."""
    Training: type[models.Model] = apps.get_model("training", "Training")
    for eintrag in Training.objects.filter(trainings_link__isnull=True):
        eintrag.trainings_link = uuid4()
        eintrag.save(update_fields=["trainings_link"])


class Migration(migrations.Migration):
    """Bestehende Trainingsbindungen gelten ohne Datenänderung als Beitritt."""

    dependencies = [
        ("training", "0004_abschrift"),
    ]

    operations = [
        migrations.AddField(
            model_name="training",
            name="trainings_link",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(trainings_links_setzen, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="training",
            name="trainings_link",
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="training",
            name="beitritt_gesperrt",
            field=models.BooleanField(default=False),
        ),
    ]

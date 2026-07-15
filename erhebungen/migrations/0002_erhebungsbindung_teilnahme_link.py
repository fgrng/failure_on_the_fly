"""Ergänzt Teilnahme-Links und ihre pseudonymen Bindungen."""

from uuid import uuid4

import django.db.models.deletion
from django.db import migrations, models


def teilnahme_links_setzen(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Gibt auch bestehenden Stichproben jeweils einen eigenen Teilnahme-Link."""
    stichprobe = apps.get_model("erhebungen", "Stichprobe")
    for eintrag in stichprobe.objects.filter(teilnahme_link__isnull=True):
        eintrag.teilnahme_link = uuid4()
        eintrag.save(update_fields=["teilnahme_link"])


class Migration(migrations.Migration):
    """Speichert die Bindung getrennt von der allgemeinen Teilnahme."""

    dependencies = [
        ("erhebungen", "0001_initial"),
        ("sitzungen", "0005_teilnahme_audioverarbeitung_eingewilligt"),
    ]

    operations = [
        migrations.AddField(
            model_name="stichprobe",
            name="teilnahme_link",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(teilnahme_links_setzen, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="stichprobe",
            name="teilnahme_link",
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.CreateModel(
            name="Erhebungsbindung",
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
                ("token", models.CharField(max_length=9, unique=True)),
                (
                    "stichprobe",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="erhebungen.stichprobe",
                    ),
                ),
                (
                    "teilnahme",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sitzungen.teilnahme",
                    ),
                ),
            ],
        ),
    ]

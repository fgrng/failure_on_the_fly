"""Gibt jeder Teilnahme ihre Teilnahmekennung (ADR-0049)."""

import secrets

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

import sitzungen.models


def kennungen_vergeben(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    # Ein AddField-Default zöge einen Wert für alle; jede Teilnahme braucht ihren.
    Teilnahme = apps.get_model("sitzungen", "Teilnahme")
    for teilnahme in Teilnahme.objects.only("pk"):
        teilnahme.kennung = secrets.token_hex(4)
        teilnahme.save(update_fields=["kennung"])


class Migration(migrations.Migration):

    dependencies = [
        ("sitzungen", "0013_teilnahme_drei_einwilligungen"),
    ]

    operations = [
        migrations.AddField(
            model_name="teilnahme",
            name="kennung",
            field=models.CharField(default="", editable=False, max_length=8),
            preserve_default=False,
        ),
        migrations.RunPython(kennungen_vergeben, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="teilnahme",
            name="kennung",
            field=models.CharField(
                default=sitzungen.models.neue_teilnahmekennung,
                editable=False,
                max_length=8,
            ),
        ),
    ]

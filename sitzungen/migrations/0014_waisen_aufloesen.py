"""Löst liegen gebliebene laufende Sitzungen vor dem Constraint auf.

Je Teilnahme bleibt die jüngste laufende Sitzung fortsetzbar, alle älteren
werden `abgebrochen`. Ausnahmsweise bezeichnet `abgebrochen` hier passiv liegen
gebliebene Altbestände, keinen Abbruch durch die Teilnehmende; einen eigenen
Status bekommen sie nicht, weil ihn künftig nichts mehr erzeugte.
"""

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

from sitzungen.waisen import waisen_aufloesen


def laufende_waisen_abbrechen(
    apps: Apps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    """Lässt je Teilnahme nur die jüngste laufende Sitzung laufen."""

    waisen_aufloesen(apps.get_model("sitzungen", "Sitzung").objects.all())


class Migration(migrations.Migration):
    """Bereitet den Constraint „höchstens eine laufende Sitzung“ vor."""

    dependencies = [
        ("sitzungen", "0013_teilnahme_drei_einwilligungen"),
    ]

    operations = [
        migrations.RunPython(laufende_waisen_abbrechen, migrations.RunPython.noop),
    ]

"""Anlagedatum für den Bestand aus der frühesten Sitzung.

Spätestens als ihre erste Sitzung begann, bestand eine Konfiguration
nachweislich. Bestand ohne Sitzung bleibt leer, statt ein Datum zu erfinden.
"""

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models import Min


def anlagedatum_aus_frueher_sitzung(
    apps: Apps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    """Setzt das Anlagedatum des Bestands auf den Beginn seiner ersten Sitzung."""

    modell_konfiguration = apps.get_model("simulation", "ModellKonfiguration")
    sitzung = apps.get_model("sitzungen", "Sitzung")
    fruehste: dict[int, object] = dict(
        sitzung.objects.filter(
            modell_konfiguration__angelegt_am__isnull=True,
            erstellt_am__isnull=False,
        )
        .values("modell_konfiguration")
        .annotate(fruehste=Min("erstellt_am"))
        .values_list("modell_konfiguration", "fruehste")
    )
    # Das historische Modell kennt die Sperre des eigenen QuerySets nicht.
    for pk, datum in fruehste.items():
        modell_konfiguration.objects.filter(pk=pk).update(angelegt_am=datum)


class Migration(migrations.Migration):
    """Trägt das Anlagedatum des Bestands nach, soweit es belegt ist."""

    dependencies = [
        ("simulation", "0009_modellkonfiguration_angelegt_am"),
        ("sitzungen", "0007_gespraechsschritt_erstellt_am"),
    ]

    operations = [
        migrations.RunPython(
            anlagedatum_aus_frueher_sitzung, migrations.RunPython.noop
        ),
    ]

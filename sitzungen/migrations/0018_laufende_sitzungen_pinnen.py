"""Pinnt die beim Deployment laufenden Sitzungen auf die aktive Transkriptions-Fassung.

Sonst folgten sie jedem späteren Wechsel der aktiven Fassung (#506). Beendete
Sitzungen bleiben ohne Pin: Die frühere Einzelzeile war veränderlich, ein
nachträglicher Pin behauptete einen nicht belegten Anbieter (ADR-0029).
"""

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def laufende_pinnen(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Setzt laufenden Sitzungen ohne Pin die aktive Fassung, sofern es sie gibt."""

    zeiger = (
        apps.get_model("simulation", "AktiveTranskriptionsKonfiguration")
        .objects.filter(pk=1)
        .first()
    )
    if zeiger is None:
        return
    apps.get_model("sitzungen", "Sitzung").objects.filter(
        status="laufend", transkriptions_konfiguration__isnull=True
    ).update(transkriptions_konfiguration_id=zeiger.konfiguration_id)


class Migration(migrations.Migration):
    """Pinnt laufende Sitzungen ohne Pin auf die aktive Transkriptions-Fassung."""

    dependencies = [
        ("simulation", "0018_transkription_zero_retention"),
        ("sitzungen", "0017_sitzung_transkriptions_konfiguration"),
    ]

    operations = [
        migrations.RunPython(laufende_pinnen, migrations.RunPython.noop),
    ]

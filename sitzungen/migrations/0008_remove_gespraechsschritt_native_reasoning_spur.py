# Von Django 6.0.7 am 21.09.2026 um 07:36 erzeugt.

from django.db import migrations


class Migration(migrations.Migration):
    """Streicht die native Reasoning-Spur des Anbieters (ADR-0005)."""

    dependencies = [
        ("sitzungen", "0007_gespraechsschritt_erstellt_am"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="gespraechsschritt",
            name="native_reasoning_spur",
        ),
    ]

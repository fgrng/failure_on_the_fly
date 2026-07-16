"""Speichert die Einwilligung zur pseudonymen Erhebungsteilnahme."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Ergänzt den serverseitig prüfbaren Erhebungs-Einwilligungszustand."""

    dependencies = [
        ("sitzungen", "0005_teilnahme_audioverarbeitung_eingewilligt"),
    ]

    operations = [
        migrations.AddField(
            model_name="teilnahme",
            name="einwilligung_erteilt",
            field=models.BooleanField(default=False),
        ),
    ]

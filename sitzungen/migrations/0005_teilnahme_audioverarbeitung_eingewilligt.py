"""Speichert die Einwilligung zur externen Audioverarbeitung je Teilnahme."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Ergänzt den serverseitig prüfbaren Einwilligungszustand."""

    dependencies = [
        ("sitzungen", "0004_fehlversuch_bewahren"),
    ]

    operations = [
        migrations.AddField(
            model_name="teilnahme",
            name="audioverarbeitung_eingewilligt",
            field=models.BooleanField(default=None, null=True),
        ),
    ]

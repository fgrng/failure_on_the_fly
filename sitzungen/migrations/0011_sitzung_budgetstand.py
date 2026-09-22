# Von Django 6.0.7 am 22.09.2026 erzeugt.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Persistiert den Zeitstand des Gesprächsbudgets an der Sitzung."""

    dependencies = [
        ("sitzungen", "0010_diagnose_eingabemodus"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitzung",
            name="verbrauchte_zeit",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="sitzung",
            name="offene_spanne_seit",
            field=models.DateTimeField(null=True),
        ),
    ]

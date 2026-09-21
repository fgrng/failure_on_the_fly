# Von Django 6.0.7 am 21.09.2026 um 16:22 erzeugt.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Ergänzt den Eingabemodus an der Diagnose; Altzeilen werden getippt.

    Anders als 0009 braucht die Migration keine Trigger-Klammer: Die Trigger
    aus 0007 sitzen auf Gesprächsschritt und Fehlversuch, und der SQLite-
    Rebuild trifft hier allein die Diagnose-Tabelle.
    """

    dependencies = [
        ("sitzungen", "0009_gespraechsschritt_eingabemodus"),
    ]

    operations = [
        migrations.AddField(
            model_name="diagnose",
            name="eingabemodus",
            field=models.CharField(
                choices=[
                    ("getippt", "Getippt"),
                    ("transkribiert", "Transkribiert"),
                    ("gemischt", "Gemischt"),
                ],
                default="getippt",
                max_length=13,
            ),
        ),
    ]

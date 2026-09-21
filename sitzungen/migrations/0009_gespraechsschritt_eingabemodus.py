# Von Django 6.0.7 am 21.09.2026 um 13:15 erzeugt.

from importlib import import_module

from django.db import migrations, models


_vorherige_migration = import_module(
    "sitzungen.migrations.0007_gespraechsschritt_erstellt_am"
)


class Migration(migrations.Migration):
    """Ergänzt den Eingabemodus und stellt die SQLite-Trigger wieder her.

    SQLite baut die Tabelle für das neue Feld neu; die Trigger auf ihr und auf
    den Fehlversuchen überstehen das nicht und werden umschlossen (wie 0007).
    """

    dependencies = [
        ("sitzungen", "0008_remove_gespraechsschritt_native_reasoning_spur"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_vorherige_migration._TRIGGER_LOESCHEN,
            reverse_sql=_vorherige_migration._TRIGGER_ERSTELLEN,
        ),
        migrations.AddField(
            model_name="gespraechsschritt",
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
        migrations.RunSQL(
            sql=_vorherige_migration._TRIGGER_ERSTELLEN,
            reverse_sql=_vorherige_migration._TRIGGER_LOESCHEN,
        ),
    ]

"""Bewahrt die Fehlversuche answerless Gesprächsschritte."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Keine Löschoperation darf einen unvollständigen Abbruchschritt hinterlassen."""

    dependencies = [
        ("sitzungen", "0003_answerless_gespraechsschritt_ist_terminal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fehlversuch",
            name="gespraechsschritt",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="sitzungen.gespraechsschritt",
            ),
        ),
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_loeschen
                BEFORE DELETE ON sitzungen_fehlversuch
                WHEN (
                    SELECT denkspur IS NULL AND aeusserung IS NULL
                    FROM sitzungen_gespraechsschritt
                    WHERE id = OLD.gespraechsschritt_id
                )
                AND (
                    SELECT COUNT(*)
                    FROM sitzungen_fehlversuch
                    WHERE gespraechsschritt_id = OLD.gespraechsschritt_id
                ) = 1
                BEGIN
                    SELECT RAISE(ABORT, 'Answerless-Schritte brauchen einen Fehlversuch.');
                END;
            """,
            reverse_sql="""
                DROP TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_loeschen;
            """,
        ),
    ]

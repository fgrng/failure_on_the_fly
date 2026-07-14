"""Verhindert Schritte nach einem endgültig gescheiterten Antwortversuch."""

from django.db import migrations


class Migration(migrations.Migration):
    """Der answerless Schritt beendet das Diagnosegespräch auch in der DB."""

    dependencies = [
        ("sitzungen", "0002_answerless_gespraechsschritte"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER sitzungen_answerless_schritt_ist_terminal
                BEFORE INSERT ON sitzungen_gespraechsschritt
                WHEN EXISTS (
                    SELECT 1
                    FROM sitzungen_gespraechsschritt
                    WHERE sitzung_id = NEW.sitzung_id
                    AND denkspur IS NULL
                    AND aeusserung IS NULL
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Answerless-Schritte beenden das Gespräch.');
                END;
            """,
            reverse_sql="""
                DROP TRIGGER sitzungen_answerless_schritt_ist_terminal;
            """,
        ),
    ]

"""Sichert answerless Gesprächsschritte gegen fehlende Fehlversuche."""

from django.db import migrations


class Migration(migrations.Migration):
    """SQLite-Trigger ergänzen den zeilenlokalen Check-Constraint."""

    dependencies = [
        ("sitzungen", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_anlegen
                BEFORE INSERT ON sitzungen_gespraechsschritt
                WHEN NEW.denkspur IS NULL AND NEW.aeusserung IS NULL
                BEGIN
                    SELECT RAISE(ABORT, 'Answerless-Schritte brauchen einen Fehlversuch.');
                END;

                CREATE TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_aktualisieren
                BEFORE UPDATE OF denkspur, aeusserung ON sitzungen_gespraechsschritt
                WHEN NEW.denkspur IS NULL AND NEW.aeusserung IS NULL
                AND NOT EXISTS (
                    SELECT 1
                    FROM sitzungen_fehlversuch
                    WHERE gespraechsschritt_id = NEW.id
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Answerless-Schritte brauchen einen Fehlversuch.');
                END;
            """,
            reverse_sql="""
                DROP TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_anlegen;
                DROP TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_aktualisieren;
            """,
        ),
    ]

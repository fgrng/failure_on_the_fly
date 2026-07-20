# Von Django 6.0.7 am 20.07.2026 um 10:05 erzeugt.

from django.db import migrations, models


_TRIGGER_ERSTELLEN = """
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
"""

_TRIGGER_LOESCHEN = """
    DROP TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_anlegen;
    DROP TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_aktualisieren;
    DROP TRIGGER sitzungen_answerless_schritt_ist_terminal;
    DROP TRIGGER sitzungen_answerless_schritt_braucht_fehlversuch_beim_loeschen;
"""


class Migration(migrations.Migration):
    """Ergänzt Zeitstempel und stellt die SQLite-Trigger wieder her."""

    dependencies = [
        ("sitzungen", "0006_teilnahme_einwilligung_erteilt"),
    ]

    operations = [
        migrations.RunSQL(sql=_TRIGGER_LOESCHEN, reverse_sql=_TRIGGER_ERSTELLEN),
        migrations.AddField(
            model_name="sitzung",
            name="erstellt_am",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="gespraechsschritt",
            name="erstellt_am",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="diagnose",
            name="erstellt_am",
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name="sitzung",
            name="erstellt_am",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="gespraechsschritt",
            name="erstellt_am",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="diagnose",
            name="erstellt_am",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.RunSQL(sql=_TRIGGER_ERSTELLEN, reverse_sql=_TRIGGER_LOESCHEN),
    ]

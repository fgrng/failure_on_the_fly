"""Normalisiert Mitgliedschaftspositionen beim Wechsel der Reihenfolgeregel."""

from django.db import migrations


class Migration(migrations.Migration):
    """Erlaubt den atomaren Wechsel zwischen fester und zufälliger Reihenfolge."""

    dependencies = [
        ("erhebungen", "0005_erhebungsvignette_erhebung_vignetten_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DROP TRIGGER erhebungen_reihenfolgeregel_bewahren;
                CREATE TRIGGER erhebungen_reihenfolgeregel_bewahren
                AFTER UPDATE OF randomisierung ON erhebungen_erhebung
                WHEN NEW.randomisierung <> OLD.randomisierung
                BEGIN
                    UPDATE erhebungen_erhebungsvignette
                    SET position = NULL
                    WHERE erhebung_id = NEW.id AND NEW.randomisierung = 'zufällig';
                    UPDATE erhebungen_erhebungsvignette
                    SET position = (
                        SELECT COUNT(*)
                        FROM erhebungen_erhebungsvignette AS fruehere
                        WHERE fruehere.erhebung_id = NEW.id
                          AND fruehere.id <= erhebungen_erhebungsvignette.id
                    )
                    WHERE erhebung_id = NEW.id AND NEW.randomisierung = 'fest';
                END;
            """,
            reverse_sql="""
                DROP TRIGGER erhebungen_reihenfolgeregel_bewahren;
                CREATE TRIGGER erhebungen_reihenfolgeregel_bewahren
                BEFORE UPDATE OF randomisierung ON erhebungen_erhebung
                WHEN (
                    (NEW.randomisierung = 'fest' AND EXISTS (
                        SELECT 1 FROM erhebungen_erhebungsvignette
                        WHERE erhebung_id = NEW.id AND position IS NULL
                    ))
                    OR (NEW.randomisierung = 'zufällig' AND EXISTS (
                        SELECT 1 FROM erhebungen_erhebungsvignette
                        WHERE erhebung_id = NEW.id AND position IS NOT NULL
                    ))
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Die Reihenfolgeregel passt nicht zu den Vignettenpositionen.');
                END;
            """,
        )
    ]

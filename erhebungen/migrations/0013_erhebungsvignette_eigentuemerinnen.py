"""Aktualisiert den SQLite-Guard für Erhebungs-Eigentümerinnen-Kreise."""

from importlib import import_module

from django.db import migrations


_migration = import_module("erhebungen.migrations.0012_erhebung_eigentuemerinnen")
_REIHENFOLGEREGEL_TRIGGER_SQL = """
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
"""

_VORHERIGE_REIHENFOLGEREGEL_TRIGGER_SQL = """
    DROP TRIGGER erhebungen_reihenfolgeregel_bewahren;
    CREATE TRIGGER erhebungen_reihenfolgeregel_bewahren
    BEFORE UPDATE OF randomisierung ON erhebungen_erhebung
    FOR EACH ROW
    WHEN ((NEW.randomisierung = 'fest' AND EXISTS (
        SELECT 1 FROM erhebungen_erhebungsvignette
        WHERE erhebung_id = NEW.id AND position IS NULL
    )) OR (NEW.randomisierung = 'zufällig' AND EXISTS (
        SELECT 1 FROM erhebungen_erhebungsvignette
        WHERE erhebung_id = NEW.id AND position IS NOT NULL
    )))
    BEGIN
        SELECT RAISE(ABORT, 'Die Reihenfolgeregel passt nicht zu den Vignettenpositionen.');
    END;
"""


def _trigger_sql(name: str, ereignis: str, vorlage: str) -> str:
    return f"DROP TRIGGER {name};\n" + vorlage.format(name=name, ereignis=ereignis)


class Migration(migrations.Migration):
    """Prüft Vignetten-Einbindungen gegen die Schnittmenge der Kreise."""

    dependencies = [
        ("erhebungen", "0012_erhebung_eigentuemerinnen"),
        ("vignetten", "0006_vignette_arbeitsheft_simulationshinweise_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            _trigger_sql(
                "erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
                "BEFORE INSERT",
                _migration._VIGNETTEN_TRIGGER_SQL,
            ),
            _trigger_sql(
                "erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
                "BEFORE INSERT",
                _migration._VIGNETTEN_TRIGGER_SQL,
            ),
        ),
        migrations.RunSQL(
            _trigger_sql(
                "erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
                "BEFORE UPDATE OF erhebung_id, vignette_id, position",
                _migration._VIGNETTEN_TRIGGER_SQL,
            ),
            _trigger_sql(
                "erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
                "BEFORE UPDATE OF erhebung_id, vignette_id, position",
                _migration._VIGNETTEN_TRIGGER_SQL,
            ),
        ),
        migrations.RunSQL(
            _REIHENFOLGEREGEL_TRIGGER_SQL,
            _VORHERIGE_REIHENFOLGEREGEL_TRIGGER_SQL,
        ),
    ]

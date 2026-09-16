"""Aktualisiert den SQLite-Guard für Erhebungs-Eigentümerinnen-Kreise."""

from importlib import import_module

from django.db import migrations


_eigentuemerinnen_migration = import_module(
    "erhebungen.migrations.0012_erhebung_eigentuemerinnen"
)
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


def _vignetten_trigger_ersetzen(name: str, ereignis: str) -> migrations.RunSQL:
    """Ersetzt einen Vignetten-Trigger in beide Migrationsrichtungen gleich."""
    sql = (
        f"DROP TRIGGER {name};\n"
        + _eigentuemerinnen_migration._VIGNETTEN_TRIGGER_SQL.format(
            name=name, ereignis=ereignis
        )
    )
    return migrations.RunSQL(sql, sql)


class Migration(migrations.Migration):
    """Prüft Vignetten-Einbindungen gegen die Schnittmenge der Kreise."""

    dependencies = [
        ("erhebungen", "0012_erhebung_eigentuemerinnen"),
        ("vignetten", "0006_vignette_arbeitsheft_simulationshinweise_and_more"),
    ]

    operations = [
        _vignetten_trigger_ersetzen(
            "erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
            "BEFORE INSERT",
        ),
        _vignetten_trigger_ersetzen(
            "erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
            "BEFORE UPDATE OF erhebung_id, vignette_id, position",
        ),
        migrations.RunSQL(
            _REIHENFOLGEREGEL_TRIGGER_SQL,
            _VORHERIGE_REIHENFOLGEREGEL_TRIGGER_SQL,
        ),
    ]

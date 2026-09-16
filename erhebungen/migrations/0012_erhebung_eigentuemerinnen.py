"""Überführt die einzelne Erhebungseigentümerin in einen Eigentümerinnen-Kreis."""

from importlib import import_module

from django.db import migrations, models


_TRIGGER_NAMEN = (
    "erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
    "erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
    "erhebungen_reihenfolgeregel_bewahren",
    "erhebungen_gueltiges_item_einfuegen",
    "erhebungen_gueltiges_item_aendern",
)

_TRIGGER_LOESCHEN_SQL = "\n".join(
    f"DROP TRIGGER {name};" for name in _TRIGGER_NAMEN
)

_vignetten_migration = import_module(
    "erhebungen.migrations.0005_erhebungsvignette_erhebung_vignetten_and_more"
)
_item_migration = import_module("erhebungen.migrations.0009_erhebungsitem")
_ALTE_TRIGGER_ERSTELLEN_SQL = "\n".join(
    (
        _vignetten_migration._VIGNETTENZUGEHOERIGKEIT_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
            ereignis="BEFORE INSERT",
        ),
        _vignetten_migration._VIGNETTENZUGEHOERIGKEIT_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
            ereignis="BEFORE UPDATE OF erhebung_id, vignette_id, position",
        ),
        """
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
        _item_migration._ERHEBUNGSITEM_TRIGGER_SQL.format(
            name="erhebungen_gueltiges_item_einfuegen", ereignis="BEFORE INSERT"
        ),
        _item_migration._ERHEBUNGSITEM_TRIGGER_SQL.format(
            name="erhebungen_gueltiges_item_aendern",
            ereignis="BEFORE UPDATE OF erhebung_id, item_id",
        ),
    )
)

_VIGNETTEN_TRIGGER_SQL = """
    CREATE TRIGGER {name}
    {ereignis} ON erhebungen_erhebungsvignette
    FOR EACH ROW
    WHEN (
        (SELECT zustand FROM vignetten_vignette WHERE id = NEW.vignette_id)
        != 'final'
        OR NOT EXISTS (
            SELECT 1
            FROM erhebungen_erhebung_eigentuemerinnen
            JOIN vignetten_vignettenhistorie_eigentuemerinnen
                ON vignetten_vignettenhistorie_eigentuemerinnen.konto_id
                = erhebungen_erhebung_eigentuemerinnen.konto_id
            JOIN vignetten_vignette
                ON vignetten_vignette.historie_id
                = vignetten_vignettenhistorie_eigentuemerinnen.vignettenhistorie_id
            WHERE erhebungen_erhebung_eigentuemerinnen.erhebung_id = NEW.erhebung_id
              AND vignetten_vignette.id = NEW.vignette_id
        )
        OR ((SELECT randomisierung FROM erhebungen_erhebung WHERE id = NEW.erhebung_id)
            = 'fest' AND NEW.position IS NULL)
        OR ((SELECT randomisierung FROM erhebungen_erhebung WHERE id = NEW.erhebung_id)
            = 'zufällig' AND NEW.position IS NOT NULL)
    )
    BEGIN
        SELECT RAISE(ABORT, 'Erhebungen brauchen eigene finale Vignetten mit passender Position.');
    END;
"""

_ITEM_TRIGGER_SQL = """
    CREATE TRIGGER {name}
    {ereignis} ON erhebungen_erhebungsitem
    FOR EACH ROW
    WHEN (
        (SELECT zustand FROM fragebogen_items_fragebogenitem WHERE id = NEW.item_id)
        != 'final'
        OR NOT EXISTS (
            SELECT 1
            FROM erhebungen_erhebung_eigentuemerinnen
            JOIN fragebogen_items_fragebogenitemhistorie_eigentuemerinnen
                ON fragebogen_items_fragebogenitemhistorie_eigentuemerinnen.konto_id
                = erhebungen_erhebung_eigentuemerinnen.konto_id
            JOIN fragebogen_items_fragebogenitem
                ON fragebogen_items_fragebogenitem.historie_id
                = fragebogen_items_fragebogenitemhistorie_eigentuemerinnen.fragebogenitemhistorie_id
            WHERE erhebungen_erhebung_eigentuemerinnen.erhebung_id = NEW.erhebung_id
              AND fragebogen_items_fragebogenitem.id = NEW.item_id
        )
    )
    BEGIN
        SELECT RAISE(ABORT, 'Erhebungen brauchen eigene finale Fragebogen-Items.');
    END;
"""

_TRIGGER_ERSTELLEN_SQL = "\n".join(
    (
        _VIGNETTEN_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
            ereignis="BEFORE INSERT",
        ),
        _VIGNETTEN_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
            ereignis="BEFORE UPDATE OF erhebung_id, vignette_id, position",
        ),
        """
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
        """,
        _ITEM_TRIGGER_SQL.format(
            name="erhebungen_gueltiges_item_einfuegen", ereignis="BEFORE INSERT"
        ),
        _ITEM_TRIGGER_SQL.format(
            name="erhebungen_gueltiges_item_aendern",
            ereignis="BEFORE UPDATE OF erhebung_id, item_id",
        ),
    )
)


def eigentuemerinnen_uebernehmen(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Übernimmt jede bisherige Eigentümerin als erste Eigentümerin ihrer Erhebung."""
    Erhebung = apps.get_model("erhebungen", "Erhebung")
    for erhebung in Erhebung.objects.all():
        erhebung.eigentuemerinnen.add(erhebung.eigentuemerin_id)


def eigentuemerinnen_zurueckuebernehmen(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Setzt für eine Rückmigration jeweils eine vorhandene Eigentümerin ein."""
    Erhebung = apps.get_model("erhebungen", "Erhebung")
    for erhebung in Erhebung.objects.all():
        eigentuemerin = erhebung.eigentuemerinnen.order_by("pk").first()
        if eigentuemerin is None:
            raise RuntimeError("Eigentümerlose Erhebungen lassen sich nicht zurückmigrieren.")
        erhebung.eigentuemerin_id = eigentuemerin.pk
        erhebung.save(update_fields=["eigentuemerin"])


class Migration(migrations.Migration):
    """Migriert Erhebungen von einer Eigentümerin zu einem Eigentümerinnen-Kreis."""

    dependencies = [
        ("erhebungen", "0011_likert_gueltig"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGER_LOESCHEN_SQL, _ALTE_TRIGGER_ERSTELLEN_SQL),
        migrations.AlterField(
            model_name="erhebung",
            name="eigentuemerin",
            field=models.ForeignKey(
                null=True,
                on_delete=models.PROTECT,
                to="konten.konto",
            ),
        ),
        migrations.AddField(
            model_name="erhebung",
            name="eigentuemerinnen",
            field=models.ManyToManyField(to="konten.konto"),
        ),
        migrations.RunPython(
            eigentuemerinnen_uebernehmen, eigentuemerinnen_zurueckuebernehmen
        ),
        migrations.RemoveField(
            model_name="erhebung",
            name="eigentuemerin",
        ),
        migrations.RunSQL(_TRIGGER_ERSTELLEN_SQL, _TRIGGER_LOESCHEN_SQL),
    ]

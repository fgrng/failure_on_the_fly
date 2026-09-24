"""Jede Vignettenbindung trägt eine Position, auch bei zufälliger Reihenfolge.

Ob die Position für die Teilnahme gilt, entscheidet allein
`Erhebung.randomisierung`. Der SQLite-Trigger, der beim Umschalten Positionen
löschte bzw. neu vergab, entfällt; die Prüf-Trigger der Vignettenbindung prüfen
nur noch Fassung und Eigentümer-Kreis.
"""

from importlib import import_module

from django.db import migrations, models
from django.db.models import Max


_eigentuemerinnen_migration = import_module(
    "erhebungen.migrations.0012_erhebung_eigentuemerinnen"
)
_reihenfolge_migration = import_module(
    "erhebungen.migrations.0013_erhebungsvignette_eigentuemerinnen"
)

_TRIGGER_LOESCHEN_SQL = """
    DROP TRIGGER erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen;
    DROP TRIGGER erhebungen_gueltige_vignettenzugehoerigkeit_aendern;
    DROP TRIGGER erhebungen_reihenfolgeregel_bewahren;
"""

_ALTE_TRIGGER_ERSTELLEN_SQL = "\n".join(
    (
        _eigentuemerinnen_migration._VIGNETTEN_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
            ereignis="BEFORE INSERT",
        ),
        _eigentuemerinnen_migration._VIGNETTEN_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
            ereignis="BEFORE UPDATE OF erhebung_id, vignette_id, position",
        ),
        # 0013 legt den Trigger per DROP + CREATE an; hier genügt das CREATE.
        _reihenfolge_migration._REIHENFOLGEREGEL_TRIGGER_SQL.replace(
            "DROP TRIGGER erhebungen_reihenfolgeregel_bewahren;", ""
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
    )
    BEGIN
        SELECT RAISE(ABORT, 'Erhebungen brauchen eigene finale Vignetten.');
    END;
"""

_NEUE_TRIGGER_ERSTELLEN_SQL = "\n".join(
    (
        _VIGNETTEN_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen",
            ereignis="BEFORE INSERT",
        ),
        _VIGNETTEN_TRIGGER_SQL.format(
            name="erhebungen_gueltige_vignettenzugehoerigkeit_aendern",
            ereignis="BEFORE UPDATE OF erhebung_id, vignette_id",
        ),
    )
)

_NEUE_TRIGGER_LOESCHEN_SQL = """
    DROP TRIGGER erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen;
    DROP TRIGGER erhebungen_gueltige_vignettenzugehoerigkeit_aendern;
"""


def positionen_nachtragen(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Gibt Bindungen ohne Position eine, in Aufnahme-Reihenfolge ans Ende."""
    Erhebungsvignette = apps.get_model("erhebungen", "Erhebungsvignette")
    ohne_position = Erhebungsvignette.objects.filter(position__isnull=True)
    for erhebung_id in set(ohne_position.values_list("erhebung_id", flat=True)):
        naechste: int = (
            Erhebungsvignette.objects.filter(erhebung_id=erhebung_id).aggregate(
                Max("position")
            )["position__max"]
            or 0
        )
        for bindung in ohne_position.filter(erhebung_id=erhebung_id).order_by("pk"):
            naechste += 1
            bindung.position = naechste
            bindung.save(update_fields=["position"])


def positionen_zufaelliger_erhebungen_leeren(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Stellt für eine Rückmigration die alte Regel her: zufällig heißt ohne Position."""
    Erhebungsvignette = apps.get_model("erhebungen", "Erhebungsvignette")
    Erhebungsvignette.objects.filter(erhebung__randomisierung="zufällig").update(
        position=None
    )


class Migration(migrations.Migration):
    """Trennt die Listenposition der Vignetten von der Reihenfolgeregel."""

    # vignetten/0007 legt die Vignetten-Trigger mit der alten SQL neu an und
    # muss deshalb vorher laufen.
    dependencies = [
        ("erhebungen", "0016_vignettenposition_zieht_um"),
        ("vignetten", "0007_geschlechter_nicht_leer"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGER_LOESCHEN_SQL, _ALTE_TRIGGER_ERSTELLEN_SQL),
        migrations.RemoveConstraint(
            model_name="erhebungsvignette",
            name="erhebungen_feste_position_ist_eindeutig",
        ),
        migrations.RunPython(
            positionen_nachtragen, positionen_zufaelliger_erhebungen_leeren
        ),
        migrations.AlterField(
            model_name="erhebungsvignette",
            name="position",
            field=models.PositiveIntegerField(),
        ),
        migrations.AddConstraint(
            model_name="erhebungsvignette",
            constraint=models.UniqueConstraint(
                fields=("erhebung", "position"),
                name="erhebungen_vignettenposition_ist_eindeutig",
            ),
        ),
        migrations.RunSQL(_NEUE_TRIGGER_ERSTELLEN_SQL, _NEUE_TRIGGER_LOESCHEN_SQL),
    ]

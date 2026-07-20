"""Bindet finale Fragebogen-Items an Erhebungen."""

import django.db.models.deletion
from django.db import migrations, models


_ERHEBUNGSITEM_TRIGGER_SQL = """
    CREATE TRIGGER {name}
    {ereignis} ON erhebungen_erhebungsitem
    FOR EACH ROW
    WHEN (
        (SELECT zustand FROM fragebogen_items_fragebogenitem WHERE id = NEW.item_id)
        != 'final'
        OR NOT EXISTS (
            SELECT 1
            FROM erhebungen_erhebung
            JOIN fragebogen_items_fragebogenitem
                ON fragebogen_items_fragebogenitem.id = NEW.item_id
            JOIN fragebogen_items_fragebogenitemhistorie_eigentuemerinnen
                ON fragebogen_items_fragebogenitemhistorie_eigentuemerinnen
                    .fragebogenitemhistorie_id = fragebogen_items_fragebogenitem.historie_id
            WHERE erhebungen_erhebung.id = NEW.erhebung_id
              AND fragebogen_items_fragebogenitemhistorie_eigentuemerinnen.konto_id
                = erhebungen_erhebung.eigentuemerin_id
        )
    )
    BEGIN
        SELECT RAISE(ABORT, 'Erhebungen brauchen eigene finale Fragebogen-Items.');
    END;
"""


class Migration(migrations.Migration):
    """Erstellt die Item-Zuordnung mit ihren Datenbank-Invarianten."""

    dependencies = [
        ("erhebungen", "0008_erhebungsbindung_erstellt_am"),
        ("fragebogen_items", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Erhebungsitem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "andockpunkt",
                    models.CharField(
                        choices=[
                            ("nach_sitzung", "Nach jeder Vignettensitzung"),
                            ("am_ende", "Am Ende"),
                        ],
                        max_length=13,
                    ),
                ),
                ("position", models.PositiveIntegerField()),
                (
                    "erhebung",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itemzugehoerigkeiten",
                        to="erhebungen.erhebung",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="fragebogen_items.fragebogenitem",
                    ),
                ),
            ],
            options={"ordering": ["andockpunkt", "position", "pk"]},
        ),
        migrations.AddConstraint(
            model_name="erhebungsitem",
            constraint=models.UniqueConstraint(
                fields=("erhebung", "item", "andockpunkt"),
                name="erhebungen_item_ist_je_andockpunkt_eindeutig",
            ),
        ),
        migrations.AddConstraint(
            model_name="erhebungsitem",
            constraint=models.UniqueConstraint(
                fields=("erhebung", "andockpunkt", "position"),
                name="erhebungen_item_position_ist_je_andockpunkt_eindeutig",
            ),
        ),
        migrations.RunSQL(
            sql=_ERHEBUNGSITEM_TRIGGER_SQL.format(
                name="erhebungen_gueltiges_item_einfuegen", ereignis="BEFORE INSERT"
            ),
            reverse_sql="DROP TRIGGER erhebungen_gueltiges_item_einfuegen;",
        ),
        migrations.RunSQL(
            sql=_ERHEBUNGSITEM_TRIGGER_SQL.format(
                name="erhebungen_gueltiges_item_aendern",
                ereignis="BEFORE UPDATE OF erhebung_id, item_id",
            ),
            reverse_sql="DROP TRIGGER erhebungen_gueltiges_item_aendern;",
        ),
    ]

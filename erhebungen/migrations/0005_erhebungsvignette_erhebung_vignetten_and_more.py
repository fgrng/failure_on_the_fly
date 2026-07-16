"""Ergänzt die Vignettenzugehörigkeit einer Erhebung samt Reihenfolgeregel."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Erstellt Mitgliedschaft, Eindeutigkeiten und Datenbank-Guards."""

    dependencies = [
        ("erhebungen", "0004_vignettenposition"),
        ("vignetten", "0002_alter_vignette_arbeitsheft_bild"),
    ]

    operations = [
        migrations.CreateModel(
            name="Erhebungsvignette",
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
                ("position", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "erhebung",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vignettenzugehoerigkeiten",
                        to="erhebungen.erhebung",
                    ),
                ),
                (
                    "vignette",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="vignetten.vignette",
                    ),
                ),
            ],
            options={"ordering": ["position", "pk"]},
        ),
        migrations.AddField(
            model_name="erhebung",
            name="vignetten",
            field=models.ManyToManyField(
                through="erhebungen.Erhebungsvignette", to="vignetten.vignette"
            ),
        ),
        migrations.AddConstraint(
            model_name="erhebungsvignette",
            constraint=models.UniqueConstraint(
                fields=("erhebung", "vignette"),
                name="erhebungen_vignette_ist_je_erhebung_eindeutig",
            ),
        ),
        migrations.AddConstraint(
            model_name="erhebungsvignette",
            constraint=models.UniqueConstraint(
                condition=models.Q(("position__isnull", False)),
                fields=("erhebung", "position"),
                name="erhebungen_feste_position_ist_eindeutig",
            ),
        ),
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen
                BEFORE INSERT ON erhebungen_erhebungsvignette
                FOR EACH ROW
                WHEN (
                    (SELECT zustand FROM vignetten_vignette WHERE id = NEW.vignette_id)
                    != 'final'
                    OR NOT EXISTS (
                        SELECT 1
                        FROM erhebungen_erhebung
                        JOIN vignetten_vignette
                            ON vignetten_vignette.id = NEW.vignette_id
                        JOIN vignetten_vignettenhistorie_eigentuemerinnen
                            ON vignetten_vignettenhistorie_eigentuemerinnen.vignettenhistorie_id
                            = vignetten_vignette.historie_id
                        WHERE erhebungen_erhebung.id = NEW.erhebung_id
                          AND vignetten_vignettenhistorie_eigentuemerinnen.konto_id
                            = erhebungen_erhebung.eigentuemerin_id
                    )
                    OR (
                        (SELECT randomisierung FROM erhebungen_erhebung
                         WHERE id = NEW.erhebung_id) = 'fest'
                        AND NEW.position IS NULL
                    )
                    OR (
                        (SELECT randomisierung FROM erhebungen_erhebung
                         WHERE id = NEW.erhebung_id) = 'zufällig'
                        AND NEW.position IS NOT NULL
                    )
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Erhebungen brauchen eigene finale Vignetten mit passender Position.');
                END;
            """,
            reverse_sql=(
                "DROP TRIGGER "
                "erhebungen_gueltige_vignettenzugehoerigkeit_einfuegen;"
            ),
        ),
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER erhebungen_gueltige_vignettenzugehoerigkeit_aendern
                BEFORE UPDATE OF erhebung_id, vignette_id, position
                ON erhebungen_erhebungsvignette
                FOR EACH ROW
                WHEN (
                    (SELECT zustand FROM vignetten_vignette WHERE id = NEW.vignette_id)
                    != 'final'
                    OR NOT EXISTS (
                        SELECT 1
                        FROM erhebungen_erhebung
                        JOIN vignetten_vignette
                            ON vignetten_vignette.id = NEW.vignette_id
                        JOIN vignetten_vignettenhistorie_eigentuemerinnen
                            ON vignetten_vignettenhistorie_eigentuemerinnen.vignettenhistorie_id
                            = vignetten_vignette.historie_id
                        WHERE erhebungen_erhebung.id = NEW.erhebung_id
                          AND vignetten_vignettenhistorie_eigentuemerinnen.konto_id
                            = erhebungen_erhebung.eigentuemerin_id
                    )
                    OR (
                        (SELECT randomisierung FROM erhebungen_erhebung
                         WHERE id = NEW.erhebung_id) = 'fest'
                        AND NEW.position IS NULL
                    )
                    OR (
                        (SELECT randomisierung FROM erhebungen_erhebung
                         WHERE id = NEW.erhebung_id) = 'zufällig'
                        AND NEW.position IS NOT NULL
                    )
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Erhebungen brauchen eigene finale Vignetten mit passender Position.');
                END;
            """,
            reverse_sql=(
                "DROP TRIGGER "
                "erhebungen_gueltige_vignettenzugehoerigkeit_aendern;"
            ),
        ),
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER erhebungen_reihenfolgeregel_bewahren
                BEFORE UPDATE OF randomisierung ON erhebungen_erhebung
                FOR EACH ROW
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
            reverse_sql="DROP TRIGGER erhebungen_reihenfolgeregel_bewahren;",
        ),
    ]

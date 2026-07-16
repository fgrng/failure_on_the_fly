"""Speichert die je Teilnahme gezogene Vignettenreihenfolge."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("erhebungen", "0005_erhebungsvignette_erhebung_vignetten_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="erhebungsbindung",
            name="randomisierungs_seed",
            field=models.PositiveBigIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.CreateModel(
            name="Vignettenziehung",
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
                ("position", models.PositiveIntegerField()),
                (
                    "erhebungsbindung",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vignettenziehungen",
                        to="erhebungen.erhebungsbindung",
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
            options={"ordering": ["position"]},
        ),
        migrations.AddConstraint(
            model_name="vignettenziehung",
            constraint=models.UniqueConstraint(
                fields=("erhebungsbindung", "position"),
                name="erhebungen_ziehung_position_ist_je_teilnahme_eindeutig",
            ),
        ),
        migrations.AddConstraint(
            model_name="vignettenziehung",
            constraint=models.UniqueConstraint(
                fields=("erhebungsbindung", "vignette"),
                name="erhebungen_ziehung_vignette_ist_je_teilnahme_eindeutig",
            ),
        ),
    ]

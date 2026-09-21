# Von Django 6.0.7 am 21.09.2026 um 07:57 erzeugt.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Legt den Itemblock an und hängt die Antwortzeilen verpflichtend an ihn.

    Neuanlage ohne Backfill (Spec #157): Es gibt weder Produktivdaten noch
    Item-Antworten, an denen der einmalige Vorgabewert wirksam würde.
    """

    dependencies = [
        ("erhebungen", "0013_erhebungsvignette_eigentuemerinnen"),
        ("sitzungen", "0008_remove_gespraechsschritt_native_reasoning_spur"),
    ]

    operations = [
        migrations.CreateModel(
            name="Itemblock",
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
                ("vorgelegt_am", models.DateTimeField(auto_now_add=True)),
                ("erledigt_am", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.RemoveConstraint(
            model_name="itemantwort",
            name="erhebungen_antwort_je_sitzung_eindeutig",
        ),
        migrations.RemoveConstraint(
            model_name="itemantwort",
            name="erhebungen_antwort_am_ende_eindeutig",
        ),
        migrations.AddField(
            model_name="itemblock",
            name="erhebungsbindung",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="itembloecke",
                to="erhebungen.erhebungsbindung",
            ),
        ),
        migrations.AddField(
            model_name="itemblock",
            name="sitzung",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="sitzungen.sitzung",
            ),
        ),
        migrations.AddField(
            model_name="itemantwort",
            name="itemblock",
            field=models.ForeignKey(
                default=0,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="antworten",
                to="erhebungen.itemblock",
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="itemantwort",
            constraint=models.UniqueConstraint(
                fields=("itemblock", "erhebungsitem"),
                name="erhebungen_antwort_je_block_eindeutig",
            ),
        ),
        migrations.AddConstraint(
            model_name="itemblock",
            constraint=models.UniqueConstraint(
                condition=models.Q(("sitzung__isnull", False)),
                fields=("erhebungsbindung", "sitzung"),
                name="erhebungen_block_je_sitzung_eindeutig",
            ),
        ),
        migrations.AddConstraint(
            model_name="itemblock",
            constraint=models.UniqueConstraint(
                condition=models.Q(("sitzung__isnull", True)),
                fields=("erhebungsbindung", "andockpunkt"),
                name="erhebungen_block_am_ende_eindeutig",
            ),
        ),
        migrations.AddConstraint(
            model_name="itemblock",
            constraint=models.CheckConstraint(
                condition=models.Q(("andockpunkt", "am_ende"), ("sitzung__isnull", True))
                | models.Q(
                    ("andockpunkt", "nach_sitzung"), ("sitzung__isnull", False)
                ),
                name="erhebungen_block_sitzung_passt_zum_andockpunkt",
            ),
        ),
    ]

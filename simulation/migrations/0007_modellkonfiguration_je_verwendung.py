"""Bezeichnung an der Modell-Konfiguration und ein Aktiv-Zeiger je Verwendung.

Bestandszeilen bekommen eine aus Sprachmodell und Nummer abgeleitete
Bezeichnung; die bisher einzige aktive Konfiguration wird zur Schüler:in
(ADR-0013, Nachführung zu #285).
"""

from django.db import migrations, models


def bezeichnungen_ableiten(apps, schema_editor) -> None:
    ModellKonfiguration = apps.get_model("simulation", "ModellKonfiguration")
    for konfiguration in ModellKonfiguration.objects.all():
        ModellKonfiguration.objects.filter(pk=konfiguration.pk).update(
            bezeichnung=f"{konfiguration.sprachmodell} (Nr. {konfiguration.pk})"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("simulation", "0006_transkriptionskonfiguration"),
    ]

    operations = [
        migrations.AddField(
            model_name="modellkonfiguration",
            name="bezeichnung",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.RunPython(bezeichnungen_ableiten, migrations.RunPython.noop),
        # Erst ohne auto_now_add: Sonst trüge der Bestand den Zeitpunkt der
        # Migration als erfundenes Anlagedatum.
        migrations.AddField(
            model_name="modellkonfiguration",
            name="angelegt_am",
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name="modellkonfiguration",
            name="angelegt_am",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.RemoveConstraint(
            model_name="aktivemodellkonfiguration",
            name="simulation_aktive_modell_konfiguration_ist_singleton",
        ),
        migrations.RemoveField(
            model_name="aktivemodellkonfiguration",
            name="singleton",
        ),
        migrations.AddField(
            model_name="aktivemodellkonfiguration",
            name="verwendung",
            field=models.CharField(
                choices=[
                    ("schuelerin", "Schüler:in"),
                    ("lehrperson", "Lehrperson"),
                    ("bewerter", "Bewerter"),
                ],
                default="schuelerin",
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="aktivemodellkonfiguration",
            name="verwendung",
            field=models.CharField(
                choices=[
                    ("schuelerin", "Schüler:in"),
                    ("lehrperson", "Lehrperson"),
                    ("bewerter", "Bewerter"),
                ],
                max_length=10,
                unique=True,
            ),
        ),
    ]

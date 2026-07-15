from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("simulation", "0002_modellkonfiguration_aktivemodellkonfiguration"),
    ]

    operations = [
        migrations.AddField(
            model_name="simulationskern",
            name="rahmenhandlung_gespraechseinleitung",
            field=models.TextField(blank=True, default=""),
        ),
    ]

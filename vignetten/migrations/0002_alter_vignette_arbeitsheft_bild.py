"""Speichert Arbeitsheft-Bilder unter unveränderlichen UUID-Pfaden."""

import vignetten.models
from django.db import migrations, models


class Migration(migrations.Migration):
    """Stellt die Bildablage auf einzigartige Namen um."""

    dependencies = [
        ("vignetten", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vignette",
            name="arbeitsheft_bild",
            field=models.ImageField(
                blank=True,
                help_text="Was die Teilnehmer:in sieht.",
                upload_to=vignetten.models.arbeitsheft_bild_pfad,
            ),
        ),
    ]

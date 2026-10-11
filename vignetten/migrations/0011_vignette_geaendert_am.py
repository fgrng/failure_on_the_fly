from importlib import import_module

import django.utils.timezone
from django.db import migrations, models

# SQLite baut die Tabelle für das neue Feld um; die Trigger, die sie lesen,
# müssen dafür weichen und danach in ihrer aktuellen Fassung neu entstehen.
_erhebungen_migration = import_module(
    "erhebungen.migrations.0017_vignettenposition_ist_pflicht"
)
_training_migration = import_module(
    "vignetten.migrations.0006_vignette_arbeitsheft_simulationshinweise_and_more"
)
_TRIGGER_LOESCHEN_SQL = (
    _erhebungen_migration._NEUE_TRIGGER_LOESCHEN_SQL
    + "\nDROP TRIGGER training_nur_finale_vignetten_einbinden;"
)
_TRIGGER_ERSTELLEN_SQL = "\n".join(
    (
        _erhebungen_migration._NEUE_TRIGGER_ERSTELLEN_SQL,
        _training_migration._TRAINING_TRIGGER_SQL,
    )
)


class Migration(migrations.Migration):

    dependencies = [
        ("erhebungen", "0017_vignettenposition_ist_pflicht"),
        ("vignetten", "0010_hilfetexte_ohne_markdown_hinweis"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGER_LOESCHEN_SQL, _TRIGGER_ERSTELLEN_SQL),
        migrations.AddField(
            model_name="vignette",
            name="geaendert_am",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.RunSQL(_TRIGGER_ERSTELLEN_SQL, _TRIGGER_LOESCHEN_SQL),
    ]

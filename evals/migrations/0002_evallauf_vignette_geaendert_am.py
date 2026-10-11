import django.utils.timezone
from django.db import migrations, models


def stand_der_fassung_uebernehmen(
    apps: migrations.StateApps, schema_editor: migrations.BaseDatabaseSchemaEditor
) -> None:
    """Bestehende Läufe gelten gegenüber ihrer Fassung, wie sie jetzt ist, als aktuell."""
    Evallauf = apps.get_model("evals", "Evallauf")
    for lauf in Evallauf.objects.select_related("vignette"):
        lauf.vignette_geaendert_am = lauf.vignette.geaendert_am
        lauf.save(update_fields=["vignette_geaendert_am"])


class Migration(migrations.Migration):

    dependencies = [
        ("evals", "0001_evallauf"),
        ("vignetten", "0011_vignette_geaendert_am"),
    ]

    operations = [
        migrations.AddField(
            model_name="evallauf",
            name="vignette_geaendert_am",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(stand_der_fassung_uebernehmen, migrations.RunPython.noop),
    ]

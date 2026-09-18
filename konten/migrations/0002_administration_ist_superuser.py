"""Überführt die frühere Administrations-Group zu Django-Superusern."""

import konten.models
from django.db import migrations


def administration_zu_superusern(apps, schema_editor):
    """Befördert die frühere Administration und entfernt die doppelte Rolle."""
    Konto = apps.get_model("konten", "Konto")
    Group = apps.get_model("auth", "Group")
    administration = Group.objects.filter(name="Administrator:in")

    # Die Rechteausweitung ist beabsichtigt: is_superuser ersetzt die bisherige
    # fachliche Administrationsrolle vollständig; produktive Instanzen existieren noch nicht.
    Konto.objects.filter(groups__in=administration).update(
        is_superuser=True,
        is_staff=True,
    )
    administration.delete()


class Migration(migrations.Migration):
    """Ersetzt die Administrations-Group durch das Django-Superuser-Flag."""

    dependencies = [
        ("konten", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="konto",
            managers=[("objects", konten.models.KontoManager())],
        ),
        migrations.RunPython(administration_zu_superusern, migrations.RunPython.noop),
    ]

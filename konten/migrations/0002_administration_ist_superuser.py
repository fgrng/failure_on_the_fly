"""Überführt die frühere Administrations-Group zu Django-Superusern."""

import konten.models
from django.apps.registry import Apps
from django.db import migrations
from django.db import models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def administration_zu_superusern(
    apps: Apps, _schema_editor: BaseDatabaseSchemaEditor
) -> None:
    """Befördert die frühere Administration und entfernt die doppelte Rolle."""
    Konto: type[models.Model] = apps.get_model("konten", "Konto")
    Group: type[models.Model] = apps.get_model("auth", "Group")
    administration: models.QuerySet[models.Model] = Group.objects.filter(
        name="Administrator:in"
    )

    # Die Rechteausweitung ist beabsichtigt: is_superuser ersetzt die bisherige
    # fachliche Administrationsrolle vollständig; produktive Instanzen existieren
    # noch nicht.
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

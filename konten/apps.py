"""Django-App-Konfiguration für Konten."""

from django.apps import AppConfig
from django.db.models.signals import post_migrate


KONTOROLLEN = ("Autor:in", "Ausbilder:in", "Forschende:r", "Administrator:in")


def erstelle_kontorollen(*, using: str, **kwargs: object) -> None:
    """Stellt die vier additiven Kontorollen bereit."""
    from django.contrib.auth.models import Group

    for name in KONTOROLLEN:
        gruppe, _ = Group.objects.using(using).get_or_create(name=name)
        gruppe.permissions.clear()


class KontenConfig(AppConfig):
    """Konfiguriert die Konten-App."""

    name: str = "konten"

    def ready(self) -> None:
        """Registriert die Rollen-Anlage nach der Migration."""
        post_migrate.connect(
            erstelle_kontorollen,
            sender=self,
            dispatch_uid="konten.erstelle_kontorollen",
        )

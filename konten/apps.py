"""Django-App-Konfiguration für Konten."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save

from .navigation import KONTOROLLEN

if TYPE_CHECKING:
    from .models import Konto


def erstelle_kontorollen(*, using: str, **kwargs: object) -> None:
    """Stellt die drei additiven Kontorollen bereit."""
    from django.contrib.auth.models import Group

    rollenname: str
    for rollenname in KONTOROLLEN:
        gruppe: Group
        gruppe, _ = Group.objects.using(using).get_or_create(name=rollenname)
        gruppe.permissions.clear()


def fixture_superuser_zu_staff(
    sender: type[Konto], instance: Konto, raw: bool, **kwargs: object
) -> None:
    """Gleicht den von Django umgangenen Speicherpfad für Fixtures aus."""
    if raw:
        from .models import Konto

        Konto.objects.filter(pk=instance.pk).update(is_staff=instance.is_superuser)
        instance.is_staff = instance.is_superuser


class KontenConfig(AppConfig):
    """Konfiguriert die Konten-App."""

    name: str = "konten"

    def ready(self) -> None:
        """Registriert die Rollen-Anlage nach der Migration."""
        from .models import Konto

        post_migrate.connect(
            erstelle_kontorollen,
            sender=self,
            dispatch_uid="konten.erstelle_kontorollen",
        )
        post_save.connect(
            fixture_superuser_zu_staff,
            sender=Konto,
            dispatch_uid="konten.fixture_superuser_zu_staff",
        )

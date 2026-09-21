"""Datenmodelle für Nutzerkonten."""

from django.apps import apps
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import ProtectedError, Q

from konten.eigentuemerschaft import EigentuemerKreis


class KontoQuerySet(models.QuerySet["Konto"]):
    """Abfragen über Konten und ihre fachlichen Rollen."""

    def mit_rolle_oder_administration(self, rolle: str) -> "KontoQuerySet":
        """Liefert Konten mit einer Rolle einschließlich der Administration."""
        return self.filter(Q(groups__name=rolle) | Q(is_superuser=True)).distinct()


class KontoManager(UserManager.from_queryset(KontoQuerySet)):
    """Stellt Konto-spezifische Abfragen neben Djangos Nutzeranlage bereit."""


class Konto(AbstractUser):
    """Das Nutzerkonto der Anwendung mit Djangos Standard-Anmeldefeldern."""

    objects: KontoManager = KontoManager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Leitet den Django-Admin-Zutritt aus der Administration ab."""
        self.is_staff = self.is_superuser
        if update_fields := kwargs.get("update_fields"):
            kwargs["update_fields"] = set(update_fields) | {"is_staff"}
        super().save(*args, **kwargs)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        """Verhindert eigentümerlose aktive Bestände."""
        # Die zu prüfenden Bestände kommen aus Djangos Modellregistrierung
        # statt aus Importen: So importiert `konten` nicht in die Bestands-Apps
        # zurück (ADR-0016), und ein künftig hinzukommendes Bestandsmodell ist
        # am Tag seiner Einführung mitgeschützt.
        bestandsmodelle: list[type[EigentuemerKreis]] = [
            modell
            for modell in apps.get_models()
            if issubclass(modell, EigentuemerKreis)
        ]
        for modell in bestandsmodelle:
            for bestand in modell.objects.filter(eigentuemerinnen=self):
                if bestand.ist_aktiv() and bestand.eigentuemerinnen.count() == 1:
                    raise ProtectedError(modell.LOESCHSPERRE_MELDUNG, [bestand])

        return super().delete(using=using, keep_parents=keep_parents)

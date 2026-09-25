"""Datenmodelle für Nutzerkonten."""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import ProtectedError, Q

from konten.eigentuemerschaft import bestandsmodelle
from konten.navigation import KONTOROLLEN


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

    def rollen(self) -> list[str]:
        """Nennt die Fachrollen in fester Reihenfolge, zuletzt die Administration."""
        gruppen: set[str] = set(self.groups.values_list("name", flat=True))
        rollen: list[str] = [rolle for rolle in KONTOROLLEN if rolle in gruppen]
        if self.is_superuser:
            rollen.append("Administrator:in")
        return rollen

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        """Verhindert eigentümerlose aktive Bestände."""
        # Aus der Modellregistrierung, nicht aus Importen: Ein künftig
        # hinzukommendes Bestandsmodell ist am Tag seiner Einführung
        # mitgeschützt.
        for modell in bestandsmodelle():
            for bestand in modell.objects.filter(eigentuemerinnen=self):
                if bestand.ist_aktiv() and bestand.eigentuemerinnen.count() == 1:
                    raise ProtectedError(modell.LOESCHSPERRE_MELDUNG, [bestand])

        return super().delete(using=using, keep_parents=keep_parents)

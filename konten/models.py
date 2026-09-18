"""Datenmodelle für Nutzerkonten."""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import ProtectedError, Q


class KontoQuerySet(models.QuerySet["Konto"]):
    """Abfragen über Konten und ihre fachlichen Rollen."""

    def mit_rolle_oder_administration(self, rolle: str) -> "KontoQuerySet":
        """Liefert Konten mit einer Rolle einschließlich der Administration."""
        return self.filter(Q(groups__name=rolle) | Q(is_superuser=True)).distinct()


class KontoManager(UserManager.from_queryset(KontoQuerySet)):  # type: ignore[misc]
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
        """Verhindert eigentümerlose aktive Objekte."""
        from erhebungen.models import Erhebung
        from training.models import Training
        from vignetten.models import Vignettenhistorie

        for historie in Vignettenhistorie.objects.filter(
            archiviert=False, eigentuemerinnen=self
        ):
            if historie.eigentuemerinnen.count() == 1:
                raise ProtectedError(
                    "Aktive Vignettenhistorien brauchen mindestens eine Eigentümerin.",
                    [historie],
                )

        for training in Training.objects.filter(eigentuemerinnen=self):
            if training.eigentuemerinnen.count() == 1:
                raise ProtectedError(
                    "Trainings brauchen mindestens eine Eigentümerin; bitte "
                    "übertragen Sie das Training vorher.",
                    [training],
                )

        for erhebung in Erhebung.objects.exclude(
            status=Erhebung.Status.ARCHIVIERT
        ).filter(eigentuemerinnen=self):
            if erhebung.eigentuemerinnen.count() == 1:
                raise ProtectedError(
                    "Aktive Erhebungen brauchen mindestens eine Eigentümerin; bitte "
                    "übertragen Sie die Erhebung vorher.",
                    [erhebung],
                )

        return super().delete(using=using, keep_parents=keep_parents)

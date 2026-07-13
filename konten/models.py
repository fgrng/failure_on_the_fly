"""Datenmodelle für Nutzerkonten."""

from django.contrib.auth.models import AbstractUser
from django.db.models import ProtectedError


class Konto(AbstractUser):
    """Das Nutzerkonto der Anwendung mit Djangos Standard-Anmeldefeldern."""

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        """Verhindert eigentümerlose aktive Vignettenhistorien."""
        from vignetten.models import Vignettenhistorie

        for historie in Vignettenhistorie.objects.filter(
            archiviert=False, eigentuemerinnen=self
        ):
            if historie.eigentuemerinnen.count() == 1:
                raise ProtectedError(
                    "Aktive Vignettenhistorien brauchen mindestens eine Eigentümerin.",
                    [historie],
                )

        return super().delete(using=using, keep_parents=keep_parents)

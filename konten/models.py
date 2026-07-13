"""Datenmodelle für Nutzerkonten."""

from django.contrib.auth.models import AbstractUser
from django.db.models.deletion import ProtectedError


class Konto(AbstractUser):
    """Das Nutzerkonto der Anwendung mit Djangos Standard-Anmeldefeldern."""

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
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

        return super().delete(*args, **kwargs)

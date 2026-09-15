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

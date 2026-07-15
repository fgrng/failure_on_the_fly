"""Datenmodelle für Erhebungen und Stichproben."""

from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from konten.models import Konto


class ErhebungQuerySet(models.QuerySet["Erhebung"]):
    """Abfragen über Erhebungen."""

    def sichtbar_fuer(self, konto: "Konto") -> models.QuerySet["Erhebung"]:
        """Liefert ausschließlich Erhebungen der Eigentümerin."""
        return self.filter(eigentuemerin=konto)


class Erhebung(models.Model):
    """Ein Untersuchungsdesign mit konfigurierbaren Texten und Reihenfolgeregel."""

    class Status(models.TextChoices):
        """Die Zustände einer Erhebung."""

        ENTWURF: tuple[str, str] = "entwurf", "Entwurf"
        FINAL: tuple[str, str] = "final", "Final"
        ARCHIVIERT: tuple[str, str] = "archiviert", "Archiviert"

    class Randomisierung(models.TextChoices):
        """Die Reihenfolgeregel der Vignetten in einer Erhebung."""

        FEST: tuple[str, str] = "fest", "Feste Reihenfolge"
        ZUFAELLIG: tuple[str, str] = "zufällig", "Zufällige Reihenfolge"

    name: models.CharField = models.CharField(max_length=255)
    eigentuemerin: models.ForeignKey = models.ForeignKey(
        "konten.Konto", on_delete=models.PROTECT
    )
    status: models.CharField = models.CharField(
        max_length=10, choices=Status, default=Status.ENTWURF
    )
    instruktionstext: models.TextField = models.TextField(blank=True)
    einwilligungstext: models.TextField = models.TextField(blank=True)
    abschlusstext: models.TextField = models.TextField(blank=True)
    randomisierung: models.CharField = models.CharField(
        max_length=9, choices=Randomisierung, default=Randomisierung.FEST
    )

    objects: models.Manager["Erhebung"] = ErhebungQuerySet.as_manager()


class Stichprobe(models.Model):
    """Eine organisatorische Untergruppe einer Erhebung mit Zeitraum."""

    class Phase(models.TextChoices):
        """Die aus dem Erhebungszeitraum abgeleiteten Phasen."""

        VOR: tuple[str, str] = "vor", "Vor"
        LAUFEND: tuple[str, str] = "laufend", "Laufend"
        NACH: tuple[str, str] = "nach", "Nach"

    erhebung: models.ForeignKey = models.ForeignKey(Erhebung, on_delete=models.PROTECT)
    beginn: models.DateTimeField = models.DateTimeField()
    ende: models.DateTimeField = models.DateTimeField()
    archiviert: models.BooleanField = models.BooleanField(default=False)

    @property
    def phase(self) -> str:
        """Leitet die Phase aus Zeitraum und Systemzeit ab."""
        jetzt: datetime = timezone.now()
        if jetzt < self.beginn:
            return self.Phase.VOR
        if jetzt > self.ende:
            return self.Phase.NACH
        return self.Phase.LAUFEND

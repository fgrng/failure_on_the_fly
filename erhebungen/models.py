"""Datenmodelle für Erhebungen und Stichproben."""

from datetime import datetime
from secrets import choice
from typing import TYPE_CHECKING
from uuid import uuid4

from django.db import IntegrityError, models, transaction
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
    teilnahme_link: models.UUIDField = models.UUIDField(
        default=uuid4,
        unique=True,
        editable=False,
    )
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


_TOKEN_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"


def _teilnahme_token() -> str:
    """Erzeugt ein gut ablesbares, achtstelliges Pseudonym."""
    return "".join(choice(_TOKEN_ALPHABET) for _ in range(4)) + "-" + "".join(
        choice(_TOKEN_ALPHABET) for _ in range(4)
    )


class ErhebungsbindungManager(models.Manager["Erhebungsbindung"]):
    """Legt pseudonyme Bindungen mit kollisionsfreien Tokens an."""

    def anlegen(self, stichprobe: Stichprobe) -> "Erhebungsbindung":
        """Erstellt die Teilnahme und versucht bei einer Tokenkollision erneut."""
        from sitzungen.models import Teilnahme

        while True:
            try:
                with transaction.atomic():
                    return self.create(
                        stichprobe=stichprobe,
                        teilnahme=Teilnahme.objects.create(),
                        token=_teilnahme_token(),
                    )
            except IntegrityError:
                continue


class Erhebungsbindung(models.Model):
    """Verbindet eine pseudonyme Teilnahme mit ihrer Stichprobe."""

    teilnahme: models.OneToOneField = models.OneToOneField(
        "sitzungen.Teilnahme",
        on_delete=models.CASCADE,
    )
    stichprobe: models.ForeignKey = models.ForeignKey(
        Stichprobe,
        on_delete=models.PROTECT,
    )
    token: models.CharField = models.CharField(max_length=9, unique=True)

    objects: ErhebungsbindungManager = ErhebungsbindungManager()

    @property
    def verfallen(self) -> bool:
        """Zeigt den Ablauf unvollständiger Teilnahmen nach dem Erhebungsfenster an."""
        from sitzungen.models import Sitzung

        if self.stichprobe.phase != Stichprobe.Phase.NACH:
            return False
        return self.teilnahme.sitzung_set.exclude(
            status__in=[
                Sitzung.Status.ABGESCHLOSSEN,
                Sitzung.Status.ABGEBROCHEN,
                Sitzung.Status.GESCHEITERT,
            ]
        ).exists() or not self.teilnahme.sitzung_set.exists()

"""Datenmodelle für Erhebungen und Stichproben."""

from datetime import datetime
from secrets import choice
from typing import TYPE_CHECKING
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

if TYPE_CHECKING:
    from konten.models import Konto


class ErhebungQuerySet(models.QuerySet["Erhebung"]):
    """Abfragen über Erhebungen."""

    def update(self, **kwargs: object) -> int:
        """Hält finale Designs und Statuswechsel an den Lebenszyklus-Methoden."""

        if {"status", "modell_konfiguration"} & kwargs.keys():
            raise ValidationError("Zustandswechsel laufen über die Lebenszyklus-Methoden.")
        if kwargs and self.exclude(status=Erhebung.Status.ENTWURF).exists():
            raise ValidationError("Finale Erhebungen sind eingefroren.")
        return super().update(**kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:
        """Löscht gesammelt ausschließlich Entwürfe."""

        if self.exclude(status=Erhebung.Status.ENTWURF).exists():
            raise ValidationError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete()

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
    modell_konfiguration: models.ForeignKey = models.ForeignKey(
        "simulation.ModellKonfiguration",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    objects: models.Manager["Erhebung"] = ErhebungQuerySet.as_manager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Schützt Lebenszyklus und eingefrorene finale Designs."""

        if self._state.adding:
            if self.status != self.Status.ENTWURF:
                raise ValidationError("Erhebungen werden als Entwurf angelegt.")
        else:
            gespeicherte_erhebung: Erhebung = type(self).objects.get(pk=self.pk)
            if self.status != gespeicherte_erhebung.status:
                raise ValidationError(
                    "Zustandswechsel laufen über die Lebenszyklus-Methoden."
                )
            if gespeicherte_erhebung.status != self.Status.ENTWURF:
                raise ValidationError("Finale Erhebungen sind eingefroren.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Erlaubt physisches Löschen ausschließlich für Entwürfe."""

        if not type(self).objects.filter(
            pk=self.pk, status=self.Status.ENTWURF
        ).exists():
            raise ValidationError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete(*args, **kwargs)

    def _schreibqueryset(self) -> models.QuerySet["Erhebung"]:
        # Liefert die interne Schreibroute der Lebenszyklus-Methoden.

        return models.QuerySet(model=type(self), using=self._state.db)

    def _status_wechseln(
        self,
        erwarteter_status: str,
        zielstatus: str,
        fehlermeldung: str,
        **aktualisierungen: object,
    ) -> None:
        # Schreibt einen geprüften Lebenszyklus-Übergang und aktualisiert die Instanz.

        if not self._schreibqueryset().filter(
            pk=self.pk, status=erwarteter_status
        ).update(status=zielstatus, **aktualisierungen):
            raise ValidationError(fehlermeldung)
        self.status = zielstatus
        for feld, wert in aktualisierungen.items():
            setattr(self, feld, wert)

    @transaction.atomic
    def finalisieren(self) -> None:
        """Finalisiert einen Entwurf und pinnt die aktive Modell-Konfiguration."""

        from simulation.models import ModellKonfiguration

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.aktive()
        self._status_wechseln(
            erwarteter_status=self.Status.ENTWURF,
            zielstatus=self.Status.FINAL,
            fehlermeldung="Nur Entwürfe können finalisiert werden.",
            modell_konfiguration=konfiguration,
        )

    @transaction.atomic
    def zurueckziehen(self) -> None:
        """Macht eine datenfreie finale Erhebung wieder bearbeitbar."""

        if self.stichprobe_set.filter(archiviert=False).exists() or any(
            stichprobe.traegt_daten for stichprobe in self.stichprobe_set.all()
        ):
            raise ValidationError(
                "Erhebungen mit nicht archivierten Stichproben können nicht "
                "zurückgezogen werden."
            )
        self._status_wechseln(
            erwarteter_status=self.Status.FINAL,
            zielstatus=self.Status.ENTWURF,
            fehlermeldung="Nur finale Erhebungen können zurückgezogen werden.",
        )

    @transaction.atomic
    def archivieren(self) -> None:
        """Archiviert eine Erhebung ohne laufende Stichprobe."""

        jetzt: datetime = timezone.now()
        if self.stichprobe_set.filter(beginn__lte=jetzt, ende__gte=jetzt).exists():
            raise ValidationError(
                "Erhebungen mit laufenden Stichproben können nicht archiviert werden."
            )
        self._status_wechseln(
            erwarteter_status=self.Status.FINAL,
            zielstatus=self.Status.ARCHIVIERT,
            fehlermeldung="Nur finale Erhebungen können archiviert werden.",
        )

    @transaction.atomic
    def entarchivieren(self) -> None:
        """Macht eine archivierte Erhebung wieder final."""

        self._status_wechseln(
            erwarteter_status=self.Status.ARCHIVIERT,
            zielstatus=self.Status.FINAL,
            fehlermeldung="Nur archivierte Erhebungen können entarchiviert werden.",
        )


class StichprobeQuerySet(models.QuerySet["Stichprobe"]):
    """Abfragen über Stichproben."""

    def update(self, **kwargs: object) -> int:
        """Hält Archivieren an der Lebenszyklus-Methode."""

        if "archiviert" in kwargs:
            raise ValidationError("Archivieren läuft über die Lebenszyklus-Methode.")
        return super().update(**kwargs)


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

    objects: models.Manager["Stichprobe"] = StichprobeQuerySet.as_manager()
    _wird_archiviert: bool

    def save(self, *args: object, **kwargs: object) -> None:
        """Hält Archivieren an der Lebenszyklus-Methode."""

        if not self._state.adding:
            gespeicherte_stichprobe: Stichprobe = type(self).objects.get(pk=self.pk)
            if self.archiviert != gespeicherte_stichprobe.archiviert:
                if not getattr(self, "_wird_archiviert", False):
                    raise ValidationError(
                        "Archivieren läuft über die Lebenszyklus-Methode."
                    )
        super().save(*args, **kwargs)

    @transaction.atomic
    def archivieren(self) -> None:
        """Archiviert eine datenfreie Stichprobe."""

        if self.archiviert:
            raise ValidationError("Die Stichprobe ist bereits archiviert.")
        if self.traegt_daten:
            raise ValidationError("Datentragende Stichproben können nicht archiviert werden.")
        self._wird_archiviert = True
        try:
            self.archiviert = True
            self.save(update_fields=["archiviert"])
        finally:
            del self._wird_archiviert

    @property
    def traegt_daten(self) -> bool:
        """Erkennt die mit einer Stichprobe verbundenen Erhebungsdaten."""

        for relation in self._meta.related_objects:
            if relation.related_model._meta.label_lower != "erhebungen.erhebungsbindung":
                continue
            return relation.related_model.objects.filter(
                **{relation.field.name: self}
            ).exists()
        return False

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


class Vignettenposition(models.Model):
    """Eine gezogene Vignetten-Fassung an ihrer Position in einer Teilnahme."""

    erhebungsbindung: models.ForeignKey = models.ForeignKey(
        Erhebungsbindung,
        on_delete=models.CASCADE,
        related_name="vignettenpositionen",
    )
    sitzung: models.OneToOneField = models.OneToOneField(
        "sitzungen.Sitzung",
        on_delete=models.CASCADE,
    )
    position: models.PositiveIntegerField = models.PositiveIntegerField()
    vignette: models.ForeignKey = models.ForeignKey(
        "vignetten.Vignette",
        on_delete=models.PROTECT,
    )

    def clean(self) -> None:
        """Bindet Sitzung und gezogene Fassung an dieselbe Teilnahme."""

        sitzung = self.sitzung
        erhebungsbindung = self.erhebungsbindung
        fehler: dict[str, str] = {}
        if sitzung.teilnahme_id != erhebungsbindung.teilnahme_id:
            fehler["sitzung"] = "Die Sitzung gehört zu einer anderen Teilnahme."
        if sitzung.vignette_id != self.vignette_id:
            fehler["vignette"] = "Die Vignette stimmt nicht mit der Sitzung überein."
        if fehler:
            raise ValidationError(fehler)

    def save(self, *args: object, **kwargs: object) -> None:
        """Schreibt nur Positionen aus einer konsistenten Datenspur."""

        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        """Hält die Reihenfolge je Teilnahme eindeutig und lesbar."""

        ordering: list[str] = ["position"]
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["erhebungsbindung", "position"],
                name="erhebungen_position_ist_je_teilnahme_eindeutig",
            ),
        ]

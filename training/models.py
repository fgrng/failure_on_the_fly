"""Datenmodelle für kuratierte Trainings."""

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import m2m_changed, post_save

if TYPE_CHECKING:
    from konten.models import Konto


_ZUSTANDSWECHSEL_FEHLERMELDUNG = "Zustandswechsel laufen über die Lebenszyklus-Methoden."


class TrainingQuerySet(models.QuerySet["Training"]):
    """Abfragen über Trainings."""

    def update(self, **kwargs: object) -> int:
        """Hält Zustandswechsel an der Lebenszyklus-Naht."""
        if "zustand" in kwargs:
            raise RuntimeError(_ZUSTANDSWECHSEL_FEHLERMELDUNG)
        return super().update(**kwargs)

    def sichtbar_fuer(self, konto: "Konto") -> models.QuerySet["Training"]:
        """Liefert eigene Trainings oder alle für die Administration."""
        if konto.groups.filter(name="Administrator:in").exists():
            return self
        return self.filter(eigentuemerin=konto)

    def veroeffentlicht(self) -> models.QuerySet["Training"]:
        """Liefert die für Teilnehmende sichtbaren Trainings."""
        return self.filter(zustand=Training.Zustand.VEROEFFENTLICHT)


class Training(models.Model):
    """Ein von einer Ausbilderin kuratierter Satz finaler Vignetten."""

    class Zustand(models.TextChoices):
        """Die Zustände eines Trainings."""

        ENTWURF: tuple[str, str] = "entwurf", "Entwurf"
        VEROEFFENTLICHT: tuple[str, str] = "veröffentlicht", "Veröffentlicht"

    name: models.CharField = models.CharField(max_length=255)
    eigentuemerin: models.ForeignKey = models.ForeignKey(
        "konten.Konto", on_delete=models.PROTECT
    )
    zustand: models.CharField = models.CharField(
        max_length=14,
        choices=Zustand,
        default=Zustand.ENTWURF,
    )
    vignetten: models.ManyToManyField = models.ManyToManyField("vignetten.Vignette")

    objects: models.Manager["Training"] = TrainingQuerySet.as_manager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Verhindert direkte Zustandswechsel."""
        if self._state.adding and self.zustand != self.Zustand.ENTWURF:
            raise ValidationError(_ZUSTANDSWECHSEL_FEHLERMELDUNG)
        if not self._state.adding:
            gespeichertes_training: Training = type(self).objects.get(pk=self.pk)
            if self.zustand != gespeichertes_training.zustand and not getattr(
                self, "_wechselt_zustand", False
            ):
                raise ValidationError(_ZUSTANDSWECHSEL_FEHLERMELDUNG)
        super().save(*args, **kwargs)

    @transaction.atomic
    def veroeffentlichen(self) -> None:
        """Veröffentlicht genau einen Entwurf."""
        gespeichertes_training: Training = type(self).objects.select_for_update().get(
            pk=self.pk
        )
        if gespeichertes_training.zustand != self.Zustand.ENTWURF:
            raise ValidationError("Nur Entwürfe können veröffentlicht werden.")
        self._wechselt_zustand = True
        try:
            self.zustand = self.Zustand.VEROEFFENTLICHT
            self.save(update_fields=["zustand"])
        finally:
            del self._wechselt_zustand


class Trainingsbindung(models.Model):
    """Verbindet eine Teilnahme mit Training und Nutzerkonto."""

    teilnahme: models.OneToOneField = models.OneToOneField(
        "sitzungen.Teilnahme", on_delete=models.CASCADE
    )
    training: models.ForeignKey = models.ForeignKey(Training, on_delete=models.PROTECT)
    konto: models.ForeignKey = models.ForeignKey(
        "konten.Konto", on_delete=models.PROTECT
    )

    class Meta:
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["training", "konto"],
                name="training_bindung_ist_je_konto_eindeutig",
            )
        ]


def _pruefe_finale_vignetten(
    sender: type[models.Model],
    instance: models.Model,
    action: str,
    reverse: bool,
    pk_set: set[int] | None,
    **kwargs: object,
) -> None:
    """Hält nicht-finale Vignetten aus Trainings heraus."""
    if action != "pre_add" or not pk_set:
        return
    from vignetten.models import Vignette

    if reverse:
        if instance.zustand != Vignette.Zustand.FINAL:
            raise ValidationError("Trainings können nur finale Vignetten einbinden.")
        return
    if (
        Vignette.objects.filter(pk__in=pk_set)
        .exclude(zustand=Vignette.Zustand.FINAL)
        .exists()
    ):
        raise ValidationError("Trainings können nur finale Vignetten einbinden.")


m2m_changed.connect(
    _pruefe_finale_vignetten,
    sender=Training.vignetten.through,
    dispatch_uid="training.pruefe_finale_vignetten",
)


def _archivierte_vignette_aus_trainings_entfernen(
    sender: type[models.Model],
    instance: models.Model,
    **kwargs: object,
) -> None:
    """Entfernt eine gerade archivierte Vignette aus allen Trainings."""
    from vignetten.models import Vignette

    if instance.zustand == Vignette.Zustand.ARCHIVIERT:
        Training.vignetten.through.objects.filter(vignette_id=instance.pk).delete()


post_save.connect(
    _archivierte_vignette_aus_trainings_entfernen,
    sender="vignetten.Vignette",
    dispatch_uid="training.archivierte_vignette_aus_trainings_entfernen",
)

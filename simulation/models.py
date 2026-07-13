"""Datenmodell des Simulationskerns."""

from django.db import models
from django.db.models import Q

_UNVERAENDERLICH_FEHLERMELDUNG: str = "ModellKonfigurationen sind append-only."


class KernHistorie(models.Model):
    """Die einzige, namenlose Historie der Simulationskern-Fassungen."""

    id: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        primary_key=True,
        default=1,
        editable=False,
    )

    class Meta:
        constraints: list[models.BaseConstraint] = [
            models.CheckConstraint(
                condition=Q(id=1),
                name="simulation_kern_historie_ist_singleton",
            ),
        ]


class Simulationskern(models.Model):
    """Eine versionierte Fassung der zentralen Simulationsvorgaben."""

    class Zustand(models.TextChoices):
        """Mögliche Zustände einer Simulationskern-Fassung."""

        ENTWURF: tuple[str, str] = "entwurf", "Entwurf"
        FINAL: tuple[str, str] = "final", "Final"
        ARCHIVIERT: tuple[str, str] = "archiviert", "Archiviert"

    zustand: models.CharField = models.CharField(
        max_length=11,
        choices=Zustand,
        default=Zustand.ENTWURF,
    )
    finalisiert_am: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
    )
    historie: models.ForeignKey = models.ForeignKey(
        KernHistorie,
        on_delete=models.PROTECT,
    )
    vorgaengerin: models.ForeignKey = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    system_prompt_vorlage: models.TextField = models.TextField(
        blank=True,
        default="",
    )
    user_prompt_vorlage: models.TextField = models.TextField(
        blank=True,
        default="",
    )
    rahmenhandlung_einleitung: models.TextField = models.TextField(
        blank=True,
        default="",
    )
    rahmenhandlung_debrief: models.TextField = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["historie"],
                condition=Q(zustand="entwurf"),
                name="simulation_ein_entwurf_pro_historie",
            ),
            models.UniqueConstraint(
                fields=["vorgaengerin"],
                condition=~Q(zustand="archiviert"),
                name="simulation_keine_nichtarchivierten_schwestern",
            ),
            models.CheckConstraint(
                condition=(
                    Q(zustand="entwurf", finalisiert_am__isnull=True)
                    | (~Q(zustand="entwurf") & Q(finalisiert_am__isnull=False))
                ),
                name="simulation_finalisiert_am_passt_zu_zustand",
            ),
        ]


class ModellKonfigurationQuerySet(models.QuerySet["ModellKonfiguration"]):
    """QuerySets für unveränderliche Modell-Konfigurationen."""

    def update(self, **kwargs: object) -> int:
        """Verhindert Massenänderungen an Modell-Konfigurationen."""

        raise RuntimeError(_UNVERAENDERLICH_FEHLERMELDUNG)


class ModellKonfigurationManager(
    models.Manager.from_queryset(ModellKonfigurationQuerySet),
):
    """Zugang zur aktiven Modell-Konfiguration."""

    def aktive(self) -> "ModellKonfiguration":
        """Liefert die Konfiguration, auf die der aktive Zeiger verweist."""

        return AktiveModellKonfiguration.objects.get(singleton=1).konfiguration

    def aktivieren(
        self,
        konfiguration: "ModellKonfiguration",
    ) -> "ModellKonfiguration":
        """Setzt die einzige aktive Konfiguration."""

        AktiveModellKonfiguration.objects.update_or_create(
            singleton=1,
            defaults={"konfiguration": konfiguration},
        )
        return konfiguration


class ModellKonfiguration(models.Model):
    """Unveränderliche Konfiguration eines Sprachmodells."""

    sprachmodell: models.CharField = models.CharField(max_length=255)
    parameter: models.JSONField = models.JSONField(default=dict)

    objects: ModellKonfigurationManager = ModellKonfigurationManager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Verhindert jede Mutation einer bereits angelegten Konfiguration."""

        if not self._state.adding:
            raise RuntimeError(_UNVERAENDERLICH_FEHLERMELDUNG)
        super().save(*args, **kwargs)


class AktiveModellKonfiguration(models.Model):
    """Der einzige, veränderliche Zeiger auf eine Modell-Konfiguration."""

    konfiguration: models.ForeignKey = models.ForeignKey(
        ModellKonfiguration,
        on_delete=models.PROTECT,
    )
    singleton: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=1,
        unique=True,
        editable=False,
    )

    class Meta:
        constraints: list[models.BaseConstraint] = [
            models.CheckConstraint(
                condition=Q(singleton=1),
                name="simulation_aktive_modell_konfiguration_ist_singleton",
            ),
        ]

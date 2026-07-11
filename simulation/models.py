from django.db import models
from django.db.models import Q


class KernHistorie(models.Model):
    """Die einzige, namenlose Historie der Simulationskern-Fassungen."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(id=1),
                name="simulation_kern_historie_ist_singleton",
            ),
        ]


class Simulationskern(models.Model):
    class Zustand(models.TextChoices):
        ENTWURF = "entwurf", "Entwurf"
        FINAL = "final", "Final"
        ARCHIVIERT = "archiviert", "Archiviert"

    zustand = models.CharField(
        max_length=11,
        choices=Zustand,
        default=Zustand.ENTWURF,
    )
    finalisiert_am = models.DateTimeField(null=True, blank=True)
    historie = models.ForeignKey(KernHistorie, on_delete=models.PROTECT)
    vorgaengerin = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    system_prompt_vorlage = models.TextField(blank=True, default="")
    user_prompt_vorlage = models.TextField(blank=True, default="")
    rahmenhandlung_einleitung = models.TextField(blank=True, default="")
    rahmenhandlung_debrief = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
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

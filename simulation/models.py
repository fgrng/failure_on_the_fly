"""Datenmodell des Simulationskerns."""

from string import Template

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


VERTRAG_PROMPT: frozenset[str] = frozenset(
    {
        "fehlermuster_beschreibung",
        "lernauftrag",
        "arbeitsheft_beschreibung",
        "schuelerin_name",
        "schuelerin_geschlecht",
        "fach",
        "thema",
        "klassenstufe",
    }
)
VERTRAG_RAHMEN: frozenset[str] = frozenset(
    {
        "schuelerin_name",
        "schuelerin_geschlecht",
        "lehrperson_name",
        "lehrperson_geschlecht",
        "fach",
        "thema",
        "klassenstufe",
        "schuelerin_pronomen",
        "schuelerin_possessiv",
        "lehrperson_pronomen",
        "lehrperson_possessiv",
        "lehrperson_anrede",
    }
)


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

    def clean(self) -> None:
        """Lehnt Vorlagen mit Platzhaltern außerhalb ihres Vertrags ab."""

        fehler: dict[str, str] = {}
        vorlagenfeld: str
        erlaubte_platzhalter: frozenset[str]
        for vorlagenfeld, erlaubte_platzhalter in (
            ("system_prompt_vorlage", VERTRAG_PROMPT),
            ("user_prompt_vorlage", VERTRAG_PROMPT),
            ("rahmenhandlung_einleitung", VERTRAG_RAHMEN),
            ("rahmenhandlung_debrief", VERTRAG_RAHMEN),
        ):
            vorlage: Template = Template(getattr(self, vorlagenfeld))
            if (
                not vorlage.is_valid()
                or not set(vorlage.get_identifiers()) <= erlaubte_platzhalter
            ):
                fehler[vorlagenfeld] = "Enthält ungültige Platzhalter."
        if fehler:
            raise ValidationError(fehler)

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

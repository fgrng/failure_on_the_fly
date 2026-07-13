"""Datenmodelle für Vignetten und ihre Historien."""

from typing import TYPE_CHECKING

from django.db import models, transaction
from django.db.models import Q

from simulation.models import Simulationskern

if TYPE_CHECKING:
    from konten.models import Konto


class VignettenhistorieQuerySet(models.QuerySet["Vignettenhistorie"]):
    """Abfragen über Vignettenhistorien."""

    def sichtbar_fuer(self, konto: "Konto") -> models.QuerySet["Vignettenhistorie"]:
        """Liefert die Historien aus dem Eigentümer-Kreis eines Kontos."""
        return self.filter(eigentuemerinnen=konto)


class Vignettenhistorie(models.Model):
    """Die gemeinsame, eigentümerinnengetragene Linie einer Vignette."""

    name: models.CharField = models.CharField(max_length=255, blank=True, default="")
    archiviert: models.BooleanField = models.BooleanField(default=False)
    eigentuemerinnen: models.ManyToManyField = models.ManyToManyField("konten.Konto")

    objects: models.Manager["Vignettenhistorie"] = (
        VignettenhistorieQuerySet.as_manager()
    )


class VignetteQuerySet(models.QuerySet["Vignette"]):
    """Abfragen über Vignettenfassungen."""

    def einbindbar(self) -> models.QuerySet["Vignette"]:
        """Liefert die finalen Fassungen, die eingebunden werden dürfen."""
        return self.filter(zustand=Vignette.Zustand.FINAL)


class VignetteManager(models.Manager.from_queryset(VignetteQuerySet)):
    """Manager für neue Vignettenlinien."""

    @transaction.atomic
    def anlegen(self, konto: "Konto") -> "Vignette":
        """Legt einen Entwurf mit Historie und aktuellem finalem Kern an."""
        kern: Simulationskern = Simulationskern.objects.filter(
            zustand=Simulationskern.Zustand.FINAL
        ).latest("finalisiert_am", "pk")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(konto)
        return self.create(historie=historie, gepinnter_kern=kern)


class Vignette(models.Model):
    """Eine versionierte Fassung einer konkreten Trainingssituation."""

    class Zustand(models.TextChoices):
        """Mögliche Zustände einer Vignettenfassung."""

        ENTWURF: tuple[str, str] = "entwurf", "Entwurf"
        FINAL: tuple[str, str] = "final", "Final"
        ARCHIVIERT: tuple[str, str] = "archiviert", "Archiviert"

    class Geschlecht(models.TextChoices):
        """Die kanonischen Geschlechter für die Rahmenhandlungsgrammatik."""

        MAENNLICH: tuple[str, str] = "männlich", "Männlich"
        WEIBLICH: tuple[str, str] = "weiblich", "Weiblich"

    class BudgetTyp(models.TextChoices):
        """Mögliche Maße des Gesprächsbudgets."""

        SCHRITTE: tuple[str, str] = "schritte", "Schritte"
        ZEIT: tuple[str, str] = "zeit", "Zeit"

    zustand: models.CharField = models.CharField(
        max_length=11, choices=Zustand, default=Zustand.ENTWURF
    )
    finalisiert_am: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    historie: models.ForeignKey = models.ForeignKey(
        Vignettenhistorie, on_delete=models.PROTECT
    )
    vorgaengerin: models.ForeignKey = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT
    )
    fehlermuster_beschreibung: models.TextField = models.TextField(blank=True)
    lernauftrag: models.TextField = models.TextField(blank=True)
    arbeitsheft_beschreibung: models.TextField = models.TextField(
        blank=True, help_text="Prompt-Quelle für das Modell."
    )
    arbeitsheft_text: models.TextField = models.TextField(
        blank=True, help_text="Was die Teilnehmer:in sieht."
    )
    arbeitsheft_bild: models.ImageField = models.ImageField(
        upload_to="arbeitshefte/", blank=True, help_text="Was die Teilnehmer:in sieht."
    )
    schuelerin_name: models.CharField = models.CharField(max_length=255, blank=True)
    schuelerin_geschlecht: models.CharField = models.CharField(
        max_length=9, choices=Geschlecht, blank=True
    )
    lehrperson_name: models.CharField = models.CharField(max_length=255, blank=True)
    lehrperson_geschlecht: models.CharField = models.CharField(
        max_length=9, choices=Geschlecht, blank=True
    )
    fach: models.CharField = models.CharField(max_length=255, blank=True)
    thema: models.CharField = models.CharField(max_length=255, blank=True)
    klassenstufe: models.CharField = models.CharField(max_length=255, blank=True)
    referenzdiagnose: models.TextField = models.TextField(blank=True)
    budget_typ: models.CharField = models.CharField(
        max_length=8, choices=BudgetTyp, blank=True
    )
    budget_wert: models.PositiveIntegerField = models.PositiveIntegerField(
        null=True, blank=True
    )
    gepinnter_kern: models.ForeignKey = models.ForeignKey(
        "simulation.Simulationskern", null=True, blank=True, on_delete=models.PROTECT
    )

    objects: VignetteManager = VignetteManager()

    class Meta:
        """Datenbankinvarianten der Vignettenfassung."""

        # Absichtlich eigenständig gegenüber simulation (ADR-0017): Die
        # Vignette besitzt eigene Inhalte, Eigentümerschaft und Kern-Pin.
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["historie"],
                condition=Q(zustand="entwurf"),
                name="vignetten_ein_entwurf_pro_historie",
            ),
            models.UniqueConstraint(
                fields=["vorgaengerin"],
                condition=~Q(zustand="archiviert"),
                name="vignetten_keine_nichtarchivierten_schwestern",
            ),
            models.CheckConstraint(
                condition=(
                    Q(zustand="entwurf", finalisiert_am__isnull=True)
                    | (~Q(zustand="entwurf") & Q(finalisiert_am__isnull=False))
                ),
                name="vignetten_finalisiert_am_passt_zu_zustand",
            ),
            models.CheckConstraint(
                condition=Q(zustand="entwurf")
                | ~(Q(arbeitsheft_text="") & Q(arbeitsheft_bild="")),
                name="vignetten_arbeitsheft_text_oder_bild",
            ),
        ]


def rahmen_platzhalter(vignette: Vignette) -> dict[str, str]:
    """Liefert die Rohwerte und Grammatikformen für die Rahmenhandlung."""
    pronomen_und_possessiv: dict[str, tuple[str, str]] = {
        Vignette.Geschlecht.WEIBLICH: ("sie", "ihr"),
        Vignette.Geschlecht.MAENNLICH: ("er", "sein"),
    }
    anreden: dict[str, str] = {
        Vignette.Geschlecht.WEIBLICH: "Frau",
        Vignette.Geschlecht.MAENNLICH: "Herr",
    }
    schuelerin_pronomen, schuelerin_possessiv = pronomen_und_possessiv[
        vignette.schuelerin_geschlecht
    ]
    lehrperson_pronomen, lehrperson_possessiv = pronomen_und_possessiv[
        vignette.lehrperson_geschlecht
    ]
    lehrperson_anrede: str = anreden[vignette.lehrperson_geschlecht]
    return {
        "schuelerin_name": vignette.schuelerin_name,
        "schuelerin_geschlecht": vignette.schuelerin_geschlecht,
        "lehrperson_name": vignette.lehrperson_name,
        "lehrperson_geschlecht": vignette.lehrperson_geschlecht,
        "fach": vignette.fach,
        "thema": vignette.thema,
        "klassenstufe": vignette.klassenstufe,
        "schuelerin_pronomen": schuelerin_pronomen,
        "schuelerin_possessiv": schuelerin_possessiv,
        "lehrperson_pronomen": lehrperson_pronomen,
        "lehrperson_possessiv": lehrperson_possessiv,
        "lehrperson_anrede": lehrperson_anrede,
    }

"""Datenmodell des Simulationskerns."""

from datetime import datetime
from string import Template

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

_UNVERAENDERLICH_FEHLERMELDUNG: str = "ModellKonfigurationen sind append-only."
_KERN_UNVERAENDERLICH_FEHLERMELDUNG: str = "Finale Kern-Fassungen sind unveränderlich."


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


class SimulationskernQuerySet(models.QuerySet["Simulationskern"]):
    """Öffentliche Abfragen ohne direkte Schreibroute für Kern-Fassungen."""

    def update(self, **kwargs: object) -> int:
        """Hält Zustands- und Inhaltsänderungen an den Lebenszyklus-Methoden."""

        raise RuntimeError("Kern-Fassungen ändern sich nur über Lebenszyklus-Methoden.")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Löscht gesammelt ausschließlich Entwürfe."""

        if self.exclude(zustand=Simulationskern.Zustand.ENTWURF).exists():
            raise RuntimeError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete()

    def bulk_create(
        self,
        objs: list["Simulationskern"],
        **kwargs: object,
    ) -> list["Simulationskern"]:
        """Verhindert das Umgehen der Anlege-Naht per Masseneinfügen."""

        raise RuntimeError("Kern-Fassungen werden über die Anlege-Naht erzeugt.")

    def bulk_update(
        self,
        objs: list["Simulationskern"],
        fields: list[str],
        **kwargs: object,
    ) -> int:
        """Verhindert das Umgehen der Lebenszyklus-Methoden per Massenupdate."""

        raise RuntimeError("Kern-Fassungen ändern sich nur über Lebenszyklus-Methoden.")


class SimulationskernManager(models.Manager.from_queryset(SimulationskernQuerySet)):
    """Schreibnaht für neue Fassungen des Simulationskerns."""

    @transaction.atomic
    def anlegen(
        self,
        *,
        system_prompt_vorlage: str = "",
        user_prompt_vorlage: str = "",
        rahmenhandlung_einleitung: str = "",
        rahmenhandlung_debrief: str = "",
    ) -> "Simulationskern":
        """Legt die erste Kern-Fassung als Entwurf mit Historie an."""

        historie, _ = KernHistorie.objects.get_or_create(pk=1)
        if self.filter(historie=historie).exists():
            raise ValueError("Der Simulationskern wurde bereits angelegt.")
        return self._erstellen(
            historie=historie,
            system_prompt_vorlage=system_prompt_vorlage,
            user_prompt_vorlage=user_prompt_vorlage,
            rahmenhandlung_einleitung=rahmenhandlung_einleitung,
            rahmenhandlung_debrief=rahmenhandlung_debrief,
        )

    def create(self, **kwargs: object) -> "Simulationskern":
        """Verhindert das Umgehen der Anlege-Naht."""

        raise RuntimeError("Kern-Fassungen werden über die Anlege-Naht erzeugt.")

    def _erstellen(self, **werte: object) -> "Simulationskern":
        # Speichert eine Fassung, die eine Lebenszyklus-Methode erzeugt.

        kern: Simulationskern = self.model(**werte)
        kern._wird_angelegt = True
        kern.save(using=self.db)
        return kern


class Simulationskern(models.Model):
    """Eine versionierte Fassung der zentralen Simulationsvorgaben."""

    _wird_angelegt: bool

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

    objects: SimulationskernManager = SimulationskernManager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Verhindert Änderungen außerhalb der Lebenszyklus-Methoden."""

        if self._state.adding:
            if not getattr(self, "_wird_angelegt", False):
                raise RuntimeError("Kern-Fassungen werden über die Anlege-Naht erzeugt.")
        else:
            vorherige_fassung: Simulationskern = type(self).objects.get(pk=self.pk)
            if vorherige_fassung.zustand != self.Zustand.ENTWURF:
                raise RuntimeError(_KERN_UNVERAENDERLICH_FEHLERMELDUNG)
            if (
                self.zustand != vorherige_fassung.zustand
                or self.finalisiert_am != vorherige_fassung.finalisiert_am
            ):
                raise RuntimeError("Zustandswechsel laufen über die Lebenszyklus-Methoden.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Erlaubt das physische Löschen ausschließlich für Entwürfe."""

        if not type(self).objects.filter(
            pk=self.pk,
            zustand=self.Zustand.ENTWURF,
        ).exists():
            raise RuntimeError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete(*args, **kwargs)

    def _schreibqueryset(self) -> models.QuerySet["Simulationskern"]:
        # Liefert die interne Schreibroute der Lebenszyklus-Methoden.

        return models.QuerySet(model=type(self), using=self._state.db)

    @transaction.atomic
    def bearbeiten(self) -> "Simulationskern":
        """Erzeugt aus einer finalen Fassung einen neuen Entwurf."""

        if not type(self).objects.filter(
            pk=self.pk,
            zustand=self.Zustand.FINAL,
        ).exists():
            raise ValueError("Die Kern-Fassung wurde inzwischen geändert.")
        return type(self).objects._erstellen(
            historie=self.historie,
            vorgaengerin=self,
            system_prompt_vorlage=self.system_prompt_vorlage,
            user_prompt_vorlage=self.user_prompt_vorlage,
            rahmenhandlung_einleitung=self.rahmenhandlung_einleitung,
            rahmenhandlung_debrief=self.rahmenhandlung_debrief,
        )

    @transaction.atomic
    def finalisieren(self) -> None:
        """Finalisiert einen vertragskonformen Entwurf."""

        if self.zustand != self.Zustand.ENTWURF:
            raise ValueError("Nur Entwürfe können finalisiert werden.")
        self.full_clean()
        self.save()
        finalisiert_am: datetime = timezone.now()
        if not self._schreibqueryset().filter(
            pk=self.pk,
            zustand=self.Zustand.ENTWURF,
        ).update(
            zustand=self.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
        ):
            raise ValueError("Der Kern-Entwurf wurde inzwischen geändert.")
        self.zustand = self.Zustand.FINAL
        self.finalisiert_am = finalisiert_am

    @transaction.atomic
    def archivieren(self) -> None:
        """Archiviert eine finale Fassung."""

        if not self._schreibqueryset().filter(
            pk=self.pk,
            zustand=self.Zustand.FINAL,
        ).update(zustand=self.Zustand.ARCHIVIERT):
            raise ValueError("Die Kern-Fassung wurde inzwischen geändert.")
        self.zustand = self.Zustand.ARCHIVIERT

    @transaction.atomic
    def entarchivieren(self) -> None:
        """Macht eine archivierte Fassung wieder final."""

        if not self._schreibqueryset().filter(
            pk=self.pk,
            zustand=self.Zustand.ARCHIVIERT,
        ).update(zustand=self.Zustand.FINAL):
            raise ValueError("Die Kern-Fassung wurde inzwischen geändert.")
        self.zustand = self.Zustand.FINAL

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

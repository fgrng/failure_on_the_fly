"""Datenmodelle für Vignetten und ihre Historien."""

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from simulation.models import Simulationskern


_PFLICHTFELD_NAMEN: tuple[str, ...] = (
    "fehlermuster_beschreibung",
    "lernauftrag",
    "arbeitsheft_beschreibung",
    "schuelerin_name",
    "schuelerin_geschlecht",
    "lehrperson_name",
    "lehrperson_geschlecht",
    "fach",
    "thema",
    "klassenstufe",
    "budget_typ",
)

if TYPE_CHECKING:
    from konten.models import Konto


def arbeitsheft_bild_pfad(_: "Vignette", dateiname: str) -> str:
    """Vergibt jeder hochgeladenen Arbeitsheft-Datei einen neuen Pfad."""
    return f"arbeitshefte/{uuid4().hex}{Path(dateiname).suffix.lower()}"


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

    def bulk_create(
        self,
        objs: list["Vignette"],
        **kwargs: object,
    ) -> list["Vignette"]:
        """Verhindert das Umgehen der Anlege-Naht per Masseneinfügen."""
        raise RuntimeError("Vignetten werden über die Anlege-Naht erzeugt.")

    def bulk_update(
        self,
        objs: list["Vignette"],
        fields: list[str],
        **kwargs: object,
    ) -> int:
        """Verhindert das Umgehen der Lebenszyklus-Methoden per Massenupdate."""
        raise RuntimeError("Vignetten dürfen nicht per Massenupdate geändert werden.")

    def update(self, **kwargs: object) -> int:
        """Verhindert das Umgehen der Unveränderlichkeit per Massenupdate."""
        raise RuntimeError("Vignetten dürfen nicht per Massenupdate geändert werden.")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Löscht gesammelt ausschließlich Entwürfe."""
        if self.exclude(zustand=Vignette.Zustand.ENTWURF).exists():
            raise ValidationError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete()

    def einbindbar(self) -> models.QuerySet["Vignette"]:
        """Liefert die finalen Fassungen, die eingebunden werden dürfen."""
        return self.filter(zustand=Vignette.Zustand.FINAL)


class VignetteManager(models.Manager.from_queryset(VignetteQuerySet)):
    """Manager für neue Vignettenlinien."""

    def create(self, **kwargs: object) -> "Vignette":
        """Verhindert das Umgehen der Anlege-Naht."""
        raise RuntimeError("Vignetten werden über die Anlege-Naht erzeugt.")

    def _erstellen(self, **werte: object) -> "Vignette":
        # Speichert eine Fassung, die eine Lebenszyklus-Methode erzeugt.
        vignette: Vignette = self.model(**werte)
        vignette._wird_angelegt = True
        vignette.save(using=self.db)
        return vignette

    @transaction.atomic
    def anlegen(self, konto: "Konto") -> "Vignette":
        """Legt einen Entwurf mit Historie und aktuellem finalem Kern an."""
        kern: Simulationskern = Simulationskern.objects.filter(
            zustand=Simulationskern.Zustand.FINAL
        ).latest("finalisiert_am", "pk")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(konto)
        return self._erstellen(historie=historie, gepinnter_kern=kern)


class Vignette(models.Model):
    """Eine versionierte Fassung einer konkreten Trainingssituation."""

    _wird_angelegt: bool

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
    fehlermuster_beschreibung: models.TextField = models.TextField(
        blank=True, help_text="Ausführliche Beschreibung des Fehlermusters; bestenfalls mit Beispielen für fehlerbezogenes Verhalten. Wird für die Simulation einbezogen."
    )
    lernauftrag: models.TextField = models.TextField(
        blank=True, help_text="Beschreibung des Lern- oder Arbeitsauftrags, den die Schüler:innen im Unterricht erhalten haben. Für Teilnehmer:in sichtbar."
    )
    arbeitsheft_beschreibung: models.TextField = models.TextField(
        blank=True, help_text="Ausführliche Beschreibung des Arbeitshefts von der zu simulierenden Schüler:in. Wird für die Simulation einbezogen. Für Teilnehmer:in nicht sichtbar."
    )
    arbeitsheft_text: models.TextField = models.TextField(
        blank=True, help_text="Inhalt des Arbeitshefts von der zu simulierenden Schüler:in. Für Teilnehmer:in sichtbar."
    )
    arbeitsheft_bild: models.ImageField = models.ImageField(
        upload_to=arbeitsheft_bild_pfad,
        blank=True,
        help_text="Abbildung des Arbeitshefts von der zu simulierenden Schüler:in. Für Teilnehmer:in sichtbar.",
    )
    schuelerin_name: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text="Vorname der zu simulierenden Schüler:in. Wird für die "
        "Simulation einbezogen. Für Teilnehmer:in sichtbar.",
    )
    schuelerin_geschlecht: models.CharField = models.CharField(
        max_length=9,
        choices=Geschlecht,
        blank=True,
        help_text="Geschlecht der zu simulierenden Schüler:in; steuert die "
        "Grammatik der Rahmenhandlung und die Illustration des "
        "Gesprächsanlasses. Wird für die Simulation einbezogen. "
        "Für Teilnehmer:in sichtbar.",
    )
    lehrperson_name: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nachname der erfahrenen Lehrperson, die durch die "
        "Hospitation führt und im Debrief nach der Diagnose fragt. Wird für "
        "die Simulation nicht einbezogen — die Lehrperson ist der "
        "simulierten Schüler:in unbekannt. Für Teilnehmer:in sichtbar.",
    )
    lehrperson_geschlecht: models.CharField = models.CharField(
        max_length=9,
        choices=Geschlecht,
        blank=True,
        help_text="Geschlecht der erfahrenen Lehrperson; steuert Anrede "
        "(Frau/Herr), Pronomen und die Illustrationen der Rahmenhandlung. "
        "Wird für die Simulation nicht einbezogen. "
        "Für Teilnehmer:in sichtbar.",
    )
    fach: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text="Unterrichtsfach, in dem die Vignette spielt. Wird für die "
        "Simulation einbezogen. Für Teilnehmer:in sichtbar.",
    )
    thema: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text="Unterrichtsthema, an dem das Fehlermuster auftritt. Wird "
        "für die Simulation einbezogen. Für Teilnehmer:in sichtbar.",
    )
    klassenstufe: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text="Klassenstufe der zu simulierenden Schüler:in. Wird für "
        "die Simulation einbezogen. Für Teilnehmer:in sichtbar.",
    )
    referenzdiagnose: models.TextField = models.TextField(
        blank=True,
        help_text="Optionale fachdidaktische Notiz der Autor:in zum "
        "Fehlermuster. Ohne jede Wirkung auf Simulation und Ablauf; sie "
        "erscheint nur in der Vignettenansicht und im Datenexport. "
        "Für Teilnehmer:in nicht sichtbar.",
    )
    budget_typ: models.CharField = models.CharField(
        max_length=8,
        choices=BudgetTyp,
        blank=True,
        help_text="Maß des Gesprächsbudgets, an dem das Diagnosegespräch "
        "endet und der Debrief folgt: Gesprächsschritte oder Zeit. Pro "
        "Vignette ist genau ein Maß aktiv. Für Teilnehmer:in nicht sichtbar.",
    )
    budget_wert: models.PositiveIntegerField = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Grenze des Gesprächsbudgets, größer als 0: Anzahl der "
        "Gesprächsschritte bzw. Sekunden — je nach gewähltem Budget-Typ. "
        "Für Teilnehmer:in nicht sichtbar.",
    )
    gepinnter_kern: models.ForeignKey = models.ForeignKey(
        "simulation.Simulationskern", null=True, blank=True, on_delete=models.PROTECT
    )

    objects: VignetteManager = VignetteManager()

    @property
    def lehrperson_bildkuerzel(self) -> str:
        """Kürzel für die geschlechtsabhängige Rahmenhandlungs-Illustration (Einstieg, Debrief)."""
        return "m" if self.lehrperson_geschlecht == self.Geschlecht.MAENNLICH else "w"

    @property
    def schuelerin_bildkuerzel(self) -> str:
        """Kürzel für die geschlechtsabhängige Gesprächsanlass-Illustration."""
        return "m" if self.schuelerin_geschlecht == self.Geschlecht.MAENNLICH else "w"

    @property
    def hat_nicht_archivierte_nachfolgerin(self) -> bool:
        """Gibt zurück, ob diese Fassung eine nicht archivierte Nachfolgerin hat."""
        return (
            type(self)
            .objects.filter(historie=self.historie, pk__gt=self.pk)
            .exclude(zustand=self.Zustand.ARCHIVIERT)
            .exists()
        )

    def save(self, *args: object, **kwargs: object) -> None:
        """Verhindert inhaltliche Änderungen an nicht mehr entworfenen Fassungen."""
        if self._state.adding:
            if not getattr(self, "_wird_angelegt", False):
                raise RuntimeError("Vignetten werden über die Anlege-Naht erzeugt.")
        else:
            gespeicherte_fassung: Vignette = type(self).objects.get(pk=self.pk)
            if (
                self.zustand != gespeicherte_fassung.zustand
                and not getattr(self, "_wechselt_zustand", False)
            ):
                raise ValidationError(
                    "Zustandswechsel laufen über die Lebenszyklus-Methoden."
                )
            if gespeicherte_fassung.zustand != self.Zustand.ENTWURF and any(
                getattr(self, modellfeld.attname)
                != getattr(gespeicherte_fassung, modellfeld.attname)
                for modellfeld in self._meta.local_fields
                if modellfeld.name != "zustand"
            ):
                raise ValidationError("Finale Fassungen sind unveränderlich.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Erlaubt das physische Löschen ausschließlich für Entwürfe."""
        if not type(self).objects.filter(
            pk=self.pk,
            zustand=self.Zustand.ENTWURF,
        ).exists():
            raise ValidationError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete(*args, **kwargs)

    def _zustand_wechseln(self, zustand: str, update_fields: list[str]) -> None:
        """Speichert einen ausschließlich intern ausgelösten Zustandsübergang."""
        # Anders als beim Kern hält save() die Vignetten-Unveränderlichkeit;
        # daher laufen ihre Zustandskanten über diese geschützte Schreibnaht.
        self._wechselt_zustand = True
        try:
            self.zustand = zustand
            self.save(update_fields=update_fields)
        finally:
            del self._wechselt_zustand

    @transaction.atomic
    def bearbeiten(self) -> "Vignette":
        """Erzeugt aus einer finalen Fassung einen Entwurf derselben Historie."""
        quelle: Vignette = type(self).objects.select_for_update().get(pk=self.pk)
        if quelle.zustand != self.Zustand.FINAL:
            raise ValidationError("Nur finale Fassungen können bearbeitet werden.")
        if quelle.hat_nicht_archivierte_nachfolgerin:
            raise ValidationError(
                "Diese Fassung hat bereits eine nicht archivierte Nachfolgerin."
            )
        return type(self).objects._erstellen(
            historie=quelle.historie,
            vorgaengerin=quelle,
            gepinnter_kern=quelle.gepinnter_kern,
            fehlermuster_beschreibung=quelle.fehlermuster_beschreibung,
            lernauftrag=quelle.lernauftrag,
            arbeitsheft_beschreibung=quelle.arbeitsheft_beschreibung,
            arbeitsheft_text=quelle.arbeitsheft_text,
            arbeitsheft_bild=quelle.arbeitsheft_bild.name,
            schuelerin_name=quelle.schuelerin_name,
            schuelerin_geschlecht=quelle.schuelerin_geschlecht,
            lehrperson_name=quelle.lehrperson_name,
            lehrperson_geschlecht=quelle.lehrperson_geschlecht,
            fach=quelle.fach,
            thema=quelle.thema,
            klassenstufe=quelle.klassenstufe,
            referenzdiagnose=quelle.referenzdiagnose,
            budget_typ=quelle.budget_typ,
            budget_wert=quelle.budget_wert,
        )

    @transaction.atomic
    def vorspulen(self) -> None:
        """Pinnt einen Entwurf auf die aktuellste finale Kern-Fassung."""
        if not type(self).objects.filter(
            pk=self.pk,
            zustand=self.Zustand.ENTWURF,
        ).exists():
            raise ValidationError("Nur Entwürfe können vorgespult werden.")
        self.gepinnter_kern = Simulationskern.objects.filter(
            zustand=Simulationskern.Zustand.FINAL
        ).latest("finalisiert_am", "pk")
        self.save(update_fields=["gepinnter_kern"])

    @transaction.atomic
    def archivieren(self) -> None:
        """Archiviert eine finale Fassung."""
        if not type(self).objects.filter(
            pk=self.pk,
            zustand=self.Zustand.FINAL,
        ).exists():
            raise ValidationError("Nur finale Fassungen können archiviert werden.")
        self._zustand_wechseln(self.Zustand.ARCHIVIERT, ["zustand"])

    @transaction.atomic
    def entarchivieren(self) -> None:
        """Macht eine archivierte Fassung wieder final."""
        if not type(self).objects.filter(
            pk=self.pk,
            zustand=self.Zustand.ARCHIVIERT,
        ).exists():
            raise ValidationError("Nur archivierte Fassungen können entarchiviert werden.")
        self._zustand_wechseln(self.Zustand.FINAL, ["zustand"])

    @transaction.atomic
    def finalisieren(self) -> None:
        """Prüft einen Entwurf und friert ihn als finale Fassung ein."""
        if self.zustand != self.Zustand.ENTWURF:
            raise ValidationError("Nur Entwürfe können finalisiert werden.")
        fehlende_felder: list[str] = [
            feldname
            for feldname in _PFLICHTFELD_NAMEN
            if not getattr(self, feldname)
        ]
        if fehlende_felder:
            raise ValidationError(
                f"Zum Finalisieren fehlen: {', '.join(fehlende_felder)}."
            )
        if not self.arbeitsheft_text and not self.arbeitsheft_bild:
            raise ValidationError(
                "Zum Finalisieren braucht das Arbeitsheft Text oder ein Bild."
            )
        if self.budget_wert is None or self.budget_wert <= 0:
            raise ValidationError("Zum Finalisieren muss das Budget größer als 0 sein.")
        if self.gepinnter_kern is None:
            raise ValidationError("Zum Finalisieren fehlt ein gepinnter Simulationskern.")
        if self.gepinnter_kern.zustand == Simulationskern.Zustand.ARCHIVIERT:
            raise ValidationError(
                "Der gepinnte Simulationskern wurde archiviert; bitte vorspulen()."
            )
        if self.gepinnter_kern.zustand != Simulationskern.Zustand.FINAL:
            raise ValidationError("Der gepinnte Simulationskern ist nicht final.")

        self.finalisiert_am = timezone.now()
        self._zustand_wechseln(
            self.Zustand.FINAL,
            ["zustand", "finalisiert_am"],
        )

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


def prompt_platzhalter(vignette: Vignette) -> dict[str, str]:
    """Liefert die Rohwerte der Vignette für Prompt-Vorlagen."""

    return {
        "fehlermuster_beschreibung": vignette.fehlermuster_beschreibung,
        "lernauftrag": vignette.lernauftrag,
        "arbeitsheft_beschreibung": vignette.arbeitsheft_beschreibung,
        "schuelerin_name": vignette.schuelerin_name,
        "schuelerin_geschlecht": vignette.schuelerin_geschlecht,
        "fach": vignette.fach,
        "thema": vignette.thema,
        "klassenstufe": vignette.klassenstufe,
    }


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

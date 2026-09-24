"""Persistenzmodelle einer Sitzung."""

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q


class Teilnahme(models.Model):
    """Die anonyme Klammer für Sitzungen eines Aufrufers."""

    # Die drei Einwilligungen einer Erhebungsteilnahme; `None` heißt nicht
    # entschieden oder nicht angeboten. Die Audioverarbeitung heißt in der
    # Oberfläche Spracherkennung und wird auch im Training eingeholt.
    sprachmodell_eingewilligt: models.BooleanField = models.BooleanField(
        null=True,
        default=None,
    )
    audioverarbeitung_eingewilligt: models.BooleanField = models.BooleanField(
        null=True,
        default=None,
    )
    speicherung_eingewilligt: models.BooleanField = models.BooleanField(
        null=True,
        default=None,
    )

    @property
    def hat_in_audioverarbeitung_eingewilligt(self) -> bool:
        """Macht die serverseitige Voraussetzung für Transkription abfragbar."""
        return self.audioverarbeitung_eingewilligt is True

    @property
    def ist_fluechtig(self) -> bool:
        """Wer der Speicherung widersprochen hat, macht eine flüchtige Teilnahme.

        Unentschieden bleibt sie etwa im Training und wird dort gespeichert.
        """
        return self.speicherung_eingewilligt is False

    @staticmethod
    def fluechtig_q(pfad: str = "") -> Q:
        """Dieselbe Regel wie `ist_fluechtig` für Abfragen über eine Beziehung."""
        return Q(**{f"{pfad}speicherung_eingewilligt": False})


class Sitzung(models.Model):
    """Eine persistierte Sitzung einer Vignette."""

    class Status(models.TextChoices):
        """Die möglichen Ausgänge einer Sitzung."""

        LAUFEND: tuple[str, str] = "laufend", "Laufend"
        ABGESCHLOSSEN: tuple[str, str] = "abgeschlossen", "Abgeschlossen"
        ABGEBROCHEN: tuple[str, str] = "abgebrochen", "Abgebrochen"
        GESCHEITERT: tuple[str, str] = "gescheitert", "Gescheitert"

    teilnahme: models.ForeignKey = models.ForeignKey(
        Teilnahme,
        on_delete=models.CASCADE,
    )
    vignette: models.ForeignKey = models.ForeignKey(
        "vignetten.Vignette",
        on_delete=models.PROTECT,
    )
    simulationskern: models.ForeignKey = models.ForeignKey(
        "simulation.Simulationskern",
        on_delete=models.PROTECT,
    )
    modell_konfiguration: models.ForeignKey = models.ForeignKey(
        "simulation.ModellKonfiguration",
        on_delete=models.PROTECT,
    )
    status: models.CharField = models.CharField(
        max_length=13,
        choices=Status,
        default=Status.LAUFEND,
    )
    erstellt_am: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        null=True,
    )
    verbrauchte_zeit: models.FloatField = models.FloatField(default=0.0)
    offene_spanne_seit: models.DateTimeField = models.DateTimeField(null=True)

    @property
    def gespraechsschritte(self) -> models.QuerySet["Gespraechsschritt"]:
        """Liefert die Gesprächsschritte dieser Sitzung in ihrer Reihenfolge."""

        return self.gespraechsschritt_set.order_by("reihenfolge")


class Eingabemodus(models.TextChoices):
    """Die Herkunft eines abgeschickten Textes der Teilnehmer:in."""

    GETIPPT: tuple[str, str] = "getippt", "Getippt"
    TRANSKRIBIERT: tuple[str, str] = "transkribiert", "Transkribiert"
    GEMISCHT: tuple[str, str] = "gemischt", "Gemischt"

    @classmethod
    def aus_formular(cls, wert: str | None) -> "Eingabemodus":
        """Liest den Modus als Beobachtung: fehlend oder unbekannt heißt getippt.

        Der Wert kommt aus dem Browser und hat keine Steuerwirkung; er darf
        deshalb nie zu einer abgewiesenen Anfrage führen.
        """

        return cls(wert) if wert in cls.values else cls.GETIPPT


class GespraechsschrittManager(models.Manager["Gespraechsschritt"]):
    """Schreibt answerless Schritte atomar mit ihren Fehlversuchen."""

    @transaction.atomic
    def answerless_anlegen(
        self,
        *,
        sitzung: "Sitzung",
        eingabe: str,
        reihenfolge: int,
        fehlversuche: list["Fehlversuch"],
        eingabemodus: str = Eingabemodus.GETIPPT,
    ) -> "Gespraechsschritt":
        """Legt einen Abbruchschritt erst nach seinen Fehlversuchen answerless an."""

        schritt: Gespraechsschritt = self.create(
            sitzung=sitzung,
            eingabe=eingabe,
            denkspur="",
            aeusserung="",
            reihenfolge=reihenfolge,
            eingabemodus=eingabemodus,
        )
        Fehlversuch.objects.bulk_create(
            [
                Fehlversuch(
                    pk=fehlversuch.pk,
                    gespraechsschritt=schritt,
                    grund=fehlversuch.grund,
                    rohantwort=fehlversuch.rohantwort,
                )
                for fehlversuch in fehlversuche
            ]
        )
        self.filter(pk=schritt.pk).update(denkspur=None, aeusserung=None)
        schritt.denkspur = None
        schritt.aeusserung = None
        return schritt


class Gespraechsschritt(models.Model):
    """Eine Eingabe mit einer geglückten oder endgültig gescheiterten Antwort."""

    erstellt_am: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        null=True,
    )
    sitzung: models.ForeignKey = models.ForeignKey(Sitzung, on_delete=models.CASCADE)
    eingabe: models.TextField = models.TextField()
    denkspur: models.TextField = models.TextField(null=True, blank=True)
    aeusserung: models.TextField = models.TextField(null=True, blank=True)
    reihenfolge: models.PositiveIntegerField = models.PositiveIntegerField()
    eingabemodus: models.CharField = models.CharField(
        max_length=13,
        choices=Eingabemodus,
        default=Eingabemodus.GETIPPT,
    )

    objects: GespraechsschrittManager = GespraechsschrittManager()

    class Meta:
        """Sichert die Struktur jedes gespeicherten Gesprächsschritts."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["sitzung", "reihenfolge"],
                name="sitzungen_reihenfolge_ist_je_sitzung_eindeutig",
            ),
            models.CheckConstraint(
                condition=(
                    Q(denkspur__isnull=False, aeusserung__isnull=False)
                    | Q(denkspur__isnull=True, aeusserung__isnull=True)
                ),
                name="sitzungen_antwort_hat_denkspur_und_aeusserung_oder_keine",
            ),
        ]


class Fehlversuch(models.Model):
    """Eine verworfene Modellantwort neben ihrem Gesprächsschritt."""

    gespraechsschritt: models.ForeignKey = models.ForeignKey(
        Gespraechsschritt,
        on_delete=models.PROTECT,
    )
    grund: models.TextField = models.TextField()
    rohantwort: models.TextField = models.TextField()


class Diagnose(models.Model):
    """Die einmalige, freie Diagnose am Ende einer Sitzung."""

    erstellt_am: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        null=True,
    )
    sitzung: models.OneToOneField = models.OneToOneField(
        Sitzung,
        on_delete=models.CASCADE,
    )
    text: models.TextField = models.TextField()
    eingabemodus: models.CharField = models.CharField(
        max_length=13,
        choices=Eingabemodus,
        default=Eingabemodus.GETIPPT,
    )


class Vignettenposition(models.Model):
    """Eine gespielte Vignetten-Fassung an ihrer Position in einer Teilnahme."""

    teilnahme: models.ForeignKey = models.ForeignKey(
        Teilnahme,
        on_delete=models.CASCADE,
        related_name="vignettenpositionen",
    )
    sitzung: models.OneToOneField = models.OneToOneField(
        Sitzung,
        on_delete=models.CASCADE,
    )
    position: models.PositiveIntegerField = models.PositiveIntegerField()
    vignette: models.ForeignKey = models.ForeignKey(
        "vignetten.Vignette",
        on_delete=models.PROTECT,
    )

    def clean(self) -> None:
        """Bindet Sitzung und gespielte Fassung an dieselbe Teilnahme."""

        fehler: dict[str, str] = {}
        if self.sitzung.teilnahme_id != self.teilnahme_id:
            fehler["sitzung"] = "Die Sitzung gehört zu einer anderen Teilnahme."
        if self.sitzung.vignette_id != self.vignette_id:
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
                fields=["teilnahme", "position"],
                name="sitzungen_position_ist_je_teilnahme_eindeutig",
            ),
        ]

"""Persistenzmodelle einer Sitzung."""

from django.db import models, transaction
from django.db.models import Q


class Teilnahme(models.Model):
    """Die anonyme Klammer für Sitzungen eines Aufrufers."""

    einwilligung_erteilt: models.BooleanField = models.BooleanField(default=False)
    audioverarbeitung_eingewilligt: models.BooleanField = models.BooleanField(
        null=True,
        default=None,
    )

    @property
    def hat_in_audioverarbeitung_eingewilligt(self) -> bool:
        """Macht die serverseitige Voraussetzung für Transkription abfragbar."""
        return self.audioverarbeitung_eingewilligt is True


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
    ) -> "Gespraechsschritt":
        """Legt einen Abbruchschritt erst nach seinen Fehlversuchen answerless an."""

        schritt: Gespraechsschritt = self.create(
            sitzung=sitzung,
            eingabe=eingabe,
            denkspur="",
            aeusserung="",
            reihenfolge=reihenfolge,
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
    native_reasoning_spur: models.TextField = models.TextField(null=True, blank=True)
    reihenfolge: models.PositiveIntegerField = models.PositiveIntegerField()

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

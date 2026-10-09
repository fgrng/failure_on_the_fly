"""Evallauf, Evalgespräch, Wechsel und Urteil (ADR-0046).

Quote und Bestehen sind abgeleitet und werden nie gespeichert.
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils import timezone

from simulation.models import (
    Eval,
    Evalinput,
    Evalkatalog,
    Evalkriterium,
    ModellKonfiguration,
    Simulationskern,
    UebergreifendesKriterium,
    Verwendung,
    evals_verfuegbar,
)
from vignetten.models import Vignette, prompt_platzhalter

_LAEUFT_SCHON: str = "Für diese Fassung wartet oder läuft bereits ein Evallauf."


@dataclass(frozen=True)
class Zelle:
    """Quote und Bestehen eines Kriteriums über die Wiederholungen eines Evalinputs."""

    kriterium: str
    erfuellt: int
    ohne_urteil: int
    k: int

    @property
    def bestanden(self) -> bool:
        """Bestanden nur, wenn jede der k Wiederholungen erfüllt ist (pass^k)."""

        return self.erfuellt == self.k


@dataclass(frozen=True)
class Inputzeile:
    """Die Zellen eines Evalinputs, eine je Kriterium seines Evals."""

    nummer: int
    kuerzel: str
    zellen: list[Zelle]


@dataclass(frozen=True)
class Evalergebnis:
    """Die Übersicht eines Evals: Evalinputs mal Kriterien."""

    name: str
    kriterien: list[str]
    zeilen: list[Inputzeile]


class EvallaufManager(models.Manager["Evallauf"]):
    """Schreibnaht für neue Evalläufe."""

    def ausloesen(self, vignette: Vignette) -> "Evallauf":
        """Hält den Eingabestand der Fassung fest und stellt einen Lauf in die Warteschlange.

        Ein fertiger oder abgebrochener Vorgänger wird im selben Zug ersetzt;
        scheitert eine Prüfung, bleibt er unverändert.
        """

        if not evals_verfuegbar():
            raise ValidationError("Evals sind derzeit nicht verfügbar.")
        try:
            with transaction.atomic():
                return self._ausloesen(Vignette.objects.get(pk=vignette.pk))
        except IntegrityError:
            raise ValidationError(_LAEUFT_SCHON) from None

    def _ausloesen(self, vignette: Vignette) -> "Evallauf":
        # Prüft und ersetzt in einer Transaktion; der Stand der Fassung ist
        # der eben gelesene, nicht der eines älteren Objekts der Aufruferin.

        if vignette.zustand == Vignette.Zustand.ARCHIVIERT:
            raise ValidationError("Archivierte Fassungen lassen sich nicht prüfen.")
        if vignette.gepinnter_kern is None:
            raise ValidationError("Der Fassung fehlt ein gepinnter Simulationskern.")
        if self.filter(
            vignette=vignette,
            zustand__in=[Evallauf.Zustand.WARTET, Evallauf.Zustand.LAEUFT],
        ).exists():
            raise ValidationError(_LAEUFT_SCHON)
        self.filter(vignette=vignette).delete()
        return self.create(
            vignette=vignette,
            kern=vignette.gepinnter_kern,
            katalog=Evalkatalog.objects.finale_fassung(),
            schuelerin_konfiguration=ModellKonfiguration.objects.belegte(
                Verwendung.SCHUELERIN
            ),
            lehrperson_konfiguration=ModellKonfiguration.objects.belegte(
                Verwendung.LEHRPERSON
            ),
            bewerter_konfiguration=ModellKonfiguration.objects.belegte(
                Verwendung.BEWERTER
            ),
            platzhalter=prompt_platzhalter(vignette),
        )


class Evallauf(models.Model):
    """Die Ausführung aller Evals des Katalogs über einer Vignettenfassung."""

    class Zustand(models.TextChoices):
        """Der Zustand ist zugleich die Warteschlange (ADR-0047)."""

        WARTET = "wartet", "Wartet"
        LAEUFT = "laeuft", "Läuft"
        FERTIG = "fertig", "Fertig"
        ABGEBROCHEN = "abgebrochen", "Abgebrochen"

    vignette: models.OneToOneField = models.OneToOneField(
        Vignette, on_delete=models.CASCADE, related_name="evallauf"
    )
    kern: models.ForeignKey = models.ForeignKey(
        Simulationskern, on_delete=models.PROTECT, related_name="+"
    )
    katalog: models.ForeignKey = models.ForeignKey(
        Evalkatalog, on_delete=models.PROTECT, related_name="+"
    )
    schuelerin_konfiguration: models.ForeignKey = models.ForeignKey(
        ModellKonfiguration, on_delete=models.PROTECT, related_name="+"
    )
    lehrperson_konfiguration: models.ForeignKey = models.ForeignKey(
        ModellKonfiguration, on_delete=models.PROTECT, related_name="+"
    )
    bewerter_konfiguration: models.ForeignKey = models.ForeignKey(
        ModellKonfiguration, on_delete=models.PROTECT, related_name="+"
    )
    # Die Prompt-Platzhalter der Fassung beim Auslösen: Ein Entwurf, der
    # während Wartezeit oder Ausführung gespeichert wird, ändert den Lauf nicht.
    platzhalter: models.JSONField = models.JSONField()
    zustand: models.CharField = models.CharField(
        max_length=11, choices=Zustand, default=Zustand.WARTET
    )
    ausgeloest_am: models.DateTimeField = models.DateTimeField(default=timezone.now)
    gestartet_am: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    beendet_am: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    objects: EvallaufManager = EvallaufManager()

    @property
    def ist_offen(self) -> bool:
        """Ob der Lauf wartet oder läuft; dann gibt es keinen zweiten Start."""

        return self.zustand in (self.Zustand.WARTET, self.Zustand.LAEUFT)

    def uebersicht(self) -> list[Evalergebnis]:
        """Je Eval die Quoten aller Evalinputs und Kriterien, in Katalogreihenfolge.

        Beispiel: Bei k = 3 und den Urteilen erfüllt, nicht erfüllt, erfüllt
        steht in der Zelle ``Zelle(kriterium, erfuellt=2, ohne_urteil=0, k=3)``,
        und sie besteht nicht.
        """

        zaehler: dict[tuple[int, str, int], list[int]] = {}
        for urteil in Urteil.objects.filter(gespraech__evallauf=self).select_related(
            "gespraech"
        ):
            schluessel: tuple[int, str, int] = (
                urteil.gespraech.evalinput_id,
                *urteil.kriterium_schluessel,
            )
            stand: list[int] = zaehler.setdefault(schluessel, [0, 0])
            if urteil.erfuellt is True:
                stand[0] += 1
            elif urteil.erfuellt is None:
                stand[1] += 1
        uebergreifende: list[UebergreifendesKriterium] = list(
            self.katalog.uebergreifende_kriterien.all()
        )
        ergebnisse: list[Evalergebnis] = []
        eval_: Eval
        for eval_ in self.katalog.evals.prefetch_related(
            "kriterien", "inputs__schritte"
        ):
            kriterien: list[tuple[str, int, str]] = [
                ("eval", kriterium.pk, kriterium.text)
                for kriterium in eval_.kriterien.all()
            ] + [
                ("uebergreifend", kriterium.pk, kriterium.text)
                for kriterium in uebergreifende
            ]
            zeilen: list[Inputzeile] = []
            evalinput: Evalinput
            for nummer, evalinput in enumerate(eval_.inputs.all(), 1):
                zellen: list[Zelle] = []
                for art, pk, text in kriterien:
                    erfuellt, ohne_urteil = zaehler.get((evalinput.pk, art, pk), [0, 0])
                    zellen.append(Zelle(text, erfuellt, ohne_urteil, self.katalog.k))
                zeilen.append(Inputzeile(nummer, evalinput.kuerzel, zellen))
            ergebnisse.append(
                Evalergebnis(
                    eval_.name or "Unbenanntes Eval",
                    [text for _, _, text in kriterien],
                    zeilen,
                )
            )
        return ergebnisse


class Evalgespraech(models.Model):
    """Eine Wiederholung eines Evalinputs zwischen simulierter Lehrperson und Schüler:in."""

    evallauf: models.ForeignKey = models.ForeignKey(
        Evallauf, on_delete=models.CASCADE, related_name="gespraeche"
    )
    evalinput: models.ForeignKey = models.ForeignKey(
        Evalinput, on_delete=models.PROTECT, related_name="+"
    )
    wiederholung: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField()

    class Meta:
        """Jede Wiederholung eines Evalinputs gibt es je Lauf einmal."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["evallauf", "evalinput", "wiederholung"],
                name="evals_gespraech_wiederholung_eindeutig",
            ),
        ]


class Wechsel(models.Model):
    """Ein Inputschritt im Evalgespräch: Äußerung der Lehrperson und Antwort.

    Ohne Äußerung der Schüler:in ist der Antwortversuch endgültig gescheitert
    (wie ADR-0011); die Fehlversuche stehen daneben.
    """

    gespraech: models.ForeignKey = models.ForeignKey(
        Evalgespraech, on_delete=models.CASCADE, related_name="wechsel"
    )
    position: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField()
    lehrperson_aeusserung: models.TextField = models.TextField()
    denkspur: models.TextField = models.TextField(blank=True, default="")
    aeusserung: models.TextField = models.TextField(null=True, blank=True)
    # Je Fehlversuch {"grund": …, "rohantwort": …}, in Reihenfolge.
    fehlversuche: models.JSONField = models.JSONField(default=list, blank=True)

    class Meta:
        """Die Wechsel eines Gesprächs stehen in ihrer Reihenfolge."""

        ordering: list[str] = ["position"]
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["gespraech", "position"],
                name="evals_wechsel_position_eindeutig",
            ),
        ]


class Urteil(models.Model):
    """Das Ergebnis genau eines Kriteriums an einem Evalgespräch.

    `erfuellt` ist dreiwertig: leer heißt *ohne Urteil*.
    """

    gespraech: models.ForeignKey = models.ForeignKey(
        Evalgespraech, on_delete=models.CASCADE, related_name="urteile"
    )
    evalkriterium: models.ForeignKey = models.ForeignKey(
        Evalkriterium,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    uebergreifendes_kriterium: models.ForeignKey = models.ForeignKey(
        UebergreifendesKriterium,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    erfuellt: models.BooleanField = models.BooleanField(null=True)
    begruendung: models.TextField = models.TextField(blank=True, default="")

    class Meta:
        """Genau ein Kriterium je Urteil, je Gespräch und Kriterium ein Urteil."""

        constraints: list[models.BaseConstraint] = [
            models.CheckConstraint(
                condition=(
                    Q(
                        evalkriterium__isnull=False,
                        uebergreifendes_kriterium__isnull=True,
                    )
                    | Q(
                        evalkriterium__isnull=True,
                        uebergreifendes_kriterium__isnull=False,
                    )
                ),
                name="evals_urteil_genau_ein_kriterium",
            ),
            models.UniqueConstraint(
                fields=["gespraech", "evalkriterium"],
                name="evals_urteil_je_evalkriterium",
            ),
            models.UniqueConstraint(
                fields=["gespraech", "uebergreifendes_kriterium"],
                name="evals_urteil_je_uebergreifendem_kriterium",
            ),
        ]

    @property
    def kriterium_schluessel(self) -> tuple[str, int]:
        """Art und Primärschlüssel des beurteilten Kriteriums."""

        if self.evalkriterium_id is not None:
            return ("eval", self.evalkriterium_id)
        return ("uebergreifend", self.uebergreifendes_kriterium_id)

"""Evallauf, Evalgespräch, Wechsel und Urteil (ADR-0046).

Quote und Bestehen sind abgeleitet und werden nie gespeichert.
"""

from collections import Counter
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
    Inputschritt,
    ModellKonfiguration,
    Simulationskern,
    UebergreifendesKriterium,
    Verwendung,
    evals_verfuegbar,
)
from vignetten.models import Vignette, prompt_platzhalter

_LAEUFT_SCHON: str = "Für diese Fassung wartet oder läuft bereits ein Evallauf."

# Was ein Urteil beurteilt: ein Evalkriterium oder ein übergreifendes Kriterium.
type Kriterium = Evalkriterium | UebergreifendesKriterium


@dataclass(frozen=True)
class Zelle:
    """Quote und Bestehen eines Kriteriums über die Wiederholungen eines Evalinputs."""

    kriterium: str
    erfuellt: int
    nicht_erfuellt: int
    ohne_urteil: int
    k: int

    @property
    def bestanden(self) -> bool:
        """Bestanden nur, wenn jede der k Wiederholungen erfüllt ist (pass^k)."""

        return self.erfuellt == self.k

    @property
    def ausstehend(self) -> int:
        """Wiederholungen ohne geschriebenes Urteil, etwa nach einem Abbruch."""

        return self.k - self.erfuellt - self.nicht_erfuellt - self.ohne_urteil


@dataclass(frozen=True)
class Inputzeile:
    """Die Zellen eines Evalinputs, eine je Kriterium seines Evals."""

    nummer: int
    kuerzel: str
    zellen: list[Zelle]
    evalinput_pk: int


@dataclass(frozen=True)
class Evalergebnis:
    """Die Übersicht eines Evals: Evalinputs mal Kriterien."""

    name: str
    kriterien: list[str]
    zeilen: list[Inputzeile]


@dataclass(frozen=True)
class Beurteilung:
    """Ein Kriterium eines Gesprächs mit seinem Urteil, sobald es geschrieben ist."""

    kriterium: str
    uebergreifend: bool
    urteil: "Urteil | None"


@dataclass(frozen=True)
class Einsicht:
    """Das gewählte Evalgespräch eines Laufs; ohne Gespräch nicht ausgeführt."""

    eval_name: str
    nummer: int
    evalinput: Evalinput
    wiederholung: int
    # Die Wiederholungen 1..k und ob es zu ihnen ein Gespräch gibt.
    wiederholungen: list[tuple[int, bool]]
    gespraech: "Evalgespraech | None"
    # Jeder geschriebene Wechsel mit dem Inputschritt, aus dem er entstand.
    wechsel: list[tuple["Wechsel", Inputschritt]]
    beurteilungen: list[Beurteilung]


def _anzeigename(eval_: Eval) -> str:
    # Der Name eines Evals; ein namenloses heißt „Unbenanntes Eval“.

    return eval_.name or "Unbenanntes Eval"


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

    @property
    def unvollstaendig(self) -> bool:
        """Ob mindestens ein Kriterium ohne Urteil blieb; ein Neustart lohnt."""

        return Urteil.objects.filter(
            gespraech__evallauf=self, erfuellt__isnull=True
        ).exists()

    @property
    def bestanden(self) -> bool:
        """Insgesamt bestanden nur als fertiger Lauf, in dem jede Zelle besteht.

        Ein wartender, laufender oder abgebrochener Teilstand besteht nie,
        auch wenn jedes bisher geschriebene Urteil erfüllt ist.
        """

        return self.zustand == self.Zustand.FERTIG and all(
            zelle.bestanden
            for ergebnis in self.uebersicht()
            for zeile in ergebnis.zeilen
            for zelle in zeile.zellen
        )

    def uebersicht(self) -> list[Evalergebnis]:
        """Je Eval die Quoten aller Evalinputs und Kriterien, in Katalogreihenfolge.

        Beispiel: Bei k = 3 und den Urteilen erfüllt, nicht erfüllt, erfüllt
        steht in der Zelle ``Zelle(kriterium, erfuellt=2, nicht_erfuellt=1,
        ohne_urteil=0, k=3)``, und sie besteht nicht.
        """

        # Je Evalinput, Kriterium und Ausgang (erfüllt, nicht erfüllt, ohne
        # Urteil) die Zahl der Urteile.
        zaehler: Counter[tuple[int, type[Kriterium], int, bool | None]] = Counter(
            (
                urteil.gespraech.evalinput_id,
                *urteil.kriterium_schluessel,
                urteil.erfuellt,
            )
            for urteil in Urteil.objects.filter(
                gespraech__evallauf=self
            ).select_related("gespraech")
        )
        ergebnisse: list[Evalergebnis] = []
        for eval_, kriterien in self.evals_mit_kriterien():
            zeilen: list[Inputzeile] = []
            evalinput: Evalinput
            for nummer, evalinput in enumerate(eval_.inputs.all(), 1):
                zellen: list[Zelle] = []
                for kriterium in kriterien:
                    schluessel: tuple[int, type[Kriterium], int] = (
                        evalinput.pk,
                        type(kriterium),
                        kriterium.pk,
                    )
                    zellen.append(
                        Zelle(
                            kriterium.text,
                            erfuellt=zaehler[(*schluessel, True)],
                            nicht_erfuellt=zaehler[(*schluessel, False)],
                            ohne_urteil=zaehler[(*schluessel, None)],
                            k=self.katalog.k,
                        )
                    )
                zeilen.append(
                    Inputzeile(nummer, evalinput.kuerzel, zellen, evalinput.pk)
                )
            ergebnisse.append(
                Evalergebnis(
                    _anzeigename(eval_),
                    [kriterium.text for kriterium in kriterien],
                    zeilen,
                )
            )
        return ergebnisse

    def einsicht(
        self, evalinput_pk: int | None, wiederholung: int | None
    ) -> Einsicht | None:
        """Das Gespräch zu Evalinput und Wiederholung; ohne Evalinput keins.

        Ein Evalinput außerhalb des festgehaltenen Katalogs weicht dem ersten,
        eine Wiederholung außerhalb 1..k der ersten ausgeführten. Gespräche
        anderer Läufe sind so nie erreichbar.
        """

        # Je Evalinput sein Eval, dessen Kriterien und seine Nummer im Eval.
        kandidaten: dict[int, tuple[Eval, list[Kriterium], int, Evalinput]] = {
            evalinput.pk: (eval_, kriterien, nummer, evalinput)
            for eval_, kriterien in self.evals_mit_kriterien()
            for nummer, evalinput in enumerate(eval_.inputs.all(), 1)
        }
        if not kandidaten:
            return None
        eval_, kriterien, nummer, evalinput = (
            kandidaten[evalinput_pk]
            if evalinput_pk in kandidaten
            else next(iter(kandidaten.values()))
        )
        # Ein Gespräch ohne Wechsel und Urteil brach ab, bevor etwas geschah.
        gespraeche: dict[int, Evalgespraech] = {
            gespraech.wiederholung: gespraech
            for gespraech in self.gespraeche.filter(
                evalinput=evalinput
            ).prefetch_related("wechsel", "urteile")
            if gespraech.wechsel.all() or gespraech.urteile.all()
        }
        if wiederholung not in range(1, self.katalog.k + 1):
            wiederholung = min(gespraeche, default=1)
        gespraech: Evalgespraech | None = gespraeche.get(wiederholung)
        urteile: dict[tuple[type[Kriterium], int], Urteil] = (
            {urteil.kriterium_schluessel: urteil for urteil in gespraech.urteile.all()}
            if gespraech
            else {}
        )
        schritte: list[Inputschritt] = list(evalinput.schritte.all())
        return Einsicht(
            _anzeigename(eval_),
            nummer,
            evalinput,
            wiederholung,
            [(zahl, zahl in gespraeche) for zahl in range(1, self.katalog.k + 1)],
            gespraech,
            [
                (wechsel, schritte[wechsel.position - 1])
                for wechsel in (gespraech.wechsel.all() if gespraech else [])
            ],
            [
                Beurteilung(
                    kriterium.text,
                    isinstance(kriterium, UebergreifendesKriterium),
                    urteile.get((type(kriterium), kriterium.pk)),
                )
                for kriterium in kriterien
            ],
        )

    def evals_mit_kriterien(self) -> list[tuple[Eval, list[Kriterium]]]:
        """Je Eval des festgehaltenen Katalogs seine Kriterien, die übergreifenden zuletzt.

        Evalinputs und Schritte der Evals sind vorab geladen.
        """

        uebergreifende: list[UebergreifendesKriterium] = list(
            self.katalog.uebergreifende_kriterien.all()
        )
        return [
            (eval_, [*eval_.kriterien.all(), *uebergreifende])
            for eval_ in self.katalog.evals.prefetch_related(
                "kriterien", "inputs__schritte"
            )
        ]


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


class UrteilManager(models.Manager["Urteil"]):
    """Schreibnaht für Urteile."""

    def schreiben(
        self,
        gespraech: Evalgespraech,
        kriterium: Kriterium,
        erfuellt: bool | None,
        begruendung: str,
    ) -> "Urteil":
        """Legt das Urteil zu einem Kriterium an, gleich welcher Art es ist."""

        feld: str = (
            "evalkriterium"
            if isinstance(kriterium, Evalkriterium)
            else "uebergreifendes_kriterium"
        )
        return self.create(
            gespraech=gespraech,
            erfuellt=erfuellt,
            begruendung=begruendung,
            **{feld: kriterium},
        )


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

    objects: UrteilManager = UrteilManager()

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
    def kriterium_schluessel(self) -> tuple[type[Kriterium], int]:
        """Art und Primärschlüssel des beurteilten Kriteriums."""

        if self.evalkriterium_id is not None:
            return (Evalkriterium, self.evalkriterium_id)
        return (UebergreifendesKriterium, self.uebergreifendes_kriterium_id)

"""Datenmodell des Simulationskerns."""

from dataclasses import dataclass
from string import Template

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q

from simulation.lebenszyklus import (
    FassungManager,
    VersionierteFassung,
    lebenszyklus_constraints,
)

_UNVERAENDERLICH_FEHLERMELDUNG: str = "ModellKonfigurationen sind append-only."


VERTRAG_PROMPT: frozenset[str] = frozenset(
    {
        "fehlermuster_beschreibung",
        "lernauftrag",
        "arbeitsheft",
        "lernauftrag_simulationshinweise",
        "arbeitsheft_simulationshinweise",
        "schuelerin_name",
        "schuelerin_geschlecht",
        "fach",
        "thema",
        "klassenstufe",
    }
)
PROMPT_PLATZHALTER_MIT_UMGEBUNG: frozenset[str] = frozenset(
    {
        "fehlermuster_beschreibung",
        "lernauftrag",
        "arbeitsheft",
        "lernauftrag_simulationshinweise",
        "arbeitsheft_simulationshinweise",
    }
)
# Die Werte, die der Evallauf selbst berechnet, ergänzen den Promptvertrag;
# jede Vorlage des Evalkatalogs erhält nur ihren eigenen (ADR-0010).
VERTRAG_EVAL: frozenset[str] = VERTRAG_PROMPT | {
    "inputstrategie",
    "kriterium",
    "verlauf",
}
VERTRAG_LEHRPERSON: frozenset[str] = VERTRAG_PROMPT | {"inputstrategie", "verlauf"}
VERTRAG_BEWERTER: frozenset[str] = VERTRAG_PROMPT | {"kriterium", "verlauf"}
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
        """Hält die Kern-Historie als einzige Zeile."""

        constraints: list[models.BaseConstraint] = [
            models.CheckConstraint(
                condition=Q(id=1),
                name="simulation_kern_historie_ist_singleton",
            ),
        ]


class SimulationskernManager(FassungManager):
    """Schreibnaht für neue Fassungen des Simulationskerns."""

    @transaction.atomic
    def anlegen(
        self,
        *,
        system_prompt_vorlage: str = "",
        user_prompt_vorlage: str = "",
        rahmenhandlung_einleitung: str = "",
        rahmenhandlung_gespraechseinleitung: str = "",
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
            rahmenhandlung_gespraechseinleitung=rahmenhandlung_gespraechseinleitung,
            rahmenhandlung_debrief=rahmenhandlung_debrief,
        )


class Simulationskern(VersionierteFassung):
    """Eine versionierte Fassung der zentralen Simulationsvorgaben."""

    _bezeichnung: str = "Kern"

    historie: models.ForeignKey = models.ForeignKey(
        KernHistorie,
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
    rahmenhandlung_gespraechseinleitung: models.TextField = models.TextField(
        blank=True,
        default="",
    )
    rahmenhandlung_debrief: models.TextField = models.TextField(
        blank=True,
        default="",
    )

    objects: SimulationskernManager = SimulationskernManager()

    def _kopierwerte(self) -> dict[str, object]:
        # Ein neuer Kern-Entwurf übernimmt alle Vorlagen der finalen Fassung.

        return {
            "system_prompt_vorlage": self.system_prompt_vorlage,
            "user_prompt_vorlage": self.user_prompt_vorlage,
            "rahmenhandlung_einleitung": self.rahmenhandlung_einleitung,
            "rahmenhandlung_gespraechseinleitung": (
                self.rahmenhandlung_gespraechseinleitung
            ),
            "rahmenhandlung_debrief": self.rahmenhandlung_debrief,
        }

    def clean(self) -> None:
        """Lehnt Vorlagen mit Platzhaltern außerhalb ihres Vertrags ab."""

        fehler: dict[str, str] = {}
        vorlagenfeld: str
        erlaubte_platzhalter: frozenset[str]
        for vorlagenfeld, erlaubte_platzhalter in (
            ("system_prompt_vorlage", VERTRAG_PROMPT),
            ("user_prompt_vorlage", VERTRAG_PROMPT),
            ("rahmenhandlung_einleitung", VERTRAG_RAHMEN),
            ("rahmenhandlung_gespraechseinleitung", VERTRAG_RAHMEN),
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
        """Sichert die Lebenszyklus-Invarianten der Kern-Fassungen."""

        constraints: list[models.BaseConstraint] = lebenszyklus_constraints(
            "simulation"
        )


class EvalkatalogHistorie(models.Model):
    """Die einzige, namenlose Historie der Evalkatalog-Fassungen."""

    id: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        primary_key=True,
        default=1,
        editable=False,
    )

    class Meta:
        """Hält die Katalog-Historie als einzige Zeile."""

        constraints: list[models.BaseConstraint] = [
            models.CheckConstraint(
                condition=Q(id=1),
                name="simulation_evalkatalog_historie_ist_singleton",
            ),
        ]


class EvalkatalogManager(FassungManager):
    """Schreibnaht für neue Fassungen des Evalkatalogs."""

    @transaction.atomic
    def anlegen(self) -> "Evalkatalog":
        """Legt die erste Katalog-Fassung als leeren Entwurf an.

        Einen Standardkatalog gibt es nicht: Der erste Katalog entsteht in der
        Oberfläche (ADR-0046).
        """

        historie, _ = EvalkatalogHistorie.objects.get_or_create(pk=1)
        if self.filter(historie=historie).exists():
            raise ValueError("Der Evalkatalog wurde bereits angelegt.")
        return self._erstellen(historie=historie)

    def finale_fassung(self) -> "Evalkatalog | None":
        """Die Fassung, gegen die jeder Evallauf prüft, oder None ohne sie."""

        return self.filter(zustand=Evalkatalog.Zustand.FINAL).first()


def _vorlagenmangel(bezeichnung: str, vorlage: str, vertrag: frozenset[str]) -> str:
    # Prüft eine Vorlage wie beim Kern ohne Modellaufruf: nichtleer, gültig und
    # nur mit Platzhaltern ihres Vertrags. Liefert die Meldung oder "".

    if not vorlage.strip():
        return f"Die {bezeichnung} ist leer."
    template: Template = Template(vorlage)
    if not template.is_valid():
        return f"Die {bezeichnung} enthält einen ungültigen Platzhalter."
    fremde: list[str] = sorted(set(template.get_identifiers()) - vertrag)
    if fremde:
        return (
            f"Die {bezeichnung} enthält Platzhalter außerhalb ihres Vertrags: "
            + ", ".join(f"${name}" for name in fremde)
            + "."
        )
    return ""


class Evalkatalog(VersionierteFassung):
    """Eine versionierte Fassung der Evals, Kriterien und Vorlagen (ADR-0046)."""

    _bezeichnung: str = "Evalkatalog"

    historie: models.ForeignKey = models.ForeignKey(
        EvalkatalogHistorie,
        on_delete=models.PROTECT,
    )
    k: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        "k",
        default=3,
        help_text="Wie oft jeder Evalinput durchgespielt wird.",
    )
    lehrperson_vorlage: models.TextField = models.TextField(
        "Lehrperson-Vorlage",
        blank=True,
        default="",
    )
    bewerter_vorlage: models.TextField = models.TextField(
        "Bewerter-Vorlage",
        blank=True,
        default="",
    )

    objects: EvalkatalogManager = EvalkatalogManager()

    def _kopierwerte(self) -> dict[str, object]:
        # Ein neuer Katalog-Entwurf übernimmt Durchlauf und Vorlagen.

        return {
            "k": self.k,
            "lehrperson_vorlage": self.lehrperson_vorlage,
            "bewerter_vorlage": self.bewerter_vorlage,
        }

    @transaction.atomic
    def bearbeiten(self) -> "Evalkatalog":
        """Erzeugt einen neuen Entwurf samt Kopie der Kriterien und des Eval-Baums."""

        entwurf: Evalkatalog = super().bearbeiten()
        for kriterium in self.uebergreifende_kriterien.all():
            UebergreifendesKriterium(
                katalog=entwurf, position=kriterium.position, text=kriterium.text
            ).save()
        for eval_ in self.evals.all():
            kopie: Eval = Eval(
                katalog=entwurf, position=eval_.position, name=eval_.name
            )
            kopie.save()
            for evalkriterium in eval_.kriterien.all():
                Evalkriterium(
                    eval=kopie, position=evalkriterium.position, text=evalkriterium.text
                ).save()
            for evalinput in eval_.inputs.all():
                input_kopie: Evalinput = Evalinput(
                    eval=kopie, position=evalinput.position
                )
                input_kopie.save()
                for schritt in evalinput.schritte.all():
                    Inputschritt(
                        evalinput=input_kopie,
                        position=schritt.position,
                        art=schritt.art,
                        text=schritt.text,
                    ).save()
        return entwurf

    def maengel(self) -> list[str]:
        """Was dem Entwurf zum Finalisieren fehlt, je Lücke eine Meldung.

        Ein Entwurf darf unvollständig gespeichert werden; geprüft wird erst
        beim Finalisieren. Übergreifende Kriterien dürfen fehlen.
        """

        meldungen: list[str] = [
            _vorlagenmangel(
                "Lehrperson-Vorlage", self.lehrperson_vorlage, VERTRAG_LEHRPERSON
            ),
            _vorlagenmangel(
                "Bewerter-Vorlage", self.bewerter_vorlage, VERTRAG_BEWERTER
            ),
        ]
        if self.k < 1:
            meldungen.append("k muss mindestens 1 sein.")
        for nummer, kriterium in enumerate(self.uebergreifende_kriterien.all(), 1):
            if not kriterium.text.strip():
                meldungen.append(f"Übergreifendes Kriterium {nummer} ist leer.")
        evals: models.QuerySet[Eval] = self.evals.prefetch_related(
            "kriterien", "inputs__schritte"
        )
        if not evals:
            meldungen.append("Der Evalkatalog hat kein Eval.")
        for eval_ in evals:
            name: str = f"Eval „{eval_.name or 'Unbenanntes Eval'}“"
            kriterien: list[Evalkriterium] = list(eval_.kriterien.all())
            inputs: list[Evalinput] = list(eval_.inputs.all())
            if not kriterien:
                meldungen.append(f"{name} hat kein Evalkriterium.")
            if not inputs:
                meldungen.append(f"{name} hat keinen Evalinput.")
            for nummer, kriterium in enumerate(kriterien, 1):
                if not kriterium.text.strip():
                    meldungen.append(f"Evalkriterium {nummer} von {name} ist leer.")
            for nummer, evalinput in enumerate(inputs, 1):
                schritte: list[Inputschritt] = list(evalinput.schritte.all())
                if not schritte:
                    meldungen.append(
                        f"Evalinput {nummer} von {name} hat keinen Inputschritt."
                    )
                for schrittnummer, schritt in enumerate(schritte, 1):
                    if not schritt.text.strip():
                        meldungen.append(
                            f"Inputschritt {schrittnummer} in Evalinput {nummer} "
                            f"von {name} ist leer."
                        )
        return [meldung for meldung in meldungen if meldung]

    @transaction.atomic
    def finalisieren(self) -> None:
        """Finalisiert einen vollständigen Entwurf; sonst nennt der Fehler alle Lücken."""

        maengel: list[str] = self.maengel()
        if maengel:
            raise ValidationError(maengel)
        super().finalisieren()

    def kriterium_anlegen(self, text: str = "") -> "UebergreifendesKriterium":
        """Hängt ein übergreifendes Kriterium ans Ende der Liste."""

        return UebergreifendesKriterium.anhaengen(self, text=text)

    def eval_anlegen(self, name: str = "") -> "Eval":
        """Hängt ein Eval ans Ende des Katalogs."""

        return Eval.anhaengen(self, name=name)

    class Meta:
        """Sichert die Lebenszyklus-Invarianten der Katalog-Fassungen."""

        constraints: list[models.BaseConstraint] = lebenszyklus_constraints(
            "simulation_evalkatalog"
        )


_NUR_AM_ENTWURF: str = "Der Evalkatalog ändert sich nur an einem Entwurf."


def _nur_an_entwuerfen(katalog_ids: set[int]) -> None:
    # Teile des Katalogs teilen die Schreibsperre ihrer Fassung: Jede
    # betroffene Fassung muss ein Entwurf sein.

    entwuerfe: int = Evalkatalog.objects.filter(
        pk__in=katalog_ids, zustand=Evalkatalog.Zustand.ENTWURF
    ).count()
    if entwuerfe != len(katalog_ids):
        raise RuntimeError(_NUR_AM_ENTWURF)


class KatalogteilQuerySet(models.QuerySet["Katalogteil"]):
    """Hält auch gesammelte Schreibzugriffe an der Schreibsperre der Fassung."""

    def update(self, **kwargs: object) -> int:
        """Verhindert Massenänderungen an Teilen des Katalogs."""

        raise RuntimeError(_NUR_AM_ENTWURF)

    def bulk_create(
        self, objs: list["Katalogteil"], **kwargs: object
    ) -> list["Katalogteil"]:
        """Verhindert das Umgehen der Schreibsperre per Masseneinfügen."""

        raise RuntimeError(_NUR_AM_ENTWURF)

    def bulk_update(
        self,
        objs: list["Katalogteil"],
        fields: list[str],
        **kwargs: object,
    ) -> int:
        """Verhindert das Umgehen der Schreibsperre per Massenupdate."""

        raise RuntimeError(_NUR_AM_ENTWURF)

    def delete(self) -> tuple[int, dict[str, int]]:
        """Löscht gesammelt nur Teile von Entwürfen."""

        _nur_an_entwuerfen(set(self.values_list(self.model._katalog_pfad, flat=True)))
        return super().delete()


class Katalogteil(models.Model):
    """Ein geordneter Teil einer Evalkatalog-Fassung, änderbar nur am Entwurf.

    Vertrag der Unterklassen: `_eltern` nennt den Fremdschlüssel, unter dem die
    Geschwister hängen, `_katalog_pfad` den Lookup bis zur Fassung. Hängt ein
    Teil nicht direkt am Katalog, beginnt sein Pfad mit `<_eltern>__`, etwa
    `eval__katalog_id`.
    """

    _eltern: str
    _katalog_pfad: str

    position: models.PositiveIntegerField = models.PositiveIntegerField()

    objects: models.Manager = models.Manager.from_queryset(KatalogteilQuerySet)()

    class Meta:
        """Ordnet die Teile nach ihrer gespeicherten Position."""

        abstract: bool = True
        ordering: list[str] = ["position"]

    @classmethod
    def anhaengen(cls, eltern: models.Model, **werte: object) -> "Katalogteil":
        """Legt einen Teil hinter dem letzten seiner Geschwister an."""

        letzte: int = (
            cls.objects.filter(**{cls._eltern: eltern}).aggregate(
                models.Max("position")
            )["position__max"]
            or 0
        )
        teil: Katalogteil = cls(**{cls._eltern: eltern}, position=letzte + 1, **werte)
        teil.save()
        return teil

    def _geschwister(self) -> models.QuerySet["Katalogteil"]:
        # Alle Teile unter demselben Elternteil, dieser eingeschlossen.

        return type(self).objects.filter(
            **{f"{self._eltern}_id": getattr(self, f"{self._eltern}_id")}
        )

    def _katalog_id(self) -> int | None:
        # Die Fassung, an der der Teil hängt; tiefere Teile fragen ihr Elternteil
        # in der Datenbank, damit auch ein umgehängter Teil die neue Fassung trifft.

        eltern_id: int | None = getattr(self, f"{self._eltern}_id")
        if "__" not in self._katalog_pfad:
            return eltern_id
        eltern: type[models.Model] = self._meta.get_field(self._eltern).related_model
        return (
            eltern.objects.filter(pk=eltern_id)
            .values_list(self._katalog_pfad.split("__", 1)[1], flat=True)
            .first()
        )

    def _nur_am_entwurf(self) -> None:
        # Prüft die Fassung des Teils und beim Umhängen auch die bisherige.

        bisherige: models.QuerySet = (
            type(self)
            .objects.filter(pk=self.pk)
            .values_list(self._katalog_pfad, flat=True)
        )
        _nur_an_entwuerfen({self._katalog_id(), *bisherige})

    def save(self, *args: object, **kwargs: object) -> None:
        """Speichert nur an einem Entwurf."""

        self._nur_am_entwurf()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Löscht nur an einem Entwurf."""

        self._nur_am_entwurf()
        return super().delete(*args, **kwargs)

    @transaction.atomic
    def verschieben(self, schritt: int) -> None:
        """Tauscht den Platz mit dem Nachbarn davor (-1) oder dahinter (+1).

        Am Rand der Liste bleibt alles, wie es ist.
        """

        geschwister: models.QuerySet[Katalogteil] = self._geschwister()
        nachbar: Katalogteil | None = (
            geschwister.filter(position__lt=self.position).last()
            if schritt < 0
            else geschwister.filter(position__gt=self.position).first()
        )
        if nachbar is None:
            return
        eigene: int = self.position
        # Die Zwischenposition 0 hält den eindeutigen Platz während des Tauschs frei.
        self.position = 0
        self.save(update_fields=["position"])
        nachbar.position, self.position = eigene, nachbar.position
        nachbar.save(update_fields=["position"])
        self.save(update_fields=["position"])


class UebergreifendesKriterium(Katalogteil):
    """Eine Rubrik, nach der der Bewerter jedes Evalgespräch aller Evals beurteilt.

    Reiner Text ohne Platzhalter; kern-neutral zu formulieren ist eine
    Pflegeregel, keine Mechanik (ADR-0046).
    """

    _eltern: str = "katalog"
    _katalog_pfad: str = "katalog_id"

    katalog: models.ForeignKey = models.ForeignKey(
        Evalkatalog,
        on_delete=models.CASCADE,
        related_name="uebergreifende_kriterien",
    )
    text: models.TextField = models.TextField("Kriterium", blank=True, default="")

    class Meta(Katalogteil.Meta):
        """Hält die Position je Katalog eindeutig."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["katalog", "position"],
                name="simulation_uebergreifendes_kriterium_position_eindeutig",
            ),
        ]


class Eval(Katalogteil):
    """Ein Prüffall des Katalogs mit eigenen Evalkriterien (ADR-0046)."""

    _eltern: str = "katalog"
    _katalog_pfad: str = "katalog_id"

    katalog: models.ForeignKey = models.ForeignKey(
        Evalkatalog,
        on_delete=models.CASCADE,
        related_name="evals",
    )
    name: models.CharField = models.CharField(
        "Name", max_length=200, blank=True, default=""
    )

    class Meta(Katalogteil.Meta):
        """Hält die Position je Katalog eindeutig."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["katalog", "position"],
                name="simulation_eval_position_eindeutig",
            ),
        ]

    def kriterium_anlegen(self, text: str = "") -> "Evalkriterium":
        """Hängt ein Evalkriterium ans Ende der Liste des Evals."""

        return Evalkriterium.anhaengen(self, text=text)

    @transaction.atomic
    def input_anlegen(self) -> "Evalinput":
        """Hängt einen Evalinput mit drei leeren, festen Inputschritten ans Ende."""

        evalinput: Evalinput = Evalinput.anhaengen(self)
        for _ in range(3):
            evalinput.schritt_anlegen()
        return evalinput


class Evalkriterium(Katalogteil):
    """Eine Rubrik, nach der der Bewerter jedes Evalgespräch seines Evals beurteilt.

    Reiner Text ohne Platzhalter.
    """

    _eltern: str = "eval"
    _katalog_pfad: str = "eval__katalog_id"

    eval: models.ForeignKey = models.ForeignKey(
        Eval,
        on_delete=models.CASCADE,
        related_name="kriterien",
    )
    text: models.TextField = models.TextField("Kriterium", blank=True, default="")

    class Meta(Katalogteil.Meta):
        """Hält die Position je Eval eindeutig."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["eval", "position"],
                name="simulation_evalkriterium_position_eindeutig",
            ),
        ]


class Evalinput(Katalogteil):
    """Wie die simulierte Lehrperson in einem Evalgespräch spricht (ADR-0046).

    Eine geordnete Folge von Inputschritten; ihre Zahl ist die Länge jedes
    Evalgesprächs dieses Evalinputs.
    """

    _eltern: str = "eval"
    _katalog_pfad: str = "eval__katalog_id"

    eval: models.ForeignKey = models.ForeignKey(
        Eval,
        on_delete=models.CASCADE,
        related_name="inputs",
    )

    class Meta(Katalogteil.Meta):
        """Hält die Position je Eval eindeutig."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["eval", "position"],
                name="simulation_evalinput_position_eindeutig",
            ),
        ]

    @property
    def kuerzel(self) -> str:
        """Die Folge der Schritte als F (fest) und G (gelenkt), etwa „FFG“."""

        return "".join(
            "G" if schritt.gelenkt else "F" for schritt in self.schritte.all()
        )

    def schritt_anlegen(self, art: str = "fest", text: str = "") -> "Inputschritt":
        """Hängt einen Inputschritt ans Ende des Drehbuchs."""

        return Inputschritt.anhaengen(self, art=art, text=text)


class Inputschritt(Katalogteil):
    """Ein Schritt eines Evalinputs: wörtlich (fest) oder nach Strategie (gelenkt).

    Bei *fest* ist der Text die Inputäußerung, bei *gelenkt* die
    Inputstrategie. Reiner Text ohne Platzhalter.
    """

    class Art(models.TextChoices):
        """Ob die Lehrperson den Text wörtlich sagt oder danach formuliert."""

        FEST = "fest", "sagt wörtlich"
        GELENKT = "gelenkt", "formuliert nach Strategie"

    _eltern: str = "evalinput"
    _katalog_pfad: str = "evalinput__eval__katalog_id"

    evalinput: models.ForeignKey = models.ForeignKey(
        Evalinput,
        on_delete=models.CASCADE,
        related_name="schritte",
    )
    art: models.CharField = models.CharField(
        "Art", max_length=10, choices=Art.choices, default=Art.FEST
    )
    text: models.TextField = models.TextField("Text", blank=True, default="")

    class Meta(Katalogteil.Meta):
        """Hält die Position je Evalinput eindeutig."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["evalinput", "position"],
                name="simulation_inputschritt_position_eindeutig",
            ),
        ]

    @property
    def gelenkt(self) -> bool:
        """Ob die Lehrperson nach der Inputstrategie selbst formuliert."""

        return self.art == self.Art.GELENKT


class Anbieter(models.TextChoices):
    """Die Anbieter, die eine Naht dieser Anwendung bedienen können."""

    FAKE = "fake", "Fake (ohne Netz)"
    OPENROUTER = "openrouter", "OpenRouter"
    INFOMANIAK = "infomaniak", "Infomaniak"


# Der Anbieter `fake` bedient genau ein Modell, das seinen Namen trägt.
FAKE_MODELLNAME: str = "fake"
MIKRO_STELLSCHRAUBEN: frozenset[str] = frozenset(
    {
        "temperature",
        "top_p",
        "max_tokens",
        "max_completion_tokens",
        "reasoning_effort",
        "thinking",
        "seed",
        "stop",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "verbosity",
    }
)
FAKE_STELLSCHRAUBEN: frozenset[str] = frozenset({"skript"})
# Die Maske verrät die Länge des Tokens nicht: immer acht Punkte.
TOKEN_MASKE: str = "•" * 8
# Erst ab dieser Länge geben vier sichtbare Zeichen nicht das halbe Token preis.
TOKEN_ERKENNBAR_AB: int = 12
TOKEN_SICHTBARE_ZEICHEN: int = 4


@dataclass(frozen=True)
class Anbieterprofil:
    """Was ein Anbieter von seiner Konfiguration verlangt und was er ihr vorgibt."""

    # Das Präfix, mit dem LiteLLM einen Modellnamen zum Anbieter routet.
    praefix: str
    # Ob der Anbieter nur an der Wurzel des eigenen Kontos antwortet.
    braucht_basis_url: bool
    # Die Endpunktwurzel, die ohne eigene Angabe gilt; leer, wenn es keine gibt.
    standard_basis_url: str
    # Die Allowlist der Parameter, die dieser Anbieter kennt.
    stellschrauben: frozenset[str]


ANBIETER_PROFIL: dict[str, Anbieterprofil] = {
    Anbieter.FAKE: Anbieterprofil(
        praefix="",
        braucht_basis_url=False,
        standard_basis_url="",
        stellschrauben=FAKE_STELLSCHRAUBEN,
    ),
    Anbieter.OPENROUTER: Anbieterprofil(
        praefix="openrouter/",
        braucht_basis_url=False,
        standard_basis_url="https://openrouter.ai/api/v1",
        stellschrauben=MIKRO_STELLSCHRAUBEN,
    ),
    Anbieter.INFOMANIAK: Anbieterprofil(
        praefix="openai/",
        braucht_basis_url=True,
        standard_basis_url="",
        stellschrauben=MIKRO_STELLSCHRAUBEN,
    ),
}


class AnbieterFeldgruppe(models.Model):
    """Die Anbieter-Feldgruppe, die beide Konfigurationen gleichermaßen tragen."""

    anbieter: models.CharField = models.CharField(
        max_length=10,
        choices=Anbieter,
        default=Anbieter.FAKE,
    )
    anbieter_basis_url: models.URLField = models.URLField(blank=True, default="")
    anbieter_token: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    class Meta:
        """Keine eigene Tabelle: Beide Konfigurationen tragen die Felder als Singleton."""

        abstract: bool = True

    @property
    def anbieter_token_maskiert(self) -> str:
        """Liefert den einzigen Wert des Tokens, der eine Ansicht erreichen darf."""

        if not self.anbieter_token:
            return ""
        if len(self.anbieter_token) < TOKEN_ERKENNBAR_AB:
            return TOKEN_MASKE
        return TOKEN_MASKE + self.anbieter_token[-TOKEN_SICHTBARE_ZEICHEN:]

    def _zugangsfehler(self) -> dict[str, str]:
        # Prüft Endpunkt und Token gegen das Profil des gewählten Anbieters.

        fehler: dict[str, str] = {}
        if self.anbieter == Anbieter.FAKE:
            if self.anbieter_basis_url:
                fehler["anbieter_basis_url"] = (
                    "Der Anbieter »fake« hat keinen Endpunkt."
                )
            if self.anbieter_token:
                fehler["anbieter_token"] = "Der Anbieter »fake« braucht kein Token."
            return fehler
        if not self.anbieter_token:
            fehler["anbieter_token"] = "Ohne Token bedient der Anbieter keinen Aufruf."
        if (
            ANBIETER_PROFIL[self.anbieter].braucht_basis_url
            and not self.anbieter_basis_url
        ):
            fehler["anbieter_basis_url"] = (
                "Dieser Anbieter antwortet nur an der Wurzel des eigenen Kontos."
            )
        return fehler


class ModellKonfigurationQuerySet(models.QuerySet["ModellKonfiguration"]):
    """QuerySets für unveränderliche Modell-Konfigurationen."""

    def update(self, **kwargs: object) -> int:
        """Verhindert Massenänderungen an Modell-Konfigurationen."""

        raise RuntimeError(_UNVERAENDERLICH_FEHLERMELDUNG)


class Verwendung(models.TextChoices):
    """Wofür eine Modell-Konfiguration aktiv ist; je Verwendung höchstens eine."""

    SCHUELERIN = "schuelerin", "Schüler:in"
    LEHRPERSON = "lehrperson", "Lehrperson"
    BEWERTER = "bewerter", "Bewerter"


class ModellKonfigurationManager(
    models.Manager.from_queryset(ModellKonfigurationQuerySet),
):
    """Zugang zu den aktiven Modell-Konfigurationen je Verwendung.

    Die Verwendung hat bewusst keinen Default: Keine neue Stelle soll
    versehentlich die Schüler:innen-Konfiguration erwischen.
    """

    def aktive(self, verwendung: Verwendung) -> "ModellKonfiguration | None":
        """Liefert die Konfiguration der Verwendung; keine, solange sie unbelegt ist."""

        try:
            return self.belegte(verwendung)
        except AktiveModellKonfiguration.DoesNotExist:
            return None

    def belegte(self, verwendung: Verwendung) -> "ModellKonfiguration":
        """Liefert die Konfiguration der Verwendung und scheitert, wenn sie fehlt.

        Für Aufrufer, die ohne Konfiguration nicht weiterkommen: Eine unbelegte
        Verwendung wirft ``AktiveModellKonfiguration.DoesNotExist``, statt dass
        ein leerer Pin still weiterwandert.
        """

        return (
            AktiveModellKonfiguration.objects.select_related("konfiguration")
            .get(verwendung=verwendung)
            .konfiguration
        )

    def aktive_je_verwendung(self) -> dict[str, int]:
        """Liefert je belegter Verwendung den Primärschlüssel ihrer Konfiguration."""

        return dict(
            AktiveModellKonfiguration.objects.values_list(
                "verwendung", "konfiguration_id"
            )
        )

    def aktivieren(
        self,
        konfiguration: "ModellKonfiguration",
        verwendung: Verwendung,
    ) -> "ModellKonfiguration":
        """Richtet den Zeiger der Verwendung auf die Konfiguration."""

        AktiveModellKonfiguration.objects.update_or_create(
            verwendung=verwendung,
            defaults={"konfiguration": konfiguration},
        )
        return konfiguration


class ModellKonfiguration(AnbieterFeldgruppe):
    """Unveränderliche Konfiguration eines Sprachmodells."""

    # Nicht eindeutig: Sie benennt eine Fassung für Menschen, der Primärschlüssel
    # bleibt die Identität.
    bezeichnung: models.CharField = models.CharField(max_length=120)
    sprachmodell: models.CharField = models.CharField(max_length=255)
    parameter: models.JSONField = models.JSONField(default=dict, blank=True)
    # Für den Bestand vor Einführung des Feldes der Beginn seiner frühesten
    # Sitzung, ohne Sitzung leer: Ein erfundenes Datum wäre schlimmer als keines.
    angelegt_am: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, null=True
    )

    objects: ModellKonfigurationManager = ModellKonfigurationManager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Verhindert jede Mutation und prüft die Konfiguration beim Anlegen."""

        if not self._state.adding:
            raise RuntimeError(_UNVERAENDERLICH_FEHLERMELDUNG)
        # Append-only heißt: Das Anlegen ist die einzige Stelle, an der eine
        # Konfiguration verbindlich wird — also auch aus Shell und Seeds.
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Bindet Modellname, Zugangsdaten und Parameter an den Anbieter."""

        if self.anbieter not in Anbieter.values:
            return  # Den unbekannten Anbieter meldet bereits die Feldprüfung.
        fehler: dict[str, str] = {
            **self._zugangsfehler(),
            **self._modellnamenfehler(),
            **self._parameter_fehler(),
        }
        if fehler:
            raise ValidationError(fehler)

    def _modellnamenfehler(self) -> dict[str, str]:
        # Prüft den Modellnamen gegen das Routing des gewählten Anbieters.

        if self.anbieter == Anbieter.FAKE:
            if self.sprachmodell != FAKE_MODELLNAME:
                return {
                    "sprachmodell": "Der Anbieter »fake« bedient nur das Modell »fake«."
                }
            return {}
        praefix: str = ANBIETER_PROFIL[self.anbieter].praefix
        if not self.sprachmodell.startswith(praefix):
            return {"sprachmodell": f"Dieser Anbieter verlangt das Präfix »{praefix}«."}
        return {}

    def _parameter_fehler(self) -> dict[str, str]:
        # Prüft die Parameter gegen die Allowlist des gewählten Anbieters.

        if not isinstance(self.parameter, dict):
            return {"parameter": "Parameter sind ein Objekt aus Schlüsseln und Werten."}
        erlaubt: frozenset[str] = ANBIETER_PROFIL[self.anbieter].stellschrauben
        ueberzaehlig: list[str] = sorted(set(self.parameter) - erlaubt)
        if ueberzaehlig:
            return {
                "parameter": (
                    f"Bei diesem Anbieter nicht erlaubt: {', '.join(ueberzaehlig)}. "
                    f"Erlaubt sind: {', '.join(sorted(erlaubt))}."
                )
            }
        return {}


class AktiveModellKonfiguration(models.Model):
    """Der veränderliche Zeiger einer Verwendung auf eine Modell-Konfiguration."""

    konfiguration: models.ForeignKey = models.ForeignKey(
        ModellKonfiguration,
        on_delete=models.PROTECT,
    )
    verwendung: models.CharField = models.CharField(
        max_length=10,
        choices=Verwendung,
        unique=True,
    )


class TranskriptionsKonfigurationManager(models.Manager["TranskriptionsKonfiguration"]):
    """Zugang zur einzigen Transkriptions-Konfiguration."""

    def aktuelle(self) -> "TranskriptionsKonfiguration":
        """Liefert die eine Zeile und legt sie beim ersten Zugriff an."""

        konfiguration, _ = self.get_or_create(pk=1)
        return konfiguration


class TranskriptionsKonfiguration(AnbieterFeldgruppe):
    """Der einzige, veränderliche Anbieterzugang der Transkription.

    Anders als die Modell-Konfiguration wird sie nicht gepinnt und nicht
    exportiert (ADR-0026); eine alte Fassung trüge deshalb keine Information.
    """

    id: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        primary_key=True,
        default=1,
        editable=False,
    )
    transkriptionsmodell: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    sprache: models.CharField = models.CharField(max_length=5, default="de")

    objects: TranskriptionsKonfigurationManager = TranskriptionsKonfigurationManager()

    def clean(self) -> None:
        """Bindet Modellname und Zugangsdaten an den gewählten Anbieter."""

        if self.anbieter not in Anbieter.values:
            return  # Den unbekannten Anbieter meldet bereits die Feldprüfung.
        fehler: dict[str, str] = self._zugangsfehler()
        # Der Platzhalter-Adapter braucht kein Modell; jeder echte Anbieter schon.
        if self.anbieter != Anbieter.FAKE and not self.transkriptionsmodell:
            fehler["transkriptionsmodell"] = (
                "Ohne Modellnamen weiß der Anbieter nicht, was er laden soll."
            )
        if fehler:
            raise ValidationError(fehler)

    class Meta:
        """Hält die Transkriptions-Konfiguration als einzige Zeile."""

        constraints: list[models.BaseConstraint] = [
            models.CheckConstraint(
                condition=Q(id=1),
                name="simulation_transkriptions_konfiguration_ist_singleton",
            ),
        ]

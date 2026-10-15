"""Datenmodelle für kuratierte Trainings."""

from typing import TYPE_CHECKING
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import F, Max
from django.db.models.signals import post_delete

from konten.eigentuemerschaft import EigentuemerKreis, EigentuemerKreisQuerySet
from konten.navigation import AUSBILDERIN_GRUPPE, rolle_oder_administration
from sitzungen.bindungen import Bindung, BindungQuerySet
from vignetten.models import vignette_archiviert

if TYPE_CHECKING:
    from konten.models import Konto
    from sitzungen.models import SitzungQuerySet
    from vignetten.models import Vignette


_ZUSTANDSWECHSEL_FEHLERMELDUNG = (
    "Zustandswechsel laufen über die Lebenszyklus-Methoden."
)


class TrainingQuerySet(
    EigentuemerKreisQuerySet["Training"], models.QuerySet["Training"]
):
    """Abfragen über Trainings."""

    def update(self, **kwargs: object) -> int:
        """Hält Zustandswechsel an der Lebenszyklus-Naht."""
        if "zustand" in kwargs:
            raise RuntimeError(_ZUSTANDSWECHSEL_FEHLERMELDUNG)
        return super().update(**kwargs)

    def veroeffentlicht(self) -> models.QuerySet["Training"]:
        """Liefert die für Teilnehmende sichtbaren Trainings."""
        return self.filter(zustand=Training.Zustand.VEROEFFENTLICHT)

    def beigetreten_von(self, konto: "Konto") -> models.QuerySet["Training"]:
        """Liefert die Trainings, an denen das Konto eine aktive Trainingsbindung hat."""
        return self.filter(
            trainingsbindung__konto=konto,
            trainingsbindung__zustand=Trainingsbindung.Zustand.AKTIV,
        )

    def zugaenglich_fuer(self, konto: "Konto") -> models.QuerySet["Training"]:
        """Liefert die Trainings, die das Konto betreten darf (ADR-0049).

        Teilnehmende erreichen ein Training nur über ihre aktive
        Trainingsbindung; Kreis und Administration erreichen es über `kreiszugang_fuer`.
        """
        return self.filter(
            models.Q(
                pk__in=Trainingsbindung.objects.aktiv()
                .filter(konto=konto)
                .values("training")
            )
            | models.Q(pk__in=Training.objects.kreiszugang_fuer(konto).values("pk"))
        )

    def kreiszugang_fuer(self, konto: "Konto") -> models.QuerySet["Training"]:
        """Liefert die Trainings, die der Kreis des Kontos öffnet (ADR-0037).

        Der Kreis öffnet nur mit der Rolle Ausbilder:in oder der Administration;
        nach einem Rollenentzug bleibt die Eigentümerschaft, die Tür nicht.
        """
        if not rolle_oder_administration(AUSBILDERIN_GRUPPE)(konto):
            return self.none()
        return self.sichtbar_fuer(konto)

    def fremd_einsehbare_sitzungen(self) -> "SitzungQuerySet":
        """Liefert die Sitzungen, die der Kreis dieser Trainings lesen darf (ADR-0049)."""
        from sitzungen.models import Sitzung

        return Sitzung.objects.fremd_einsehbar(
            self,
            Abschrift.wirksame_freigaben()
            .filter(training__in=self)
            .values("abschrift__teilnahme"),
        )


class Training(EigentuemerKreis):
    """Ein von einem Eigentümerinnen-Kreis kuratierter Satz finaler Vignetten."""

    ROLLENGRUPPE: str = AUSBILDERIN_GRUPPE
    LOESCHSPERRE_MELDUNG: str = (
        "Trainings brauchen mindestens eine Eigentümerin; bitte tragen Sie "
        "vorher eine Nachfolgerin ein."
    )

    class Zustand(models.TextChoices):
        """Die Zustände eines Trainings."""

        ENTWURF = "entwurf", "Entwurf"
        VEROEFFENTLICHT = "veröffentlicht", "Veröffentlicht"

    name: models.CharField = models.CharField(max_length=255)
    zustand: models.CharField = models.CharField(
        max_length=14,
        choices=Zustand,
        default=Zustand.ENTWURF,
    )
    vignetten: models.ManyToManyField = models.ManyToManyField(
        "vignetten.Vignette", through="Trainingsvignette"
    )
    trainings_link: models.UUIDField = models.UUIDField(
        default=uuid4,
        unique=True,
        editable=False,
    )
    beitritt_gesperrt: models.BooleanField = models.BooleanField(default=False)

    objects: models.Manager["Training"] = TrainingQuerySet.as_manager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Verhindert direkte Zustandswechsel."""
        if self._state.adding and self.zustand != self.Zustand.ENTWURF:
            raise ValidationError(_ZUSTANDSWECHSEL_FEHLERMELDUNG)
        if not self._state.adding:
            gespeichertes_training: Training = type(self).objects.get(pk=self.pk)
            if self.zustand != gespeichertes_training.zustand and not getattr(
                self, "_wechselt_zustand", False
            ):
                raise ValidationError(_ZUSTANDSWECHSEL_FEHLERMELDUNG)
        super().save(*args, **kwargs)

    @transaction.atomic
    def veroeffentlichen(self) -> None:
        """Veröffentlicht genau einen Entwurf."""
        gespeichertes_training: Training = (
            type(self).objects.select_for_update().get(pk=self.pk)
        )
        if gespeichertes_training.zustand != self.Zustand.ENTWURF:
            raise ValidationError("Nur Entwürfe können veröffentlicht werden.")
        self._wechselt_zustand = True
        try:
            self.zustand = self.Zustand.VEROEFFENTLICHT
            self.save(update_fields=["zustand"])
        finally:
            del self._wechselt_zustand

    def vignetten_in_reihenfolge(self) -> models.QuerySet["Vignette"]:
        """Liefert die Vignetten des Trainings in empfohlener Reihenfolge."""
        from vignetten.models import Vignette

        return Vignette.objects.filter(trainingsvignette__training=self).order_by(
            "trainingsvignette__position"
        )

    @transaction.atomic
    def vignette_aufnehmen(self, vignette: "Vignette") -> None:
        """Hängt eine finale Vignette ans Ende der Reihenfolge an.

        Eine bereits aufgenommene Vignette behält ihre Position.
        """
        zugehoerigkeiten: models.QuerySet[Trainingsvignette] = (
            self.vignettenzugehoerigkeiten.select_for_update()
        )
        if zugehoerigkeiten.filter(vignette=vignette).exists():
            return
        Trainingsvignette.objects.create(
            training=self,
            vignette=vignette,
            position=_hoechste_position(zugehoerigkeiten) + 1,
        )

    @transaction.atomic
    def vignette_entfernen(self, vignette: "Vignette") -> None:
        """Entfernt eine Vignette; die nachfolgenden rücken lückenlos nach."""
        zugehoerigkeiten: models.QuerySet[Trainingsvignette] = (
            self.vignettenzugehoerigkeiten.select_for_update()
        )
        zugehoerigkeiten.filter(vignette=vignette).delete()
        _reihenfolge_schreiben(
            zugehoerigkeiten,
            list(zugehoerigkeiten.order_by("position").values_list("pk", flat=True)),
        )

    @transaction.atomic
    def vignette_verschieben(self, vignette: "Vignette", position: int) -> None:
        """Setzt eine Vignette an eine 1-basierte Position; die übrigen rücken.

        Eine Position außerhalb der Liste setzt an den Anfang bzw. ans Ende.
        Eine inzwischen entfernte Vignette lässt die Reihenfolge unverändert.
        """
        zugehoerigkeiten: models.QuerySet[Trainingsvignette] = (
            self.vignettenzugehoerigkeiten.select_for_update()
        )
        verschobene: int | None = (
            zugehoerigkeiten.filter(vignette=vignette)
            .values_list("pk", flat=True)
            .first()
        )
        if verschobene is None:
            return
        ids: list[int] = [
            pk
            for pk in zugehoerigkeiten.order_by("position").values_list("pk", flat=True)
            if pk != verschobene
        ]
        ids.insert(min(max(position - 1, 0), len(ids)), verschobene)
        _reihenfolge_schreiben(zugehoerigkeiten, ids)

    def beitreten(self, konto: "Konto") -> bool:
        """Tritt dem Training über den Trainings-Link bei.

        Liefert, ob das Konto danach dabei ist. Eine ausgetretene Bindung
        lebt wieder auf. Die Sperre hält Neue und Ausgetretene fern; wer
        aktiv dabei ist, bleibt dabei.
        """
        if (
            self.beitritt_gesperrt
            and not self.trainingsbindung_set.aktiv().filter(konto=konto).exists()
        ):
            return False
        self.bindung_fuer(konto).wieder_beitreten()
        return True

    def bindung_fuer(self, konto: "Konto") -> "Trainingsbindung":
        """Lädt oder legt die eine Trainingsbindung des Kontos an.

        Beitritt und Sitzungsstart teilen sich diesen Weg; ein paralleler
        zweiter Aufruf scheitert an der Eindeutigkeit und lädt die erste.
        Eine ausgetretene Bindung kommt unverändert zurück.
        """
        from sitzungen.models import Teilnahme

        with transaction.atomic():
            bindung: Trainingsbindung | None = (
                Trainingsbindung.objects.filter(training=self, konto=konto)
                .select_related("teilnahme")
                .first()
            )
            if bindung is not None:
                return bindung
            try:
                with transaction.atomic():
                    return Trainingsbindung.objects.create(
                        teilnahme=Teilnahme.objects.create(),
                        training=self,
                        konto=konto,
                    )
            except IntegrityError:
                return Trainingsbindung.objects.select_related("teilnahme").get(
                    training=self, konto=konto
                )


def _hoechste_position(zugehoerigkeiten: models.QuerySet["Trainingsvignette"]) -> int:
    """Liefert die höchste belegte Position eines Trainings, für ein leeres 0."""
    return zugehoerigkeiten.aggregate(Max("position"))["position__max"] or 0


def _reihenfolge_schreiben(
    zugehoerigkeiten: models.QuerySet["Trainingsvignette"], ids: list[int]
) -> None:
    """Vergibt den Trainingsvignetten in der Folge der ids die Positionen 1..n."""
    # Erst hinter die höchste Position rücken, damit kein Zwischenstand
    # die eindeutigen Positionen kreuzt.
    zugehoerigkeiten.update(
        position=F("position") + _hoechste_position(zugehoerigkeiten)
    )
    for position, zugehoerigkeit_id in enumerate(ids, start=1):
        zugehoerigkeiten.filter(pk=zugehoerigkeit_id).update(position=position)


class Trainingsvignette(models.Model):
    """Eine finale Vignette eines Trainings an ihrer empfohlenen Position.

    Anders als die Erhebungsvignette friert sie nicht ein: Ein Training lässt
    sich auch nach dem Veröffentlichen umstellen.
    """

    training: models.ForeignKey = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="vignettenzugehoerigkeiten",
    )
    vignette: models.ForeignKey = models.ForeignKey(
        "vignetten.Vignette", on_delete=models.CASCADE
    )
    position: models.PositiveIntegerField = models.PositiveIntegerField()

    class Meta:
        """Macht Mitgliedschaft und Position je Training eindeutig."""

        ordering: list[str] = ["position"]
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["training", "vignette"],
                name="training_vignette_ist_je_training_eindeutig",
            ),
            models.UniqueConstraint(
                fields=["training", "position"],
                name="training_vignettenposition_ist_eindeutig",
            ),
        ]

    def save(self, *args: object, **kwargs: object) -> None:
        """Bindet nur finale Vignetten ein."""
        from vignetten.models import Vignette

        if self.vignette.zustand != Vignette.Zustand.FINAL:
            raise ValidationError("Trainings können nur finale Vignetten einbinden.")
        super().save(*args, **kwargs)


class TrainingsbindungQuerySet(BindungQuerySet):
    """Abfragen über Trainingsbindungen."""

    def aktiv(self) -> models.QuerySet["Trainingsbindung"]:
        """Liefert die Bindungen, die Teilnahme am Training bedeuten."""
        return self.filter(zustand=Trainingsbindung.Zustand.AKTIV)

    def ausgetreten(self) -> models.QuerySet["Trainingsbindung"]:
        """Liefert die Bindungen, deren Konto aus dem Training ausgetreten ist."""
        return self.filter(zustand=Trainingsbindung.Zustand.AUSGETRETEN)


class Trainingsbindung(Bindung):
    """Verbindet eine Teilnahme mit Training und Nutzerkonto.

    Ein Austritt löscht die Bindung nicht, sondern setzt ihren Zustand; wer ihn
    ausgelöst hat, hält sie nicht fest (ADR-0049).
    """

    KONTO_TRAGEND: bool = True

    class Zustand(models.TextChoices):
        """Die Zustände einer Trainingsbindung."""

        AKTIV = "aktiv", "Aktiv"
        AUSGETRETEN = "ausgetreten", "Ausgetreten"

    teilnahme: models.OneToOneField = models.OneToOneField(
        "sitzungen.Teilnahme", on_delete=models.CASCADE
    )
    training: models.ForeignKey = models.ForeignKey(Training, on_delete=models.PROTECT)
    konto: models.ForeignKey = models.ForeignKey(
        "konten.Konto", on_delete=models.PROTECT
    )
    zustand: models.CharField = models.CharField(
        max_length=11, choices=Zustand, default=Zustand.AKTIV
    )

    objects: models.Manager["Trainingsbindung"] = TrainingsbindungQuerySet.as_manager()

    class Meta:
        """Erlaubt je Training und Konto höchstens eine Bindung."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["training", "konto"],
                name="training_bindung_ist_je_konto_eindeutig",
            )
        ]

    @property
    def ist_aktiv(self) -> bool:
        """Sagt, ob das Konto noch Trainingsteilnehmer:in ist."""
        return self.zustand == self.Zustand.AKTIV

    def austreten(self) -> None:
        """Beendet die Teilnahme am Training; ein zweiter Austritt ändert nichts.

        Teilnahme und Sitzungen bleiben bestehen.
        """
        self.zustand = self.Zustand.AUSGETRETEN
        self.save(update_fields=["zustand"])

    def wieder_beitreten(self) -> None:
        """Belebt eine ausgetretene Bindung wieder; eine aktive bleibt, wie sie ist.

        Nur der Beitritt über den Trainings-Link ruft diesen Weg (ADR-0049).
        """
        if not self.ist_aktiv:
            self.zustand = self.Zustand.AKTIV
            self.save(update_fields=["zustand"])


class Abschrift(Bindung):
    """Die konto-gebundene Kopie einer abgeschlossenen Erhebungsteilnahme.

    Sie hält den Namen der Erhebung als Text: Ein Fremdschlüssel dorthin wäre
    der Rückzeiger, den die Abschrift gerade nicht haben darf.
    """

    KONTO_TRAGEND: bool = True

    teilnahme: models.OneToOneField = models.OneToOneField(
        "sitzungen.Teilnahme", on_delete=models.CASCADE
    )
    konto: models.ForeignKey = models.ForeignKey(
        "konten.Konto", on_delete=models.CASCADE
    )
    erhebungsname: models.CharField = models.CharField(max_length=255)
    importiert_am: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    freigegeben_fuer: models.ManyToManyField = models.ManyToManyField(
        Training, related_name="freigegebene_abschriften", blank=True
    )

    @staticmethod
    def wirksame_freigaben() -> models.QuerySet:
        """Die Freigaben, deren Konto genau diesem Training aktiv angehört.

        Die einzige Stelle der Regel aus ADR-0049; jede andere Freigabe ruht.
        Geliefert werden Zeilen der Zwischentabelle mit `abschrift` und `training`.
        """
        return Abschrift.freigegeben_fuer.through.objects.filter(
            training__trainingsbindung__konto=models.F("abschrift__konto"),
            training__trainingsbindung__zustand=Trainingsbindung.Zustand.AKTIV,
        )


def _archivierte_vignette_aus_trainings_entfernen(
    sender: type[models.Model],
    instance: models.Model,
    **kwargs: object,
) -> None:
    """Entfernt eine gerade archivierte Vignette aus allen Trainings."""
    for training in Training.objects.filter(vignetten=instance):
        training.vignette_entfernen(instance)


vignette_archiviert.connect(
    _archivierte_vignette_aus_trainings_entfernen,
    dispatch_uid="training.archivierte_vignette_aus_trainings_entfernen",
)


def _teilnahme_der_abschrift_mitnehmen(
    sender: type[models.Model],
    instance: models.Model,
    **kwargs: object,
) -> None:
    """Nimmt beim Entfernen einer Abschrift ihre Teilnahme und alle Kopien mit.

    Das Signal und nicht das Kommando ist der Ort dafür: Die Abschrift hängt mit
    `CASCADE` am Konto, ihre Zeile verschwindet also auch auf Wegen, die
    `abschrift_loeschen` nie durchlaufen. Ohne diesen Empfänger blieben dabei
    Teilnahme, Sitzungen, Transkripte und Diagnosen verwaist stehen.
    """

    from .abschriften import teilnahme_einer_abschrift_raeumen

    teilnahme_einer_abschrift_raeumen(instance.teilnahme)


post_delete.connect(
    _teilnahme_der_abschrift_mitnehmen,
    sender=Abschrift,
    dispatch_uid="training.teilnahme_der_abschrift_mitnehmen",
)

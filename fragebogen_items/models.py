"""Datenmodelle für Fragebogen-Items und ihre Historien."""

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

if TYPE_CHECKING:
    from konten.models import Konto


class LikertSkalenpol(models.TextChoices):
    """Die global festgelegten sechs Pole der Likert-Skala."""

    STIMME_VOLL_ZU = "Stimme voll zu", "Stimme voll zu"
    STIMME_ZU = "Stimme zu", "Stimme zu"
    STIMME_EHER_ZU = "Stimme eher zu", "Stimme eher zu"
    STIMME_EHER_NICHT_ZU = "Stimme eher nicht zu", "Stimme eher nicht zu"
    STIMME_NICHT_ZU = "Stimme nicht zu", "Stimme nicht zu"
    STIMME_GAR_NICHT_ZU = "Stimme gar nicht zu", "Stimme gar nicht zu"


class FragebogenItemHistorieQuerySet(models.QuerySet["FragebogenItemHistorie"]):
    """Abfragen über Fragebogen-Item-Historien."""

    def sichtbar_fuer(
        self, konto: "Konto"
    ) -> models.QuerySet["FragebogenItemHistorie"]:
        """Liefert die Historien aus dem Eigentümer-Kreis eines Kontos."""
        return self.filter(eigentuemerinnen=konto)


class FragebogenItemHistorie(models.Model):
    """Die gemeinsame, eigentümerinnengetragene Linie eines Items."""

    name: models.CharField = models.CharField(max_length=255, blank=True, default="")
    eigentuemerinnen: models.ManyToManyField = models.ManyToManyField("konten.Konto")

    objects: models.Manager["FragebogenItemHistorie"] = (
        FragebogenItemHistorieQuerySet.as_manager()
    )


class FragebogenItemQuerySet(models.QuerySet["FragebogenItem"]):
    """Abfragen über Fragebogen-Item-Fassungen."""

    def bulk_create(
        self, objs: list["FragebogenItem"], **kwargs: object
    ) -> list["FragebogenItem"]:
        """Verhindert das Umgehen der Anlege-Naht per Masseneinfügen."""
        raise RuntimeError("Fragebogen-Items werden über die Anlege-Naht erzeugt.")

    def bulk_update(
        self, objs: list["FragebogenItem"], fields: list[str], **kwargs: object
    ) -> int:
        """Verhindert das Umgehen der Lebenszyklus-Methoden per Massenupdate."""
        raise RuntimeError(
            "Fragebogen-Items dürfen nicht per Massenupdate geändert werden."
        )

    def update(self, **kwargs: object) -> int:
        """Verhindert das Umgehen der Unveränderlichkeit per Massenupdate."""
        raise RuntimeError(
            "Fragebogen-Items dürfen nicht per Massenupdate geändert werden."
        )

    def delete(self) -> tuple[int, dict[str, int]]:
        """Löscht gesammelt ausschließlich Entwürfe."""
        if self.exclude(zustand=FragebogenItem.Zustand.ENTWURF).exists():
            raise ValidationError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete()

    def einbindbar(self) -> models.QuerySet["FragebogenItem"]:
        """Liefert die finalen Fassungen, die eingebunden werden dürfen."""
        return self.filter(zustand=FragebogenItem.Zustand.FINAL)


class FragebogenItemManager(models.Manager.from_queryset(FragebogenItemQuerySet)):
    """Manager für neue Fragebogen-Item-Linien."""

    def create(self, **kwargs: object) -> "FragebogenItem":
        """Verhindert das Umgehen der Anlege-Naht."""
        raise RuntimeError("Fragebogen-Items werden über die Anlege-Naht erzeugt.")

    def _erstellen(self, **werte: object) -> "FragebogenItem":
        # Speichert eine Fassung, die eine Lebenszyklus-Methode erzeugt.
        item: FragebogenItem = self.model(**werte)
        item._wird_angelegt = True
        item.save(using=self.db)
        return item

    @transaction.atomic
    def anlegen(
        self,
        konto: "Konto",
        *,
        typ: str = "freitext",
        wortlaut: str = "",
    ) -> "FragebogenItem":
        """Legt einen Entwurf mit Historie für die anlegende Person an."""
        historie: FragebogenItemHistorie = FragebogenItemHistorie.objects.create()
        historie.eigentuemerinnen.add(konto)
        return self._erstellen(historie=historie, typ=typ, wortlaut=wortlaut)


class FragebogenItem(models.Model):
    """Eine versionierte Fassung einer einzelnen Frage an Teilnehmende."""

    _wird_angelegt: bool

    class Zustand(models.TextChoices):
        """Mögliche Zustände einer Fragebogen-Item-Fassung."""

        ENTWURF = "entwurf", "Entwurf"
        FINAL = "final", "Final"
        ARCHIVIERT = "archiviert", "Archiviert"

    class Typ(models.TextChoices):
        """Die zurzeit methodisch zugelassenen Frageformen."""

        FREITEXT = "freitext", "Freitext"
        LIKERT = "likert", "Likert-Skala"

    zustand: models.CharField = models.CharField(
        max_length=11, choices=Zustand, default=Zustand.ENTWURF
    )
    finalisiert_am: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    historie: models.ForeignKey = models.ForeignKey(
        FragebogenItemHistorie, on_delete=models.PROTECT
    )
    vorgaengerin: models.ForeignKey = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT
    )
    typ: models.CharField = models.CharField(
        max_length=9, choices=Typ, default=Typ.FREITEXT
    )
    wortlaut: models.TextField = models.TextField(blank=True)

    objects: FragebogenItemManager = FragebogenItemManager()

    def save(self, *args: object, **kwargs: object) -> None:
        """Speichert nur Entwürfe oder kontrollierte Zustandsübergänge.

        Beispiel: ``item.finalisieren()`` friert einen Entwurf ein; ein
        anschließendes ``item.save()`` kann dessen Inhalt nicht mehr ändern.
        """
        if self._state.adding:
            if not getattr(self, "_wird_angelegt", False):
                raise RuntimeError("Fragebogen-Items werden über die Anlege-Naht erzeugt.")
        else:
            gespeicherte_fassung: FragebogenItem = type(self).objects.get(pk=self.pk)
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

    def _hat_gespeicherten_zustand(self, zustand: str) -> bool:
        # Prüft den Zustand der aktuell gespeicherten Fassung.
        return type(self).objects.filter(pk=self.pk, zustand=zustand).exists()

    def _zustand_wechseln(self, zustand: str, update_fields: list[str]) -> None:
        # Speichert einen ausschließlich intern ausgelösten Zustandsübergang.
        self._wechselt_zustand = True
        try:
            self.zustand = zustand
            self.save(update_fields=update_fields)
        finally:
            del self._wechselt_zustand

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Erlaubt das physische Löschen ausschließlich für Entwürfe."""
        if not self._hat_gespeicherten_zustand(self.Zustand.ENTWURF):
            raise ValidationError("Nur Entwürfe dürfen physisch gelöscht werden.")
        return super().delete(*args, **kwargs)

    @transaction.atomic
    def bearbeiten(self) -> "FragebogenItem":
        """Erzeugt aus einer finalen Fassung einen Entwurf derselben Historie."""
        quelle: FragebogenItem = type(self).objects.select_for_update().get(pk=self.pk)
        if quelle.zustand != self.Zustand.FINAL:
            raise ValidationError("Nur finale Fassungen können bearbeitet werden.")
        return type(self).objects._erstellen(
            historie=quelle.historie,
            vorgaengerin=quelle,
            typ=quelle.typ,
            wortlaut=quelle.wortlaut,
        )

    @transaction.atomic
    def finalisieren(self) -> None:
        """Friert einen Entwurf als finale Fassung ein."""
        if self.zustand != self.Zustand.ENTWURF:
            raise ValidationError("Nur Entwürfe können finalisiert werden.")
        if not self.wortlaut:
            raise ValidationError("Zum Finalisieren fehlt der Wortlaut.")
        self.finalisiert_am = timezone.now()
        self._zustand_wechseln(self.Zustand.FINAL, ["zustand", "finalisiert_am"])

    @transaction.atomic
    def archivieren(self) -> None:
        """Archiviert eine finale Fassung."""
        if not self._hat_gespeicherten_zustand(self.Zustand.FINAL):
            raise ValidationError("Nur finale Fassungen können archiviert werden.")
        self._zustand_wechseln(self.Zustand.ARCHIVIERT, ["zustand"])

    def kann_entarchiviert_werden(self) -> bool:
        """Prüft, ob keine aktive Schwester dieselbe Vorgängerin belegt."""
        return self._hat_gespeicherten_zustand(self.Zustand.ARCHIVIERT) and not (
            self.vorgaengerin_id is not None
            and type(self)
            .objects.filter(vorgaengerin_id=self.vorgaengerin_id)
            .exclude(pk=self.pk)
            .exclude(zustand=self.Zustand.ARCHIVIERT)
            .exists()
        )

    @transaction.atomic
    def entarchivieren(self) -> None:
        """Macht eine archivierte Fassung wieder final."""
        if not self._hat_gespeicherten_zustand(self.Zustand.ARCHIVIERT):
            raise ValidationError("Nur archivierte Fassungen können entarchiviert werden.")
        if not self.kann_entarchiviert_werden():
            raise ValidationError("Die Vorgängerin hat bereits eine aktive Nachfolgerin.")
        self._zustand_wechseln(self.Zustand.FINAL, ["zustand"])

    class Meta:
        """Datenbankinvarianten der Fragebogen-Item-Fassung."""

        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["historie"],
                condition=Q(zustand="entwurf"),
                name="fragebogen_items_ein_entwurf_pro_historie",
            ),
            models.UniqueConstraint(
                fields=["vorgaengerin"],
                condition=~Q(zustand="archiviert"),
                name="fragebogen_items_keine_nichtarchivierten_schwestern",
            ),
            models.CheckConstraint(
                condition=(
                    Q(zustand="entwurf", finalisiert_am__isnull=True)
                    | (~Q(zustand="entwurf") & Q(finalisiert_am__isnull=False))
                ),
                name="fragebogen_items_finalisiert_am_passt_zu_zustand",
            ),
        ]

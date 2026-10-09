"""Lebenszyklus versionierter Fassungen: Entwurf, final, überholt (ADR-0035).

Ein Artefakt mit eigener Linie erbt von `VersionierteFassung`, trägt selbst
seine Historie als Fremdschlüssel `historie`, seine Inhaltsfelder, seinen
Vertrag in `clean()` und seine Kopierregel in `_kopierwerte()`. Seine Meta
übernimmt die Invarianten aus `lebenszyklus_constraints()`.
"""

from datetime import datetime
from typing import Any, Self

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

_NUR_ENTWUERFE_LOESCHBAR: str = "Nur Entwürfe dürfen physisch gelöscht werden."


class FassungQuerySet(models.QuerySet[Any]):
    """Öffentliche Abfragen ohne direkte Schreibroute für Fassungen."""

    def update(self, **kwargs: object) -> int:
        """Hält Zustands- und Inhaltsänderungen an den Lebenszyklus-Methoden."""

        raise RuntimeError(self.model._meldung_lebenszyklus())

    def delete(self) -> tuple[int, dict[str, int]]:
        """Löscht gesammelt ausschließlich Entwürfe."""

        if self.exclude(zustand=self.model.Zustand.ENTWURF).exists():
            raise RuntimeError(_NUR_ENTWUERFE_LOESCHBAR)
        return super().delete()

    def bulk_create(self, objs: list[Any], **kwargs: object) -> list[Any]:
        """Verhindert das Umgehen der Anlege-Naht per Masseneinfügen."""

        raise RuntimeError(self.model._meldung_anlege_naht())

    def bulk_update(self, objs: list[Any], fields: list[str], **kwargs: object) -> int:
        """Verhindert das Umgehen der Lebenszyklus-Methoden per Massenupdate."""

        raise RuntimeError(self.model._meldung_lebenszyklus())


class FassungManager(models.Manager.from_queryset(FassungQuerySet)):
    """Schreibnaht für neue Fassungen; das Anlegen ergänzt jedes Artefakt selbst."""

    def create(self, **kwargs: object) -> Any:
        """Verhindert das Umgehen der Anlege-Naht."""

        raise RuntimeError(self.model._meldung_anlege_naht())

    def finale_fassung(self) -> Any:
        """Die eine gültige finale Fassung oder None, solange es keine gibt."""

        return self.filter(zustand=self.model.Zustand.FINAL).first()

    def _erstellen(self, **werte: object) -> Any:
        # Speichert eine Fassung, die eine Lebenszyklus-Methode erzeugt.

        fassung: VersionierteFassung = self.model(**werte)
        fassung._wird_angelegt = True
        fassung.save(using=self.db)
        return fassung


class VersionierteFassung(models.Model):
    """Eine Fassung in einer Linie mit genau einer finalen Fassung."""

    # Benennt das Artefakt in Fehlermeldungen, etwa »Kern« in »Kern-Fassungen«.
    _bezeichnung: str
    _wird_angelegt: bool
    # Die Historie trägt jedes Artefakt als eigenen Fremdschlüssel.
    historie: models.ForeignKey

    class Zustand(models.TextChoices):
        """Mögliche Zustände einer Fassung; archiviert heißt hier überholt."""

        ENTWURF = "entwurf", "Entwurf"
        FINAL = "final", "Final"
        ARCHIVIERT = "archiviert", "Archiviert"

    zustand: models.CharField = models.CharField(
        max_length=11,
        choices=Zustand,
        default=Zustand.ENTWURF,
    )
    finalisiert_am: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
    )
    vorgaengerin: models.ForeignKey = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    objects: FassungManager = FassungManager()

    class Meta:
        """Keine eigene Tabelle: Jedes Artefakt trägt den Lebenszyklus selbst."""

        abstract: bool = True

    @classmethod
    def _meldung_anlege_naht(cls) -> str:
        # Meldet den Versuch, eine Fassung an der Anlege-Naht vorbei zu erzeugen.

        return f"{cls._bezeichnung}-Fassungen werden über die Anlege-Naht erzeugt."

    @classmethod
    def _meldung_lebenszyklus(cls) -> str:
        # Meldet den Versuch, eine Fassung am Lebenszyklus vorbei zu ändern.

        return (
            f"{cls._bezeichnung}-Fassungen ändern sich nur über Lebenszyklus-Methoden."
        )

    def _kopierwerte(self) -> dict[str, object]:
        # Liefert die Inhaltsfelder, die ein neuer Entwurf übernimmt.

        raise NotImplementedError

    def save(self, *args: object, **kwargs: object) -> None:
        """Verhindert Änderungen außerhalb der Lebenszyklus-Methoden."""

        if self._state.adding:
            if not getattr(self, "_wird_angelegt", False):
                raise RuntimeError(self._meldung_anlege_naht())
        else:
            vorherige_fassung: VersionierteFassung = type(self).objects.get(pk=self.pk)
            if vorherige_fassung.zustand != self.Zustand.ENTWURF:
                raise RuntimeError(
                    f"Finale {self._bezeichnung}-Fassungen sind unveränderlich."
                )
            if (
                self.zustand != vorherige_fassung.zustand
                or self.finalisiert_am != vorherige_fassung.finalisiert_am
            ):
                raise RuntimeError(
                    "Zustandswechsel laufen über die Lebenszyklus-Methoden."
                )
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Erlaubt das physische Löschen ausschließlich für Entwürfe."""

        if not self._ist_gespeichert_als(self.Zustand.ENTWURF):
            raise RuntimeError(_NUR_ENTWUERFE_LOESCHBAR)
        return super().delete(*args, **kwargs)

    def _ist_gespeichert_als(self, zustand: str) -> bool:
        # Prüft den Zustand in der Datenbank statt den im Objekt gehaltenen.

        return type(self).objects.filter(pk=self.pk, zustand=zustand).exists()

    def _schreibqueryset(self) -> models.QuerySet[Self]:
        # Liefert die interne Schreibroute der Lebenszyklus-Methoden.

        return models.QuerySet(model=type(self), using=self._state.db)

    @transaction.atomic
    def bearbeiten(self) -> Self:
        """Erzeugt aus einer finalen Fassung einen neuen Entwurf."""

        if not self._ist_gespeichert_als(self.Zustand.FINAL):
            raise ValueError(
                f"Die {self._bezeichnung}-Fassung wurde inzwischen geändert."
            )
        if (
            type(self)
            .objects.filter(
                historie=self.historie,
                zustand=self.Zustand.ENTWURF,
            )
            .exists()
        ):
            raise ValueError(f"Ein {self._bezeichnung}-Entwurf existiert bereits.")
        return type(self).objects._erstellen(
            historie=self.historie,
            vorgaengerin=self,
            **self._kopierwerte(),
        )

    @transaction.atomic
    def finalisieren(self) -> None:
        """Finalisiert einen vertragskonformen Entwurf und überholt die Vorgängerin."""

        if self.zustand != self.Zustand.ENTWURF:
            raise ValueError("Nur Entwürfe können finalisiert werden.")
        self.full_clean()
        self.save()
        finalisiert_am: datetime = timezone.now()
        # Die bisherige finale Fassung weicht vor dem eigenen Zustandswechsel:
        # Der partielle Unique-Index duldet zwei finale Fassungen keine
        # Anweisung lang nebeneinander. Bei der ersten Fassung der Historie
        # trifft das Archivieren keine Zeile.
        self._schreibqueryset().filter(
            historie=self.historie,
            zustand=self.Zustand.FINAL,
        ).update(zustand=self.Zustand.ARCHIVIERT)
        if (
            not self._schreibqueryset()
            .filter(
                pk=self.pk,
                zustand=self.Zustand.ENTWURF,
            )
            .update(
                zustand=self.Zustand.FINAL,
                finalisiert_am=finalisiert_am,
            )
        ):
            raise ValueError(
                f"Der {self._bezeichnung}-Entwurf wurde inzwischen geändert."
            )
        self.zustand = self.Zustand.FINAL
        self.finalisiert_am = finalisiert_am


def lebenszyklus_constraints(praefix: str) -> list[models.BaseConstraint]:
    """Liefert die Invarianten einer Linie; `praefix` hält die Namen eindeutig.

    Beispiel: ``lebenszyklus_constraints("simulation")`` ergibt unter anderem
    ``simulation_eine_finale_fassung_pro_historie``.
    """

    return [
        models.UniqueConstraint(
            fields=["historie"],
            condition=Q(zustand="entwurf"),
            name=f"{praefix}_ein_entwurf_pro_historie",
        ),
        models.UniqueConstraint(
            fields=["historie"],
            condition=Q(zustand="final"),
            name=f"{praefix}_eine_finale_fassung_pro_historie",
        ),
        models.UniqueConstraint(
            fields=["vorgaengerin"],
            condition=~Q(zustand="archiviert"),
            name=f"{praefix}_keine_nichtarchivierten_schwestern",
        ),
        models.CheckConstraint(
            condition=(
                Q(zustand="entwurf", finalisiert_am__isnull=True)
                | (~Q(zustand="entwurf") & Q(finalisiert_am__isnull=False))
            ),
            name=f"{praefix}_finalisiert_am_passt_zu_zustand",
        ),
    ]

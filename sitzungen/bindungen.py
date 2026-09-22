"""Die Exklusivität der Bindungsarten einer Teilnahme.

Trainingsbindung und Abschrift tragen ein Nutzerkonto, die Erhebungsbindung ein
Teilnahme-Token. Beide Arten zeigen mit einer 1:1-Beziehung auf eine Teilnahme —
zeigten sie auf dieselbe, wäre Konto ↔ Token ein Join über zwei Kanten. ADR-0018
nennt diese Verknüpfung nicht ausdrückbar; ausdrückbar ist sie sehr wohl, nur
schreibt sie niemand. Hier wird sie abgewiesen: beim Anlegen, beim Ändern und
beim Schreiben in Mengen.

Die Prüfung steht bei der Teilnahme und nicht in einer der beiden Apps, weil
`erhebungen` nach ADR-0006 nichts von Konten und damit nichts von `training`
wissen darf. Die Bindungen finden einander über ihre gemeinsame Basis, ohne
dass eine die andere importiert.
"""

from collections.abc import Iterator, Sequence

from django.core.exceptions import ValidationError
from django.db import models


UNVERTRAEGLICHE_BINDUNG: str = (
    "Diese Teilnahme trägt bereits eine Bindung der anderen Art; Nutzerkonto "
    "und Teilnahme-Token bleiben getrennt."
)

UMHAENGEN_FEHLERMELDUNG: str = (
    "Die Teilnahme einer Bindung wechselt nicht über ein Mengen-Update; die "
    "Trennung wird an der einzelnen Bindung geprüft."
)


class BindungQuerySet(models.QuerySet):
    """Hält die Mengen-Schreibwege an dieselbe Prüfung wie `save()`."""

    def update(self, **kwargs: object) -> int:
        """Weist das Umhängen einer Teilnahme am Queryset vorbei ab."""
        if "teilnahme" in kwargs or "teilnahme_id" in kwargs:
            raise RuntimeError(UMHAENGEN_FEHLERMELDUNG)
        return super().update(**kwargs)

    def bulk_create(
        self, objs: Sequence["Bindung"], *args: object, **kwargs: object
    ) -> list["Bindung"]:
        """Prüft jede Bindung einzeln, bevor die Menge geschrieben wird."""
        objs = list(objs)
        for bindung in objs:
            bindung._pruefe_bindungsart()
        return super().bulk_create(objs, *args, **kwargs)


class Bindung(models.Model):
    """Basis jeder Bindung, die eine Teilnahme an ihren Kontext hängt.

    Eine Unterklasse hält ihre Teilnahme im 1:1-Feld `teilnahme` und sagt mit
    `KONTO_TRAGEND`, auf welcher Seite der Trennung sie steht.
    """

    KONTO_TRAGEND: bool
    """Sagt, ob diese Bindung ein Nutzerkonto hält — sonst hält sie ein Token."""

    objects: models.Manager["Bindung"] = BindungQuerySet.as_manager()

    class Meta:
        abstract: bool = True

    def save(self, *args: object, **kwargs: object) -> None:
        """Weist eine Bindung ab, die die Trennung aufhöbe.

        Geprüft wird auch beim Ändern: Eine bestehende Bindung auf eine fremde
        Teilnahme umzuhängen schriebe denselben verbotenen Join wie das Anlegen.
        """
        self._pruefe_bindungsart()
        super().save(*args, **kwargs)

    def _pruefe_bindungsart(self) -> None:
        # Fragt je fremder Bindungsart eine Zeile ab, nicht je Bindung: Die
        # Teilnahme kennt ihre Bindungen nur über deren Rückbeziehungen. Die
        # eigene Art steht nie in der Abfrage, die Zeile weist sich also auch
        # beim wiederholten Speichern nicht selbst ab.

        for fremde_art in self._fremde_bindungsarten():
            if fremde_art.objects.filter(teilnahme_id=self.teilnahme_id).exists():
                raise ValidationError(UNVERTRAEGLICHE_BINDUNG)

    @classmethod
    def _fremde_bindungsarten(cls) -> Iterator[type["Bindung"]]:
        # Liefert die Bindungen, die dieselbe Teilnahme auf der anderen Seite
        # der Trennung binden — gefunden über die Rückbeziehungen der Teilnahme.

        teilnahme: type[models.Model] = cls._meta.get_field("teilnahme").related_model
        for beziehung in teilnahme._meta.related_objects:
            andere: type[models.Model] = beziehung.related_model
            if (
                issubclass(andere, Bindung)
                and andere.KONTO_TRAGEND != cls.KONTO_TRAGEND
            ):
                yield andere

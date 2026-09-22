"""Die Exklusivität der Bindungsarten einer Teilnahme.

Trainingsbindung und Abschrift tragen ein Nutzerkonto, die Erhebungsbindung ein
Teilnahme-Token. Beide Arten zeigen mit einer 1:1-Beziehung auf eine Teilnahme —
zeigten sie auf dieselbe, wäre Konto ↔ Token ein Join über zwei Kanten. ADR-0018
nennt diese Verknüpfung nicht ausdrückbar; ausdrückbar ist sie sehr wohl, nur
schreibt sie niemand. Hier wird sie abgewiesen.

Die Prüfung steht bei der Teilnahme und nicht in einer der beiden Apps, weil
`erhebungen` nach ADR-0006 nichts von Konten und damit nichts von `training`
wissen darf. Die Bindungen finden einander über ihre gemeinsame Basis, ohne
dass eine die andere importiert.
"""

from collections.abc import Iterator

from django.core.exceptions import ValidationError
from django.db import models


UNVERTRAEGLICHE_BINDUNG: str = (
    "Diese Teilnahme trägt bereits eine Bindung der anderen Art; Nutzerkonto "
    "und Teilnahme-Token bleiben getrennt."
)


class Bindung(models.Model):
    """Basis jeder Bindung, die eine Teilnahme an ihren Kontext hängt.

    Eine Unterklasse hält ihre Teilnahme im 1:1-Feld `teilnahme` und sagt mit
    `KONTO_TRAGEND`, auf welcher Seite der Trennung sie steht.
    """

    KONTO_TRAGEND: bool
    """Sagt, ob diese Bindung ein Nutzerkonto hält — sonst hält sie ein Token."""

    class Meta:
        abstract: bool = True

    def save(self, *args: object, **kwargs: object) -> None:
        """Weist eine Bindung ab, die die Trennung aufhöbe."""
        if self._state.adding:
            self._pruefe_bindungsart()
        super().save(*args, **kwargs)

    def _pruefe_bindungsart(self) -> None:
        # Fragt je fremder Bindungsart eine Zeile ab, nicht je Bindung: Die
        # Teilnahme kennt ihre Bindungen nur über deren Rückbeziehungen.

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

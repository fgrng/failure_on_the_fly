"""Der Eigentümer-Kreis, den alle bestandstragenden Modelle gemeinsam tragen."""

from typing import TYPE_CHECKING, Self

from django.db import models

from konten.navigation import ist_administratorin

if TYPE_CHECKING:
    from konten.models import Konto


class EigentuemerKreisQuerySet:
    """Die Sichtbarkeitsregel des Eigentümer-Kreises für jedes Bestands-QuerySet."""

    def sichtbar_fuer(self, konto: "Konto") -> Self:
        """Liefert eigene Bestände oder alle für die Administration."""
        if ist_administratorin(konto):
            return self
        return self.filter(eigentuemerinnen=konto)


class EigentuemerKreis(models.Model):
    """Der Kreis gleichrangiger Eigentümerinnen eines Bestands (ADR-0032).

    Die Basis trägt den Eigentümer-Kreis und nichts sonst. Sie spannt quer zur
    Lebenszyklus-Achse: Zwei ihrer Erbinnen sind Historien ohne eigenen
    Lebenszyklus, zwei sind Objekte, die einen tragen. Deshalb darf aus ihr
    niemals eine Lebenszyklus-Basis erwachsen (ADR-0017).
    """

    # Welche Rolle in diesen Kreis eintragbar ist. Eine Aufnahmeregel an der
    # Tür, kein Systemzustand: Ein Rollenentzug lässt eine bestehende
    # Eigentümerschaft unberührt, sonst verwaisten Bestände.
    ROLLENGRUPPE: str

    eigentuemerinnen: models.ManyToManyField = models.ManyToManyField("konten.Konto")

    class Meta:
        abstract: bool = True

    def ist_aktiv(self) -> bool:
        """Sagt, ob der Bestand noch in Gebrauch ist.

        Wer keine Stilllegung kennt, erbt dieses Ja.
        """
        return True

    @property
    def hat_mehrere_eigentuemerinnen(self) -> bool:
        """Sagt, ob der Kreis mehr als eine Eigentümerin trägt."""
        return self.eigentuemerinnen.count() > 1

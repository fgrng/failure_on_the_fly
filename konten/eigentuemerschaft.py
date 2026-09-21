"""Der Eigentümer-Kreis, den alle bestandstragenden Modelle gemeinsam tragen."""

from typing import TYPE_CHECKING, Self

from django.apps import apps
from django.db import models, transaction

from konten.navigation import ist_administratorin

if TYPE_CHECKING:
    from konten.models import Konto


class EigentuemerKreisQuerySet[Bestand: "EigentuemerKreis"]:
    """Sichtbarkeit und Anlegen des Eigentümer-Kreises für jedes Bestands-QuerySet."""

    def anlegen(self, konto: "Konto", **kwargs: object) -> Bestand:
        """Legt einen Bestand an und trägt das Konto als erste Eigentümerin ein."""
        bestand: Bestand = self.create(**kwargs)
        bestand.eigentuemerinnen.add(konto)
        return bestand

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

    # Was das Konto-Löschen meldet, wenn dieser Bestand im Weg steht. Jede
    # Erbin schreibt ihren Bestand aus; abgeleitet wird nichts, denn Djangos
    # `verbose_name` ergäbe »fragebogen item historie«.
    LOESCHSPERRE_MELDUNG: str = (
        "Dieser Bestand braucht mindestens eine Eigentümerin; bitte tragen "
        "Sie vorher eine Nachfolgerin ein."
    )

    eigentuemerinnen: models.ManyToManyField = models.ManyToManyField("konten.Konto")

    class Meta:
        abstract: bool = True

    def ist_aktiv(self) -> bool:
        """Sagt, ob der Bestand noch in Gebrauch ist.

        Wer keine Stilllegung kennt, erbt dieses Ja.
        """
        return True

    def austreten(self, konto_pk: int) -> bool:
        """Trägt eine Eigentümerin aus und sagt, ob das geschehen ist.

        Der letzte Platz im Kreis kann nicht geräumt werden, auch nicht bei
        einem archivierten Bestand: Er wäre entarchiviert aktiv und
        eigentümerlos. `ist_aktiv()` fragt allein der Konto-Löschpfad.

        Greift die Invariante, passiert schweigend nichts; der Rückgabewert
        ist das einzige Signal.
        """
        # Serialisiert wird über das `atomic()` selbst: Die Verbindungsoption
        # `transaction_mode: IMMEDIATE` nimmt die Schreibsperre schon beim
        # BEGIN. Ein `select_for_update()` trüge nichts bei, weil Djangos
        # SQLite-Backend die Klausel verwirft (`has_select_for_update`).
        with transaction.atomic():
            if not self.hat_mehrere_eigentuemerinnen:
                return False
            if not self.eigentuemerinnen.filter(pk=konto_pk).exists():
                return False
            self.eigentuemerinnen.remove(konto_pk)
            return True

    def moegliche_ergaenzungen(self) -> "models.QuerySet[Konto]":
        """Liefert die Konten, die in diesen Kreis aufgenommen werden können.

        Das sind die Trägerinnen der Rollengruppe samt Administration, ohne die
        bereits Eingetragenen.
        """
        # Erst hier importiert: `konten.models` holt sich für den Löschpfad die
        # Bestandsmodelle aus diesem Modul, ein Modulimport in die Gegenrichtung
        # schlösse den Kreis.
        from konten.models import Konto

        return Konto.objects.mit_rolle_oder_administration(self.ROLLENGRUPPE).exclude(
            pk__in=self.eigentuemerinnen.values("pk")
        )

    @property
    def hat_mehrere_eigentuemerinnen(self) -> bool:
        """Sagt, ob der Kreis mehr als eine Eigentümerin trägt."""
        return self.eigentuemerinnen.count() > 1


def bestandsmodelle() -> list[type[EigentuemerKreis]]:
    """Liefert jedes registrierte Modell, das einen Eigentümer-Kreis trägt.

    Hergeleitet aus Djangos Modellregistrierung statt aus Importen: So
    importiert `konten` nicht in die Bestands-Apps zurück (ADR-0016), und ein
    künftig hinzukommendes Bestandsmodell ist am Tag seiner Einführung dabei.
    """
    return [
        modell for modell in apps.get_models() if issubclass(modell, EigentuemerKreis)
    ]

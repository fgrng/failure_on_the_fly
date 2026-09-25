"""Der gemeinsame Abschnitt »Eigentümer:innen« als Tabelle (#311).

Stellvertretend über die Vignetten-Detailseite geprüft; welche Seite welches
Artefakt nennt, prüfen die View-Tests der einzelnen Apps.
"""

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from vignetten.models import Vignette, Vignettenhistorie


def _autorin(username: str, **kwargs: object) -> Konto:
    """Legt ein Konto mit der Rolle Autor:in an."""
    konto: Konto = Konto.objects.create_user(username=username, **kwargs)
    konto.groups.add(Group.objects.get(name="Autor:in"))
    return konto


def _vignette_mit_eigentuemerinnen(*konten: Konto) -> Vignette:
    """Legt eine Vignette mit dem angegebenen Eigentümer-Kreis an."""
    historie: Vignettenhistorie = Vignettenhistorie.objects.create()
    historie.eigentuemerinnen.add(*konten)
    return Vignette.objects._erstellen(historie=historie)


class EigentuemerinnenAbschnittTests(TestCase):
    """Kreis als Tabelle, Hinzufügen abgetrennt darunter."""

    def _detail(self, konto: Konto, vignette: Vignette) -> HttpResponse:
        self.client.force_login(konto)
        return self.client.get(reverse("vignetten:detail", args=[vignette.pk]))

    def test_tabelle_nennt_name_und_alle_rollen(self) -> None:
        """Jede Zeile trägt den Namen und alle Rollen des Kontos."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace", is_superuser=True)

        response: HttpResponse = self._detail(
            ada, _vignette_mit_eigentuemerinnen(ada, grace)
        )

        self.assertContains(response, '<th scope="col">Rolle</th>', html=True)
        self.assertContains(response, "<td>grace</td>", html=True)
        self.assertContains(response, "<td>Autor:in, Administrator:in</td>", html=True)

    def test_eigene_zeile_heisst_mich_entfernen_mit_erklaerung(self) -> None:
        """Die eigene Person ist markiert und erfährt, was ihr Austritt bewirkt."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada, grace)

        response: HttpResponse = self._detail(ada, vignette)

        self.assertContains(
            response, 'ada <span class="eigentuemerinnen__sie">(Sie)</span>', html=True
        )
        self.assertContains(
            response,
            reverse("vignetten:eigentuemerin_entfernen", args=[vignette.pk, ada.pk]),
        )
        self.assertContains(response, "Mich entfernen")
        self.assertContains(
            response,
            "Sie verlieren den Zugriff; die Vignette bleibt bei den übrigen "
            "Eigentümer:innen.",
        )
        self.assertContains(response, 'aria-label="grace als Eigentümer:in entfernen"')

    def test_letzte_eigentuemerin_hat_keine_aktion(self) -> None:
        """Die letzte Person im Kreis lässt sich nicht entfernen."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada)

        response: HttpResponse = self._detail(ada, vignette)

        self.assertContains(response, "Letzte Eigentümer:in")
        self.assertContains(response, "Fügen Sie zuerst eine weitere Person hinzu")
        self.assertNotContains(response, "Mich entfernen")
        self.assertNotContains(
            response,
            reverse("vignetten:eigentuemerin_entfernen", args=[vignette.pk, ada.pk]),
        )

    def test_hinzufuegen_steht_unter_eigener_unterueberschrift(self) -> None:
        """Auswahl und Knopf folgen abgetrennt unter »Eigentümer:in hinzufügen«."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace")

        response: HttpResponse = self._detail(ada, _vignette_mit_eigentuemerinnen(ada))

        self.assertContains(response, "<h3>Eigentümer:in hinzufügen</h3>", html=True)
        self.assertContains(
            response, f'<option value="{grace.pk}">grace</option>', html=True
        )
        self.assertContains(
            response,
            '<button class="button" type="submit">Hinzufügen</button>',
            html=True,
        )

    def test_ohne_moegliche_ergaenzungen_steht_ein_satz(self) -> None:
        """Gibt es niemanden mehr, fehlt das leere Auswahlfeld."""
        ada: Konto = _autorin("ada")

        response: HttpResponse = self._detail(ada, _vignette_mit_eigentuemerinnen(ada))

        self.assertNotContains(response, '<select name="konto">')
        self.assertContains(
            response,
            "Alle Konten mit der Rolle Autor:in und alle Administrator:innen "
            "gehören schon zum Kreis.",
        )

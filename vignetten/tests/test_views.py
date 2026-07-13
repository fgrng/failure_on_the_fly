"""HTTP-Tests für den Vignetten-Editor."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from simulation.models import Simulationskern
from vignetten.models import Vignette, Vignettenhistorie


class VignettenlisteTests(TestCase):
    """Die Liste zeigt nur Vignetten aus dem eigenen Eigentümer-Kreis."""

    def test_zeigt_eigene_historie_mit_fallback_label_und_versteckt_fremde(self) -> None:
        """Autor:innen sehen nur ihre Historien, auch ohne vergebenen Namen."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        eigene_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        eigene_historie.eigentuemerinnen.add(ada)
        Vignette.objects.create(
            historie=eigene_historie,
            fach="Mathematik",
            thema="Brüche",
            klassenstufe="5",
        )
        benannte_historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Addition mit Übertrag"
        )
        benannte_historie.eigentuemerinnen.add(ada)
        Vignette.objects.create(historie=benannte_historie)
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Versteckte Vignette"
        )
        fremde_historie.eigentuemerinnen.add(grace)
        Vignette.objects.create(historie=fremde_historie)
        self.client.force_login(ada)

        response = self.client.get(reverse("vignetten:liste"))

        self.assertContains(response, "Mathematik: Brüche (Klasse 5)")
        self.assertContains(response, "Addition mit Übertrag")
        self.assertNotContains(response, "Versteckte Vignette")


class VignetteAnlegenViewTests(TestCase):
    """Das Anlegeformular ist die HTTP-Naht zum Vignetten-Manager."""

    def test_speichert_ueberschriebene_akteure_und_zeigt_gepinnten_kern(self) -> None:
        """Die Oberfläche legt einen Entwurf mit dem automatisch gepinnten Kern an."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        kern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.client.force_login(ada)

        response = self.client.post(
            reverse("vignetten:anlegen"),
            {
                "fehlermuster_beschreibung": "Zählt Stellenwerte einzeln.",
                "lernauftrag": "Addiere 27 und 15.",
                "arbeitsheft_beschreibung": "27 + 15 = 312",
                "arbeitsheft_text": "27 + 15 = 312",
                "schuelerin_name": "Mia",
                "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
                "lehrperson_name": "Weber",
                "lehrperson_geschlecht": Vignette.Geschlecht.MAENNLICH,
                "fach": "Mathematik",
                "thema": "Addition",
                "klassenstufe": "5",
                "referenzdiagnose": "Stellenwerte werden nicht ausgerichtet.",
                "budget_typ": Vignette.BudgetTyp.SCHRITTE,
                "budget_wert": 5,
            },
        )

        vignette: Vignette = Vignette.objects.get()
        self.assertRedirects(response, reverse("vignetten:detail", args=[vignette.pk]))
        self.assertEqual(vignette.schuelerin_name, "Mia")
        self.assertEqual(vignette.lehrperson_geschlecht, Vignette.Geschlecht.MAENNLICH)
        self.assertEqual(vignette.gepinnter_kern, kern)
        self.assertEqual(list(vignette.historie.eigentuemerinnen.all()), [ada])
        detail_response = self.client.get(reverse("vignetten:detail", args=[vignette.pk]))
        self.assertContains(detail_response, f"Gepinnter Simulationskern: {kern.pk}")

    def test_formular_belegt_akteure_vor_und_bietet_keine_kernwahl(self) -> None:
        """Akteure sind als Komfort vorausgefüllt; der Kern bleibt nicht wählbar."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        self.client.force_login(ada)

        response = self.client.get(reverse("vignetten:anlegen"))

        self.assertContains(response, 'name="schuelerin_name" value="')
        self.assertContains(response, 'name="schuelerin_geschlecht"')
        self.assertContains(response, 'name="lehrperson_name" value="')
        self.assertContains(response, 'name="lehrperson_geschlecht"')
        self.assertNotContains(response, 'name="gepinnter_kern"')


class VignetteDetailViewTests(TestCase):
    """Die Detailansicht zeigt den Aufgabenkontext einer sichtbaren Fassung."""

    def test_rendert_die_rohfelder_des_aufgabenkontexts(self) -> None:
        """Die Ansicht zeigt Lernauftrag und Arbeitsheft ohne Rahmen-Rendering."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        vignette: Vignette = Vignette.objects.create(
            historie=historie,
            lernauftrag="Addiere 27 und 15.",
            arbeitsheft_text="27 + 15 = 312",
            arbeitsheft_beschreibung="Die Zahlen stehen untereinander.",
        )
        self.client.force_login(ada)

        response = self.client.get(reverse("vignetten:detail", args=[vignette.pk]))

        self.assertContains(response, "Addiere 27 und 15.")
        self.assertContains(response, "27 + 15 = 312")
        self.assertContains(response, "Die Zahlen stehen untereinander.")

    def test_versteckt_fremde_fassung(self) -> None:
        """Detail-URLs geben keine Fassungen anderer Eigentümerinnen preis."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(grace)
        fremde_vignette: Vignette = Vignette.objects.create(historie=historie)
        self.client.force_login(ada)

        response = self.client.get(
            reverse("vignetten:detail", args=[fremde_vignette.pk])
        )

        self.assertEqual(response.status_code, 404)


class VignettenLoginTests(TestCase):
    """Alle Editor-Einstiege verlangen eine Anmeldung."""

    def test_anonyme_zugriffe_werden_zum_login_geleitet(self) -> None:
        """Liste, Anlegen und Detail sind ausschließlich eingeloggten Personen offen."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        vignette: Vignette = Vignette.objects.create(historie=historie)

        for url in (
            reverse("vignetten:liste"),
            reverse("vignetten:anlegen"),
            reverse("vignetten:detail", args=[vignette.pk]),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/accounts/login/?next="))

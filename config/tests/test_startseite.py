"""HTTP-Tests für den öffentlichen Einstieg."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto


class StartseiteTests(TestCase):
    """Die Startseite ist der öffentliche Navigationseinstieg."""

    def test_ausbildungskachel_verweist_auf_die_vignettenliste(self) -> None:
        """Die Ausbildungskachel führt zum Vignetten-Editor."""
        response: HttpResponse = self.client.get(reverse("start"))

        self.assertContains(response, f'href="{reverse("vignetten:liste")}"')

    def test_systemkachel_verweist_auf_den_simulationskern(self) -> None:
        """Die Systemkachel führt zur Systemansicht."""
        response: HttpResponse = self.client.get(reverse("start"))

        self.assertContains(response, f'href="{reverse("simulation:kern")}"')

    def test_unverfuegbare_bereiche_sind_als_geplant_markiert(self) -> None:
        """Teilnahme und Forschung bleiben bis zur Umsetzung als geplant."""
        response: HttpResponse = self.client.get(reverse("start"))

        self.assertContains(response, "geplant", count=2)

    def test_anonyme_navigation_bietet_den_login(self) -> None:
        """Ohne Anmeldung führt die globale Navigation zur Loginseite."""
        response: HttpResponse = self.client.get(reverse("start"))

        self.assertContains(response, f'href="{reverse("login")}"')
        self.assertContains(response, f'href="{reverse("vignetten:liste")}"')
        self.assertContains(response, f'href="{reverse("simulation:kern")}"')

    def test_angemeldete_navigation_bietet_den_logout(self) -> None:
        """Angemeldete Konten können sich über die Navigation abmelden."""
        konto: Konto = get_user_model().objects.create_user(username="ada")
        self.client.force_login(konto)

        response: HttpResponse = self.client.get(reverse("start"))

        self.assertContains(response, "Logout")

    def test_loginseite_rendert_das_passwortfeld(self) -> None:
        """Djangos Login-URL liefert ein verwendbares Formular aus."""
        response: HttpResponse = self.client.get(reverse("login"))

        self.assertContains(response, 'name="password"')

    def test_direkter_login_fuehrt_zur_startseite(self) -> None:
        """Ein Login ohne Weiterleitungsziel endet auf einer vorhandenen Seite."""
        get_user_model().objects.create_user(
            username="ada", password="sicheres-passwort"
        )

        response: HttpResponse = self.client.post(
            reverse("login"),
            {"username": "ada", "password": "sicheres-passwort"},
        )

        self.assertRedirects(response, reverse("start"))

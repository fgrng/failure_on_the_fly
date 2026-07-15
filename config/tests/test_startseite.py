"""HTTP-Tests für den öffentlichen Einstieg."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto


class StartseiteTests(TestCase):
    """Die Startseite ist der öffentliche Navigationseinstieg."""

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

        self.assertContains(response, "Abmelden")

    def test_bereichskarten_folgen_der_farbcodierung(self) -> None:
        """Simulationskern und Vignetten teilen sich den Entwicklungsbereich."""
        response: HttpResponse = self.client.get(reverse("start"))

        self.assertContains(response, 'card card--authoring', count=1)
        self.assertContains(response, 'card card--system card--disabled', count=1)

    def test_loginseite_rendert_das_passwortfeld(self) -> None:
        """Djangos Login-URL liefert ein verwendbares Formular aus."""
        response: HttpResponse = self.client.get(reverse("login"))

        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'class="site-sidebar"')

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

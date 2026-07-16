"""HTTP-Tests für den öffentlichen Einstieg."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
        sidebar: str = response.content.decode().partition("</aside>")[0]
        self.assertNotIn("Entwicklung", sidebar)
        self.assertNotIn("Ausbildung", sidebar)
        self.assertNotIn("Forschung", sidebar)
        self.assertNotIn("System", sidebar)

    def test_angemeldete_navigation_bietet_den_logout(self) -> None:
        """Angemeldete Konten können sich über die Navigation abmelden."""
        konto: Konto = get_user_model().objects.create_user(username="ada")
        self.client.force_login(konto)

        response: HttpResponse = self.client.get(reverse("start"))

        self.assertContains(response, "Abmelden")

    def test_teilnehmerin_sieht_nur_teilnahmenavigation(self) -> None:
        """Ein Konto ohne Sonderrolle sieht keine fremden Bereiche."""
        konto: Konto = get_user_model().objects.create_user(username="studi")
        self.client.force_login(konto)

        response: HttpResponse = self.client.get(reverse("start"))
        sidebar: str = response.content.decode().partition("</aside>")[0]

        self.assertIn("Training starten", sidebar)
        self.assertIn("Meine Trainings", sidebar)
        self.assertNotIn("Entwicklung", sidebar)
        self.assertNotIn("Forschung", sidebar)
        self.assertNotIn("System", sidebar)
        self.assertNotIn("Trainingskataloge ansehen", sidebar)
        self.assertNotIn("Trainingskatalog erstellen", sidebar)

    def test_sonderrollen_sehen_ihre_bereiche(self) -> None:
        """Jede Sonderrolle erhält nur die zugehörigen Navigationslinks."""
        for rolle, sichtbare_links, verborgene_links in (
            (
                "Autor:in",
                ("Vignetten ansehen", "Simulationskern ansehen"),
                ("Trainingskataloge ansehen", "Meine Erhebungen", "Administration"),
            ),
            (
                "Ausbilder:in",
                ("Trainingskataloge ansehen", "Trainingskatalog erstellen"),
                ("Vignetten ansehen", "Training starten", "Meine Erhebungen"),
            ),
            (
                "Forschende:r",
                ("Meine Erhebungen", "Neue Erhebung anlegen"),
                ("Vignetten ansehen", "Trainingskataloge ansehen", "Administration"),
            ),
            (
                "Administrator:in",
                (
                    "Simulationskern verwalten",
                    "Administration",
                    "Meine Trainings",
                    "Trainingskataloge ansehen",
                    "Meine Erhebungen",
                ),
                (),
            ),
        ):
            with self.subTest(rolle=rolle):
                konto: Konto = get_user_model().objects.create_user(
                    username=rolle, is_staff=rolle == "Administrator:in"
                )
                konto.groups.add(Group.objects.get(name=rolle))
                self.client.force_login(konto)

                response: HttpResponse = self.client.get(reverse("start"))
                sidebar: str = response.content.decode().partition("</aside>")[0]

                for link in sichtbare_links:
                    self.assertIn(link, sidebar)
                for link in verborgene_links:
                    self.assertNotIn(link, sidebar)
                self.client.logout()

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

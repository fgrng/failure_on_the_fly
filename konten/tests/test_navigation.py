"""Tests für die rollenbasierte Navigation."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from konten.navigation import navigation
from konten.models import Konto


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("rollen", "erwartet"),
    [
        (
            [],
            {
                "zeige_entwicklung": False,
                "zeige_ausbildung_kuratieren": False,
                "zeige_teilnahme": True,
                "zeige_forschung": False,
                "zeige_system": False,
                "simulationskern_verwalten": False,
            },
        ),
        (
            ["Autor:in"],
            {
                "zeige_entwicklung": True,
                "zeige_ausbildung_kuratieren": False,
                "zeige_teilnahme": False,
                "zeige_forschung": False,
                "zeige_system": False,
                "simulationskern_verwalten": False,
            },
        ),
        (
            ["Ausbilder:in"],
            {
                "zeige_entwicklung": False,
                "zeige_ausbildung_kuratieren": True,
                "zeige_teilnahme": False,
                "zeige_forschung": False,
                "zeige_system": False,
                "simulationskern_verwalten": False,
            },
        ),
        (
            ["Forschende:r"],
            {
                "zeige_entwicklung": False,
                "zeige_ausbildung_kuratieren": False,
                "zeige_teilnahme": False,
                "zeige_forschung": True,
                "zeige_system": False,
                "simulationskern_verwalten": False,
            },
        ),
        (
            ["Administrator:in"],
            {
                "zeige_entwicklung": True,
                "zeige_ausbildung_kuratieren": True,
                "zeige_teilnahme": False,
                "zeige_forschung": True,
                "zeige_system": True,
                "simulationskern_verwalten": True,
            },
        ),
    ],
)
def test_navigation_berechnet_sichtbarkeit_aus_kontorollen(
    rollen: list[str], erwartet: dict[str, bool]
) -> None:
    """Die Navigation kennt Gruppenrollen und den Admin-Override zentral."""
    konto: Konto = get_user_model().objects.create_user(username="ada")
    konto.groups.add(*Group.objects.filter(name__in=rollen))
    request: HttpRequest = RequestFactory().get("/")
    request.user = konto

    assert navigation(request) == erwartet


class SidebarNavigationTests(TestCase):
    """Die Sidebar verwendet ausschließlich die berechneten Booleans."""

    def _sidebar_fuer(self, *rollen: str) -> str:
        konto: Konto = get_user_model().objects.create_user(username="ada")
        konto.groups.add(*Group.objects.filter(name__in=rollen))
        self.client.force_login(konto)
        return self.client.get(reverse("training:katalog")).content.decode()

    def test_teilnehmerin_sieht_nur_teilnahme_links(self) -> None:
        """Ein Konto ohne Gruppe erhält nur den Teil der Ausbildung zur Teilnahme."""
        sidebar: str = self._sidebar_fuer()

        self.assertIn("Training starten", sidebar)
        self.assertIn("Meine Trainings", sidebar)
        self.assertNotIn("Vignetten ansehen", sidebar)
        self.assertNotIn("Trainingskatalog erstellen", sidebar)
        self.assertNotIn("Meine Erhebungen", sidebar)
        self.assertNotIn("Administration", sidebar)

    def test_ausbilderin_sieht_nur_kuratierung_in_der_ausbildung(self) -> None:
        """Die Ausbilderrolle enthält nicht automatisch die Teilnahme."""
        sidebar: str = self._sidebar_fuer("Ausbilder:in")

        self.assertIn("Trainingskataloge ansehen", sidebar)
        self.assertIn("Trainingskatalog erstellen", sidebar)
        self.assertIn("Trainingsdaten <small>geplant</small>", sidebar)
        self.assertNotIn("Training starten", sidebar)
        self.assertNotIn("Meine Trainings", sidebar)

    def test_autorin_sieht_entwicklung_mit_lesendem_kern_link(self) -> None:
        """Autorinnen können den Kern ansehen, aber nicht verwalten."""
        sidebar: str = self._sidebar_fuer("Autor:in")

        self.assertIn("Vignetten ansehen", sidebar)
        self.assertIn("Simulationskern ansehen", sidebar)
        self.assertNotIn("Simulationskern verwalten", sidebar)
        self.assertNotIn("Training starten", sidebar)

    def test_forschende_sieht_forschungsbereich(self) -> None:
        """Die Forschung hängt nicht mehr an einer Template-Gruppenschleife."""
        sidebar: str = self._sidebar_fuer("Forschende:r")

        self.assertIn("Meine Erhebungen", sidebar)
        self.assertIn("Neue Erhebung anlegen", sidebar)
        self.assertIn("Fragebogen-Items", sidebar)

    def test_administratorin_sieht_alle_bereiche_ausser_teilnahme(self) -> None:
        """Die Gruppenrolle der Administration überschreibt fast alle Sichtbarkeiten."""
        sidebar: str = self._sidebar_fuer("Administrator:in")

        for text in (
            "Vignetten ansehen",
            "Simulationskern verwalten",
            "Trainingskatalog erstellen",
            "Meine Erhebungen",
            "Fragebogen-Items",
            "Administration",
        ):
            self.assertIn(text, sidebar)

        self.assertNotIn("Training starten", sidebar)
        self.assertNotIn("Meine Trainings", sidebar)

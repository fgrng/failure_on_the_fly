"""Tests für die rollenbasierte Navigation."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from konten.navigation import (
    AUTORIN_GRUPPE,
    administratorin_erforderlich,
    navigation,
)
from konten.models import Konto
from simulation.models import Simulationskern
from training.models import Training
from vignetten.models import Vignette


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("rollen", "is_superuser", "erwartet"),
    [
        (
            [],
            False,
            {
                "zeige_entwicklung": False,
                "zeige_ausbildung_kuratieren": False,
                "zeige_teilnahme": True,
                "zeige_abschriften": True,
                "zeige_forschung": False,
                "zeige_system": False,
            },
        ),
        (
            ["Autor:in"],
            False,
            {
                "zeige_entwicklung": True,
                "zeige_ausbildung_kuratieren": False,
                "zeige_teilnahme": False,
                "zeige_abschriften": True,
                "zeige_forschung": False,
                "zeige_system": False,
            },
        ),
        (
            ["Ausbilder:in"],
            False,
            {
                "zeige_entwicklung": False,
                "zeige_ausbildung_kuratieren": True,
                "zeige_teilnahme": False,
                "zeige_abschriften": True,
                "zeige_forschung": False,
                "zeige_system": False,
            },
        ),
        (
            ["Forschende:r"],
            False,
            {
                "zeige_entwicklung": False,
                "zeige_ausbildung_kuratieren": False,
                "zeige_teilnahme": False,
                "zeige_abschriften": True,
                "zeige_forschung": True,
                "zeige_system": False,
            },
        ),
        (
            [],
            True,
            {
                "zeige_entwicklung": True,
                "zeige_ausbildung_kuratieren": True,
                "zeige_teilnahme": False,
                "zeige_abschriften": True,
                "zeige_forschung": True,
                "zeige_system": True,
            },
        ),
    ],
)
def test_navigation_berechnet_sichtbarkeit_aus_kontorollen(
    rollen: list[str], is_superuser: bool, erwartet: dict[str, bool]
) -> None:
    """Die Navigation kennt Gruppenrollen und den Admin-Override zentral."""
    konto: Konto = get_user_model().objects.create_user(
        username="ada", is_superuser=is_superuser
    )
    konto.groups.add(*Group.objects.filter(name__in=rollen))
    request: HttpRequest = RequestFactory().get("/")
    request.user = konto

    assert navigation(request) == erwartet


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("is_superuser", "ist_autorin", "erwarteter_status"),
    [(True, False, 200), (False, True, 403), (False, False, 403)],
)
def test_administratorin_erforderlich_schuetzt_views_mit_der_administrationsrolle(
    is_superuser: bool, ist_autorin: bool, erwarteter_status: int
) -> None:
    """Nur die Administratorin passiert den Decorator, auch ohne Anmeldung nicht."""
    request: HttpRequest = RequestFactory().get("/")
    if is_superuser or ist_autorin:
        konto: Konto = get_user_model().objects.create_user(
            username="ada", is_superuser=is_superuser
        )
        if ist_autorin:
            konto.groups.add(Group.objects.get(name=AUTORIN_GRUPPE))
        request.user = konto
    else:
        request.user = AnonymousUser()

    @administratorin_erforderlich
    def geschuetzte_view(request: HttpRequest) -> HttpResponse:
        return HttpResponse()

    assert geschuetzte_view(request).status_code == erwarteter_status


class SidebarNavigationTests(TestCase):
    """Die Sidebar verwendet ausschließlich die berechneten Booleans."""

    def _sidebar_fuer(self, *rollen: str, is_superuser: bool = False) -> str:
        # Eigener Kontoname je Aufruf, damit ein Test mehrere Rollen nacheinander
        # durch dieselbe Sidebar schicken kann.
        konto: Konto = get_user_model().objects.create_user(
            username=f"ada{Konto.objects.count()}", is_superuser=is_superuser
        )
        konto.groups.add(*Group.objects.filter(name__in=rollen))
        self.client.force_login(konto)
        return self.client.get(reverse("training:katalog")).content.decode()

    def test_teilnehmerin_sieht_nur_teilnahme_links(self) -> None:
        """Ein Konto ohne Gruppe erhält nur den Teil der Ausbildung zur Teilnahme."""
        sidebar: str = self._sidebar_fuer()

        self.assertIn("Training starten", sidebar)
        self.assertIn("Meine Trainings", sidebar)
        self.assertNotIn("Vignetten ansehen", sidebar)
        self.assertNotIn("Neues Training anlegen", sidebar)
        self.assertNotIn("Meine Erhebungen", sidebar)
        self.assertNotIn("Administration", sidebar)

    def test_ausbilderin_sieht_nur_kuratierung_in_der_ausbildung(self) -> None:
        """Die Ausbilderrolle enthält nicht automatisch die Teilnahme."""
        sidebar: str = self._sidebar_fuer("Ausbilder:in")

        self.assertIn("Trainings ansehen", sidebar)
        self.assertIn("Neues Training anlegen", sidebar)
        self.assertNotIn("Trainingsdaten", sidebar)
        self.assertNotIn("Training starten", sidebar)
        self.assertNotIn("Meine Trainings", sidebar)

    def test_autorin_sieht_entwicklung_mit_lesendem_kern_link(self) -> None:
        """Autorinnen können den Kern ansehen, aber nicht verwalten."""
        sidebar: str = self._sidebar_fuer("Autor:in")

        self.assertIn("Vignetten ansehen", sidebar)
        self.assertIn("Neue Vignette anlegen", sidebar)
        self.assertIn("Simulationskern ansehen", sidebar)
        self.assertNotIn("Simulationskern verwalten", sidebar)
        self.assertNotIn("Training starten", sidebar)

    def test_jede_rolle_erreicht_die_abschriften(self) -> None:
        """Die Abschrift hängt am Konto, nicht an einer Rolle (ADR-0043)."""
        for rollen in ([], ["Autor:in"], ["Ausbilder:in"], ["Forschende:r"]):
            with self.subTest(rollen=rollen):
                self.assertIn("Meine Abschriften", self._sidebar_fuer(*rollen))

    def test_forschende_sieht_forschungsbereich(self) -> None:
        """Die Forschung hängt nicht mehr an einer Template-Gruppenschleife."""
        sidebar: str = self._sidebar_fuer("Forschende:r")

        self.assertIn("Meine Erhebungen", sidebar)
        self.assertIn("Neue Erhebung anlegen", sidebar)
        self.assertIn("Fragebogen-Items", sidebar)

    def test_administratorin_sieht_alle_bereiche_ausser_teilnahme(self) -> None:
        """Die Administration überschreibt fast alle Sichtbarkeiten."""
        sidebar: str = self._sidebar_fuer(is_superuser=True)

        for text in (
            "Vignetten ansehen",
            "Simulationskern ansehen",
            "Simulationskern verwalten",
            "Neues Training anlegen",
            "Meine Erhebungen",
            "Fragebogen-Items",
            "Administration",
        ):
            self.assertIn(text, sidebar)

        self.assertNotIn("Training starten", sidebar)
        self.assertNotIn("Meine Trainings", sidebar)

    def test_simulationskern_verwalten_steht_unter_entwicklung(self) -> None:
        """Die Kernverwaltung gehört zur Gruppe Entwicklung, nicht zu System."""
        sidebar: str = self._sidebar_fuer(is_superuser=True)
        entwicklung: str = sidebar.partition("<h2>Entwicklung</h2>")[2]
        entwicklung = entwicklung.partition("<h2>")[0]
        system: str = sidebar.partition("<h2>System</h2>")[2]
        system = system.partition("</section>")[0]

        self.assertIn("Simulationskern verwalten", entwicklung)
        self.assertNotIn("Simulationskern verwalten", system)


class BereichszuordnungTests(TestCase):
    """Jede Seite trägt den Bereich ihrer Sidebar-Gruppe (ADR-0024)."""

    def test_seiten_tragen_den_bereich_ihrer_sidebar_gruppe(self) -> None:
        """Seiten ohne eigene Farbe erben die Gruppe, unter der sie stehen."""
        linus: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        kern_entwurf: Simulationskern = kern.bearbeiten()
        vignette: Vignette = Vignette.objects.anlegen(linus)
        training_entwurf: Training = Training.objects.anlegen(linus, name="Brüche")
        training_veroeffentlicht: Training = Training.objects.anlegen(
            linus, name="Prozente"
        )
        training_veroeffentlicht.veroeffentlichen()
        self.client.force_login(linus)

        for url, bereich in (
            (reverse("vignetten:liste"), "authoring"),
            (reverse("vignetten:detail", args=[vignette.pk]), "authoring"),
            (reverse("simulation:kern_verwalten"), "authoring"),
            (
                reverse("simulation:kern_bearbeiten", args=[kern_entwurf.pk]),
                "authoring",
            ),
            (reverse("training:katalog"), "participant"),
            (reverse("training:liste"), "participant"),
            (reverse("training:anlegen"), "participant"),
            (reverse("training:kuratieren", args=[training_entwurf.pk]), "participant"),
            (
                reverse("training:detail", args=[training_veroeffentlicht.pk]),
                "participant",
            ),
        ):
            with self.subTest(url=url):
                seite: str = self.client.get(url).content.decode()
                self.assertRegex(
                    seite, rf'<section class="page[^"]* area--{bereich}[ "]'
                )

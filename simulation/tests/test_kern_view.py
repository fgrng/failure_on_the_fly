"""HTTP-Tests für die read-only Ansicht des Simulationskerns."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern


def _autorin(username: str) -> Konto:
    """Legt ein Konto mit Zugriff auf den Simulationskern an."""
    konto: Konto = get_user_model().objects.create_user(username=username)
    konto.groups.add(Group.objects.get(name="Autor:in"))
    return konto


class SimulationskernAnsichtMitKernTests(TestCase):
    """Die Kernansicht zeigt die aktuelle finale Fassung ohne Schreibroute."""

    def setUp(self) -> None:
        """Legt die aktuelle finale Kern-Fassung und Modell-Konfiguration an."""
        konto: Konto = _autorin("ada")
        aelterer_kern: Simulationskern = Simulationskern.objects.anlegen(
            system_prompt_vorlage="Alter System-Prompt",
        )
        aelterer_kern.finalisieren()
        kern: Simulationskern = aelterer_kern.bearbeiten()
        kern.system_prompt_vorlage = "Aktueller System-Prompt"
        kern.user_prompt_vorlage = "Aktueller User-Prompt"
        kern.rahmenhandlung_einleitung = "Aktuelle Einleitung"
        kern.rahmenhandlung_gespraechseinleitung = "Aktuelle Gesprächseinleitung"
        kern.rahmenhandlung_debrief = "Aktueller Debrief"
        kern.save()
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter={"temperature": 0.2}
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.client.force_login(konto)

    def test_zeigt_den_system_prompt_der_neuesten_finalen_fassung(self) -> None:
        """Angemeldete sehen den System-Prompt der neuesten finalen Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Aktueller System-Prompt")

    def test_zeigt_den_user_prompt_der_neuesten_finalen_fassung(self) -> None:
        """Angemeldete sehen den User-Prompt der neuesten finalen Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Aktueller User-Prompt")

    def test_zeigt_die_einleitung_der_neuesten_finalen_fassung(self) -> None:
        """Angemeldete sehen die Einleitung der neuesten finalen Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Aktuelle Einleitung")

    def test_zeigt_den_debrief_der_neuesten_finalen_fassung(self) -> None:
        """Angemeldete sehen den Debrief der neuesten finalen Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Aktueller Debrief")

    def test_zeigt_die_gespraechseinleitung_der_neuesten_finalen_fassung(self) -> None:
        """Angemeldete sehen die Gesprächseinleitung der neuesten Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Aktuelle Gesprächseinleitung")

    def test_zeigt_keinen_aelteren_system_prompt(self) -> None:
        """Angemeldete sehen nicht den System-Prompt der älteren Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertNotContains(response, "Alter System-Prompt")

    def test_zeigt_die_aktive_modellkonfiguration(self) -> None:
        """Angemeldete sehen die aktive Modell-Konfiguration."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "fake")

    def test_zeigt_die_erlaubten_platzhalter_beider_vertraege(self) -> None:
        """Die Referenzspalten stammen aus Prompt- und Rahmenvertrag."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "$fehlermuster_beschreibung")
        self.assertContains(response, "$lehrperson_anrede")


class SimulationskernLeereAnsichtTests(TestCase):
    """Die Kernansicht bleibt ohne Kern und Konfiguration verständlich."""

    def setUp(self) -> None:
        """Legt ein Konto an, ohne einen Kern zu initialisieren."""
        self.konto: Konto = _autorin("ada")

    def test_zeigt_initialisierungshinweis_ohne_finalen_kern(self) -> None:
        """Eine noch leere Installation bleibt lesbar statt mit 500 zu scheitern."""
        self.client.force_login(self.konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Noch nicht initialisiert")

    def test_zeigt_den_initialisierungsbefehl_ohne_finalen_kern(self) -> None:
        """Eine leere Installation nennt den nötigen Initialisierungsbefehl."""
        self.client.force_login(self.konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "manage.py kern_initialisieren")

    def test_zeigt_fehlende_aktive_modellkonfiguration(self) -> None:
        """Ohne aktiven Zeiger erklärt die Ansicht die fehlende Konfiguration."""
        self.client.force_login(self.konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Keine aktive Modell-Konfiguration")

    def test_erfordert_anmeldung(self) -> None:
        """Anonyme Anfragen werden zur Anmeldung weitergeleitet."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertRedirects(
            response,
            "/accounts/login/?next=/system/kern/",
            fetch_redirect_response=False,
        )


class SimulationskernRollenTests(TestCase):
    """Der Simulationskern ist Teil der geschützten Entwicklung."""

    def test_teilnehmerin_wird_abgewiesen_und_administratorin_zugelassen(self) -> None:
        """Die Gruppenrollen entscheiden statt is_superuser oder Template-Links."""
        teilnehmerin: Konto = get_user_model().objects.create_user(username="studi")
        self.client.force_login(teilnehmerin)
        self.assertEqual(self.client.get(reverse("simulation:kern")).status_code, 403)

        administratorin: Konto = get_user_model().objects.create_user(username="linus")
        administratorin.groups.add(Group.objects.get(name="Administrator:in"))
        self.client.force_login(administratorin)
        self.assertEqual(self.client.get(reverse("simulation:kern")).status_code, 200)

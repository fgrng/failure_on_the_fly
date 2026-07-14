"""HTTP-Tests für die read-only Ansicht des Simulationskerns."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern


class SimulationskernViewTests(TestCase):
    """Die Kernansicht zeigt die aktuelle finale Fassung ohne Schreibroute."""

    def test_zeigt_die_neueste_finale_fassung_und_aktive_modellkonfiguration(
        self,
    ) -> None:
        """Angemeldete sehen den zuletzt finalisierten Kern samt Modell-Konfiguration."""
        konto: Konto = get_user_model().objects.create_user(username="ada")
        aelterer_kern: Simulationskern = Simulationskern.objects.anlegen(
            system_prompt_vorlage="Alter System-Prompt",
        )
        aelterer_kern.finalisieren()
        kern: Simulationskern = aelterer_kern.bearbeiten()
        kern.system_prompt_vorlage = "Aktueller System-Prompt"
        kern.user_prompt_vorlage = "Aktueller User-Prompt"
        kern.rahmenhandlung_einleitung = "Aktuelle Einleitung"
        kern.rahmenhandlung_debrief = "Aktueller Debrief"
        kern.save()
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter={"temperature": 0.2}
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.client.force_login(konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Aktueller System-Prompt")
        self.assertContains(response, "Aktueller User-Prompt")
        self.assertContains(response, "Aktuelle Einleitung")
        self.assertContains(response, "Aktueller Debrief")
        self.assertNotContains(response, "Alter System-Prompt")
        self.assertContains(response, "fake")
        self.assertContains(response, 'class="area--system"')

    def test_zeigt_initialisierungshinweis_ohne_finalen_kern(self) -> None:
        """Eine noch leere Installation bleibt lesbar statt mit 500 zu scheitern."""
        konto: Konto = get_user_model().objects.create_user(username="ada")
        self.client.force_login(konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Noch nicht initialisiert")
        self.assertContains(response, "manage.py kern_initialisieren")
        self.assertContains(response, "Keine aktive Modell-Konfiguration")

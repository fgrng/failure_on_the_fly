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


def _administratorin(username: str) -> Konto:
    """Legt ein Konto mit Zugriff auf die Kern-Verwaltung an."""
    return get_user_model().objects.create_user(username=username, is_superuser=True)


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
        for platzhalter in (
            "arbeitsheft",
            "arbeitsheft_simulationshinweise",
            "fehlermuster_beschreibung",
            "lernauftrag",
            "lernauftrag_simulationshinweise",
        ):
            self.assertContains(
                response,
                f"<li><code>${platzhalter}</code> — erzeugt eine benannte Umgebung</li>",
            )
        for platzhalter in (
            "fach",
            "klassenstufe",
            "schuelerin_geschlecht",
            "schuelerin_name",
            "thema",
        ):
            self.assertContains(response, f"<li><code>${platzhalter}</code></li>")


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
        """Gruppenrollen und is_superuser entscheiden statt Template-Links."""
        teilnehmerin: Konto = get_user_model().objects.create_user(username="studi")
        self.client.force_login(teilnehmerin)
        self.assertEqual(self.client.get(reverse("simulation:kern")).status_code, 403)

        administratorin: Konto = get_user_model().objects.create_user(username="linus")
        administratorin.is_superuser = True
        administratorin.save()
        self.client.force_login(administratorin)
        self.assertEqual(self.client.get(reverse("simulation:kern")).status_code, 200)


class SimulationskernVerwaltungTests(TestCase):
    """Die Verwaltung zeigt alle Kern-Fassungen der einzigen Historie."""

    def test_zeigt_entwurf_finale_und_eingeklappte_archivierte_fassungen(self) -> None:
        """Administratorinnen überblicken die gesamte Kern-Historie."""
        aelteste_fassung: Simulationskern = Simulationskern.objects.anlegen(
            system_prompt_vorlage="Archivierter Prompt"
        )
        aelteste_fassung.finalisieren()
        aktuelle_fassung: Simulationskern = aelteste_fassung.bearbeiten()
        aktuelle_fassung.system_prompt_vorlage = "Aktueller Prompt"
        aktuelle_fassung.save()
        aktuelle_fassung.finalisieren()
        aelteste_fassung.archivieren()
        entwurf: Simulationskern = aktuelle_fassung.bearbeiten()
        entwurf.system_prompt_vorlage = "Entwurfs-Prompt"
        entwurf.save()
        self.client.force_login(_administratorin("linus"))

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, 'class="page system-page area--system"')
        self.assertContains(response, "Entwurfs-Prompt")
        self.assertContains(response, "Aktueller Prompt")
        self.assertContains(response, "Archivierter Prompt")
        self.assertContains(response, "<details>", html=False)

    def test_weist_autorin_und_konto_ohne_rolle_ab(self) -> None:
        """Nur Administratorinnen dürfen die blaue Übersicht öffnen."""
        for konto in (_autorin("ada"), get_user_model().objects.create_user("studi")):
            self.client.force_login(konto)

            response: HttpResponse = self.client.get(
                reverse("simulation:kern_verwalten")
            )

            self.assertEqual(response.status_code, 403)

    def test_markiert_die_autorinnen_ansicht_gelb(self) -> None:
        """Die read-only Ansicht erbt das Chrome ihres Entwicklungsbereichs."""
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.client.force_login(_autorin("ada"))

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, 'class="page system-page area--authoring"')
        self.assertContains(response, 'class="badge badge--authoring"')

    def test_markiert_in_der_sidebar_nur_den_verwaltungslink(self) -> None:
        """Die zwei Kern-Routen teilen den Namespace, nicht den aktiven Link."""
        self.client.force_login(_administratorin("linus"))

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(
            response,
            '<a href="/system/kern/">Simulationskern ansehen</a>',
            html=False,
        )
        self.assertContains(
            response,
            '<a href="/system/kern/verwalten/" aria-current="page">Simulationskern verwalten</a>',
            html=False,
        )

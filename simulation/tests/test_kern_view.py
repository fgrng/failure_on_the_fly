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

    def test_benennt_die_gemeinsamen_abschnitte_fuer_hilfstechnologien(self) -> None:
        """Die extrahierten Abschnitte behalten ihre zugänglichen Namen."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        for abschnitt in (
            "Rahmenhandlung",
            "Prompt-Vorlagen",
            "Modell-Konfiguration",
        ):
            self.assertContains(response, f'aria-label="{abschnitt}"')

    def test_zeigt_keine_verwaltungsgesten(self) -> None:
        """Die gelbe Leseansicht bleibt trotz gemeinsamem Fassung-Include schreibfrei."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertNotContains(response, "Entwurf ziehen")
        self.assertNotContains(response, "Finalisieren")
        self.assertNotContains(response, "Verwerfen")


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

    def setUp(self) -> None:
        """Legt eine vollständige Kern-Historie für die Übersicht an."""
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

    def test_traegt_die_system_farbfläche(self) -> None:
        """Die Verwaltungsübersicht gehört zum System-Bereich."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, 'class="page system-page area--system"')

    def test_zeigt_den_entwurf(self) -> None:
        """Die Verwaltungsübersicht zeigt den vorhandenen Entwurf."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "Entwurfs-Prompt")

    def test_zieht_aus_finaler_fassung_einen_entwurf(self) -> None:
        """Die Verwaltung legt aus der gewählten finalen Fassung einen Entwurf an."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )
        entwurf.delete()
        finale: Simulationskern = Simulationskern.objects.get(
            system_prompt_vorlage="Aktueller Prompt"
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:neue_fassung", args=[finale.pk])
        )

        self.assertRedirects(response, reverse("simulation:kern_verwalten"))
        self.assertTrue(
            Simulationskern.objects.filter(
                vorgaengerin=finale,
                zustand=Simulationskern.Zustand.ENTWURF,
            ).exists()
        )

    def test_finalisiert_den_entwurf(self) -> None:
        """Die Verwaltung macht den angegebenen Entwurf zu einer finalen Fassung."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:finalisieren", args=[entwurf.pk])
        )

        self.assertRedirects(response, reverse("simulation:kern_verwalten"))
        entwurf.refresh_from_db()
        self.assertEqual(entwurf.zustand, Simulationskern.Zustand.FINAL)

    def test_verwirft_den_entwurf(self) -> None:
        """Die Verwaltung entfernt ausschließlich den angegebenen Entwurf."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:verwerfen", args=[entwurf.pk])
        )

        self.assertRedirects(response, reverse("simulation:kern_verwalten"))
        self.assertFalse(Simulationskern.objects.filter(pk=entwurf.pk).exists())

    def test_verwerfen_weist_finale_und_archivierte_fassungen_ab(self) -> None:
        """Die Verwerfen-Route ist ausschließlich für Entwürfe erreichbar."""
        finale: Simulationskern = Simulationskern.objects.get(
            system_prompt_vorlage="Aktueller Prompt"
        )
        archiviert: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ARCHIVIERT
        )

        for simulationskern in (finale, archiviert):
            response: HttpResponse = self.client.post(
                reverse("simulation:verwerfen", args=[simulationskern.pk]), follow=True
            )
            self.assertContains(response, "hat nicht den erwarteten Zustand")
            self.assertTrue(
                Simulationskern.objects.filter(pk=simulationskern.pk).exists()
            )

    def test_gesten_sind_post_und_administratorinnen_vorbehalten(self) -> None:
        """Die schreibenden Routen weisen GET und Autorinnen ohne Adminrolle ab."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )
        urls: tuple[str, ...] = (
            reverse("simulation:neue_fassung", args=[entwurf.vorgaengerin_id]),
            reverse("simulation:finalisieren", args=[entwurf.pk]),
            reverse("simulation:verwerfen", args=[entwurf.pk]),
        )

        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 405)
        self.client.force_login(_autorin("ada"))
        for url in urls:
            self.assertEqual(self.client.post(url).status_code, 403)

    def test_zeigt_modellfehler_als_meldung(self) -> None:
        """Ein belegter Entwurfsplatz wird auf der Übersicht verständlich erklärt."""
        finale: Simulationskern = Simulationskern.objects.get(
            system_prompt_vorlage="Aktueller Prompt"
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:neue_fassung", args=[finale.pk]), follow=True
        )

        self.assertContains(response, "Ein Kern-Entwurf existiert bereits.")

    def test_zeigt_unvollstaendigen_entwurf_als_meldung(self) -> None:
        """Ein vertragswidriger Entwurf scheitert auf der Übersicht lesbar."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )
        entwurf.system_prompt_vorlage = "$unbekannt"
        entwurf.save()

        response: HttpResponse = self.client.post(
            reverse("simulation:finalisieren", args=[entwurf.pk]), follow=True
        )

        self.assertContains(response, "Enthält ungültige Platzhalter.")

    def test_kennzeichnet_die_juengste_finale_fassung_als_verwendet(self) -> None:
        """Die Verwaltungsübersicht hebt die aktuell verwendete Fassung hervor."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "Verwendete finale Fassung")

    def test_zeigt_die_juengste_finale_fassung(self) -> None:
        """Die Verwaltungsübersicht zeigt die jüngste finale Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "Aktueller Prompt")

    def test_zeigt_die_archivierte_fassung(self) -> None:
        """Die Verwaltungsübersicht zeigt die archivierte Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "Archivierter Prompt")

    def test_klappt_archivierte_fassungen_ein(self) -> None:
        """Die Verwaltungsübersicht hält archivierte Fassungen eingeklappt bereit."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "<details>", html=False)

    def test_weist_autorin_ab(self) -> None:
        """Eine Autorin ohne Administrationsrolle darf die Übersicht nicht öffnen."""
        self.client.force_login(_autorin("ada"))

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertEqual(response.status_code, 403)

    def test_weist_konto_ohne_rolle_ab(self) -> None:
        """Ein Konto ohne Rolle darf die Übersicht nicht öffnen."""
        self.client.force_login(get_user_model().objects.create_user("studi"))

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertEqual(response.status_code, 403)

    def test_weist_nicht_angemeldetes_konto_ab(self) -> None:
        """Auch anonyme Anfragen erhalten die geforderte Zugriffsverweigerung."""
        self.client.logout()

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertEqual(response.status_code, 403)


class SimulationskernSeitennavigationTests(TestCase):
    """Chrome und Sidebar unterscheiden die zwei Kern-Ansichten."""

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

    def test_markiert_in_der_sidebar_nur_den_ansichtslink(self) -> None:
        """Die Kernansicht aktiviert nur ihren eigenen Sidebar-Link."""
        self.client.force_login(_administratorin("linus"))

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(
            response,
            '<a href="/system/kern/" aria-current="page">Simulationskern ansehen</a>',
            html=False,
        )
        self.assertContains(
            response,
            '<a href="/system/kern/verwalten/">Simulationskern verwalten</a>',
            html=False,
        )

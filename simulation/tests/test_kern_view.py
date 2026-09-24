"""HTTP-Tests für die read-only Ansicht des Simulationskerns."""

import ast
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from simulation import views
from simulation.models import (
    VERTRAG_PROMPT,
    Anbieter,
    ModellKonfiguration,
    Simulationskern,
    Verwendung,
)
from simulation.standardkern import STANDARDKERN_VORLAGEN


def _autorin(username: str) -> Konto:
    """Legt ein Konto mit Zugriff auf den Simulationskern an."""
    konto: Konto = get_user_model().objects.create_user(username=username)
    konto.groups.add(Group.objects.get(name="Autor:in"))
    return konto


def _administratorin(username: str) -> Konto:
    """Legt ein Konto mit Zugriff auf die Kern-Verwaltung an."""
    return get_user_model().objects.create_user(username=username, is_superuser=True)


class SimulationskernAnsichtLeereRahmenhandlungTests(TestCase):
    """Leere Abschnitte der Rahmenhandlung zeigen den gewohnten Platzhalter."""

    def test_leere_abschnitte_zeigen_einen_strich(self) -> None:
        """Ohne Text steht „—“ im Container, wie in der Leseansicht der Erhebung."""
        kern: Simulationskern = Simulationskern.objects.anlegen(
            system_prompt_vorlage="System-Prompt",
        )
        kern.finalisieren()
        self.client.force_login(_autorin("ada"))

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, '<div class="markdown-text">—</div>', count=3)


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
        kern.rahmenhandlung_einleitung = "# Aktuelle Einleitung\n\nZu **$thema**"
        kern.rahmenhandlung_gespraechseinleitung = (
            "Aktuelle Gesprächseinleitung\n\n- *erster Schritt*"
        )
        kern.rahmenhandlung_debrief = "Aktueller Debrief\n[$fach](https://x.org)"
        kern.save()
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            anbieter=Anbieter.OPENROUTER,
            sprachmodell="openrouter/gpt-test",
            anbieter_token="sk-or-geheim",
            parameter={"temperature": 0.2},
        )
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
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

    def test_rendert_die_rahmenhandlung_mit_woertlichen_platzhaltern(self) -> None:
        """Die drei Abschnitte erscheinen als Szenentext, `$name` bleibt stehen."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "<h3>Aktuelle Einleitung</h3>")
        self.assertContains(response, "Zu <strong>$thema</strong>")
        self.assertContains(response, "<li><em>erster Schritt</em></li>")
        self.assertContains(response, "Aktueller Debrief<br>\n[$fach](https://x.org)")
        self.assertContains(response, 'class="markdown-text"', count=3)

    def test_zeigt_keinen_aelteren_system_prompt(self) -> None:
        """Angemeldete sehen nicht den System-Prompt der älteren Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertNotContains(response, "Alter System-Prompt")

    def test_zeigt_die_aktive_modellkonfiguration(self) -> None:
        """Angemeldete sehen die aktive Modell-Konfiguration."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "openrouter/gpt-test")

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

    def test_stellt_den_leeren_kern_nur_fest(self) -> None:
        """Eine noch leere Installation bleibt lesbar statt mit 500 zu scheitern."""
        self.client.force_login(self.konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Noch keine Rahmenhandlung vorhanden.")
        self.assertContains(response, "Noch keine Prompt-Vorlagen vorhanden.")

    def test_verweist_autorinnen_nicht_auf_die_verwaltung(self) -> None:
        """Die Leseansicht nennt keine Geste, die der Autorin verwehrt ist."""
        self.client.force_login(self.konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertNotContains(response, "manage.py")
        self.assertNotContains(response, reverse("simulation:kern_anlegen"))

    def test_zeigt_fehlende_aktive_modellkonfiguration(self) -> None:
        """Ohne Zeiger der Schüler:in erklärt die Ansicht die fehlende Konfiguration."""
        self.client.force_login(self.konto)

        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertContains(
            response, "Für die Schüler:in ist keine Modell-Konfiguration aktiv."
        )

    def test_erfordert_anmeldung(self) -> None:
        """Anonyme Anfragen werden zur Anmeldung weitergeleitet."""
        response: HttpResponse = self.client.get(reverse("simulation:kern"))

        self.assertRedirects(
            response,
            "/accounts/login/?next=/system/kern/",
            fetch_redirect_response=False,
        )


class ModellKonfigurationAnzeigeTests(TestCase):
    """Die Kern-Ansichten zeigen die Anbieterbindung ohne das Token."""

    def setUp(self) -> None:
        """Aktiviert eine Infomaniak-Konfiguration mit Basis-URL und Token."""
        self.konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            anbieter=Anbieter.INFOMANIAK,
            sprachmodell="openai/mistral24b",
            anbieter_basis_url="https://api.infomaniak.com/1/ai/4711/openai",
            anbieter_token="sk-infomaniak-geheim1234",
            parameter={"temperature": 0.2},
        )
        ModellKonfiguration.objects.aktivieren(
            self.konfiguration, Verwendung.SCHUELERIN
        )
        self.client.force_login(_administratorin("linus"))

    def test_zeigt_anbieter_basis_url_und_parameter(self) -> None:
        """Die Administrator:in sieht, an welchem Endpunkt die Sitzung hängt."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "infomaniak")
        self.assertContains(response, "https://api.infomaniak.com/1/ai/4711/openai")
        self.assertContains(response, "openai/mistral24b")
        self.assertContains(response, "temperature")

    def test_zeigt_das_token_nur_maskiert(self) -> None:
        """Das Geheimnis bleibt auch in der blauen Ansicht ein Geheimnis."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "••••••••1234")
        self.assertNotContains(response, self.konfiguration.anbieter_token)


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


class SimulationskernAnlegenTests(TestCase):
    """Die leere Instanz legt ihre erste Kern-Fassung aus der App heraus an."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an einer Instanz ohne Kern-Fassung an."""
        self.client.force_login(_administratorin("linus"))

    def test_leerzustand_zeigt_beide_anlege_gesten(self) -> None:
        """Ohne jede Fassung bietet die Verwaltung den leeren und den Standardweg."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, reverse("simulation:kern_anlegen_standard"))
        self.assertContains(response, "Neuen Entwurf anlegen")
        self.assertContains(response, "Standardkern als Entwurf anlegen")

    def test_legt_einen_leeren_entwurf_an(self) -> None:
        """Der leere Weg erzeugt genau einen Entwurf mit leeren Inhaltsfeldern."""
        response: HttpResponse = self.client.post(reverse("simulation:kern_anlegen"))

        self.assertRedirects(response, reverse("simulation:kern_verwalten"))
        entwurf: Simulationskern = Simulationskern.objects.get()
        self.assertEqual(entwurf.zustand, Simulationskern.Zustand.ENTWURF)
        self.assertEqual(entwurf.system_prompt_vorlage, "")
        self.assertEqual(entwurf.rahmenhandlung_debrief, "")

    def test_legt_einen_entwurf_aus_den_standardvorlagen_an(self) -> None:
        """Der Standardweg erzeugt einen Entwurf aus dem Standardkern."""
        response: HttpResponse = self.client.post(
            reverse("simulation:kern_anlegen_standard")
        )

        self.assertRedirects(response, reverse("simulation:kern_verwalten"))
        entwurf: Simulationskern = Simulationskern.objects.get()
        self.assertEqual(entwurf.zustand, Simulationskern.Zustand.ENTWURF)
        for feldname, vorlage in STANDARDKERN_VORLAGEN.items():
            self.assertEqual(getattr(entwurf, feldname), vorlage)

    def test_legt_keine_zweite_fassung_an_und_erklaert_die_ablehnung(self) -> None:
        """Eine bereits angelegte Linie nimmt keine zweite erste Fassung an."""
        Simulationskern.objects.anlegen(system_prompt_vorlage="Erster Prompt")

        response: HttpResponse = self.client.post(
            reverse("simulation:kern_anlegen"), follow=True
        )

        self.assertEqual(Simulationskern.objects.count(), 1)
        self.assertContains(response, "Der Simulationskern wurde bereits angelegt.")

    def test_verbirgt_die_gesten_neben_einem_entwurf(self) -> None:
        """Nach der ersten Fassung führt der Weg zu Entwürfen über den Lebenszyklus."""
        Simulationskern.objects.anlegen(system_prompt_vorlage="Erster Prompt")

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertNotContains(response, reverse("simulation:kern_anlegen"))

    def test_verbirgt_die_gesten_neben_einer_finalen_fassung(self) -> None:
        """Die Anzeige folgt derselben Bedingung wie die Anlege-Naht."""
        erste: Simulationskern = Simulationskern.objects.anlegen(
            system_prompt_vorlage="Erster Prompt"
        )
        erste.finalisieren()

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertNotContains(response, reverse("simulation:kern_anlegen"))

    def test_gesten_sind_post_und_administratorinnen_vorbehalten(self) -> None:
        """Die Anlege-Routen weisen GET und Autorinnen ohne Adminrolle ab."""
        urls: tuple[str, ...] = (
            reverse("simulation:kern_anlegen"),
            reverse("simulation:kern_anlegen_standard"),
        )

        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 405)
        self.client.force_login(_autorin("ada"))
        for url in urls:
            self.assertEqual(self.client.post(url).status_code, 403)


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
        # Das Finalisieren der zweiten Fassung archiviert die erste.
        aktuelle_fassung.finalisieren()
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

    def test_verlinkt_den_entwurf_zur_eigenen_bearbeitungsseite(self) -> None:
        """Die Übersicht führt für Inhaltsänderungen auf eine eigene Seite."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(
            response,
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk]),
        )

    def test_bearbeitungsseite_zeigt_felder_und_platzhaltervertraege(self) -> None:
        """Das Formular gliedert Felder und Vertragsreferenzen wie die Ansicht."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.get(
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk])
        )

        for text in (
            "Rahmenhandlung",
            "Prompt-Vorlagen",
            "rahmenhandlung_einleitung",
            "system_prompt_vorlage",
            "$lehrperson_anrede",
            "$fehlermuster_beschreibung",
            "erzeugt eine benannte Umgebung",
        ):
            self.assertContains(response, text)

    def test_bearbeitungsseite_benennt_die_felder_wie_die_ansicht(self) -> None:
        """Formular und Ansicht tragen dieselben Feldbezeichnungen."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.get(
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk])
        )

        for bezeichnung in (
            "Hospitationseinleitung",
            "Gesprächseinleitung",
            "Debrief",
            "System-Prompt-Vorlage",
            "User-Prompt-Vorlage",
        ):
            self.assertContains(response, f">{bezeichnung}</label>")

    def test_rahmenhandlung_bietet_hinweis_und_umschalter_im_szenentext(
        self,
    ) -> None:
        """Nur die drei Rahmenhandlungsfelder erhalten die Markdown-Vorschau."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.get(
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk])
        )

        self.assertContains(response, ">Bearbeiten</button>", count=3)
        self.assertContains(response, ">Vorschau</button>", count=3)
        self.assertContains(response, '"profil": "szenentext"', count=3)
        for feld in (
            "rahmenhandlung_einleitung",
            "rahmenhandlung_gespraechseinleitung",
            "rahmenhandlung_debrief",
        ):
            self.assertContains(response, f'id="id_{feld}_vorschau"')
            self.assertContains(response, f'aria-describedby="id_{feld}_helptext"')
        self.assertNotContains(response, 'id="id_system_prompt_vorlage_vorschau"')
        self.assertNotContains(response, "[Linktext](https://…)")
        self.assertContains(response, "Erlaubte Platzhalter:", count=5)

    def test_kern_vorschau_laesst_platzhalter_woertlich_stehen(self) -> None:
        """Die Vorschau ersetzt keine Platzhalter, Markdown um sie wirkt."""
        response: HttpResponse = self.client.post(
            reverse("texte:vorschau"),
            {"profil": "szenentext", "quelle": "Zu **$thema** bei $lehrperson_anrede"},
        )

        self.assertContains(
            response, "Zu <strong>$thema</strong> bei $lehrperson_anrede"
        )

    def test_platzhalteranzeige_folgt_dem_prompt_vertrag(self) -> None:
        """Die Seite nennt jeden Platzhalter des Prompt-Vertrags."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.get(
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk])
        )

        for platzhalter in VERTRAG_PROMPT:
            self.assertContains(response, f"${platzhalter}")

    def test_ungueltiger_platzhalter_erscheint_am_verursachenden_feld(self) -> None:
        """Die Formularvalidierung ordnet Vertragsverletzungen dem Feld zu."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk]),
            {
                "rahmenhandlung_einleitung": entwurf.rahmenhandlung_einleitung,
                "rahmenhandlung_gespraechseinleitung": (
                    entwurf.rahmenhandlung_gespraechseinleitung
                ),
                "rahmenhandlung_debrief": entwurf.rahmenhandlung_debrief,
                "system_prompt_vorlage": "$unbekannt",
                "user_prompt_vorlage": entwurf.user_prompt_vorlage,
            },
        )

        self.assertFormError(
            response.context["form"],
            "system_prompt_vorlage",
            "Enthält ungültige Platzhalter.",
        )
        self.assertNotIn("__all__", response.context["form"].errors)

    def test_speichert_aenderungen_und_zeigt_sie_nach_finalisierung_an(self) -> None:
        """Die bearbeitete Entwurfsfassung wird nach dem Finalisieren verwendet."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk]),
            {
                "rahmenhandlung_einleitung": entwurf.rahmenhandlung_einleitung,
                "rahmenhandlung_gespraechseinleitung": (
                    entwurf.rahmenhandlung_gespraechseinleitung
                ),
                "rahmenhandlung_debrief": entwurf.rahmenhandlung_debrief,
                "system_prompt_vorlage": "Geänderter System-Prompt",
                "user_prompt_vorlage": entwurf.user_prompt_vorlage,
            },
        )
        self.assertRedirects(response, reverse("simulation:kern_verwalten"))

        self.client.post(reverse("simulation:finalisieren", args=[entwurf.pk]))
        response = self.client.get(reverse("simulation:kern"))

        self.assertContains(response, "Geänderter System-Prompt")

    def test_bearbeiten_weist_finale_und_archivierte_fassungen_ab(self) -> None:
        """Nur der Entwurf ist über die Bearbeitungsroute zugänglich."""
        finale: Simulationskern = Simulationskern.objects.get(
            system_prompt_vorlage="Aktueller Prompt"
        )
        archiviert: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ARCHIVIERT
        )

        for simulationskern in (finale, archiviert):
            response: HttpResponse = self.client.get(
                reverse("simulation:kern_bearbeiten", args=[simulationskern.pk])
            )

            self.assertEqual(response.status_code, 404)

    def test_bearbeiten_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Die Inhaltsbearbeitung ist ausschließlich Administratorinnen erlaubt."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )
        self.client.force_login(_autorin("ada"))

        response: HttpResponse = self.client.get(
            reverse("simulation:kern_bearbeiten", args=[entwurf.pk])
        )

        self.assertEqual(response.status_code, 403)

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
            reverse("simulation:neue_fassung", args=[finale.pk]), follow=True
        )

        self.assertContains(response, "Finalisieren")

    def test_finalisiert_den_entwurf(self) -> None:
        """Die Verwaltung macht den angegebenen Entwurf zu einer finalen Fassung."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:finalisieren", args=[entwurf.pk]), follow=True
        )

        self.assertContains(response, "<h2>Finale Fassung</h2>", html=False)

    def test_verwirft_den_entwurf(self) -> None:
        """Die Verwaltung entfernt ausschließlich den angegebenen Entwurf."""
        entwurf: Simulationskern = Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.ENTWURF
        )

        response: HttpResponse = self.client.post(
            reverse("simulation:verwerfen", args=[entwurf.pk]), follow=True
        )

        self.assertNotContains(response, "Entwurfs-Prompt")

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

    def test_ueberschreibt_die_finale_fassung_ohne_verwendungs_markierung(
        self,
    ) -> None:
        """Bei genau einer finalen Fassung hat eine Verwendungs-Markierung nichts zu sagen."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "<h2>Finale Fassung</h2>", html=False)
        self.assertNotContains(response, "Verwendete finale Fassung")

    def test_zeigt_die_finale_fassung(self) -> None:
        """Die Verwaltungsübersicht zeigt die eine finale Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "Aktueller Prompt")

    def test_zeigt_die_archivierte_fassung(self) -> None:
        """Die Verwaltungsübersicht zeigt die archivierte Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))

        self.assertContains(response, "Archivierter Prompt")

    def test_zeigt_archivierte_fassungen_ohne_aktionsbereich(self) -> None:
        """Eine überholte Fassung bleibt lesbar, trägt aber keinen Aktionsbereich."""
        response: HttpResponse = self.client.get(reverse("simulation:kern_verwalten"))
        seite: str = response.content.decode()

        eingeklappt: str = seite[seite.index("<details>") : seite.index("</details>")]
        self.assertIn("Archivierter Prompt", eingeklappt)
        self.assertNotIn("page-actions", eingeklappt)

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


class SimulationsschichtImportgraphTests(TestCase):
    """Die Kern-Verwaltung kennt die Vignetten-Schicht nicht (ADR-0016)."""

    def test_kern_verwaltung_importiert_die_vignetten_schicht_nicht(self) -> None:
        """Kein Import führt von der Systemansicht in die Vignetten-Schicht."""
        baum: ast.Module = ast.parse(Path(views.__file__).read_text(encoding="utf-8"))
        importierte_module: set[str] = set()
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Import):
                importierte_module.update(alias.name for alias in knoten.names)
            elif isinstance(knoten, ast.ImportFrom):
                importierte_module.add(knoten.module or "")

        self.assertNotIn(
            "vignetten", {modul.split(".", 1)[0] for modul in importierte_module}
        )

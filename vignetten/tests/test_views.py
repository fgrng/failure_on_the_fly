"""HTTP-Tests für den Vignetten-Editor."""

from pathlib import Path
from tempfile import TemporaryDirectory

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from simulation.models import Simulationskern
from vignetten.forms import VignetteForm
from vignetten.models import Vignette, Vignettenhistorie


_GIF_INHALT: bytes = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def _gif_upload() -> SimpleUploadedFile:
    """Erzeugt eine gültige kleine GIF-Datei für einen Formular-Upload."""
    return SimpleUploadedFile("arbeitsblatt.gif", _GIF_INHALT, content_type="image/gif")


def _autorin(username: str) -> Konto:
    """Legt ein Konto mit Zugriff auf den Vignetten-Editor an."""
    konto: Konto = get_user_model().objects.create_user(username=username)
    konto.groups.add(Group.objects.get(name="Autor:in"))
    return konto


def _vollstaendige_vignette(konto: Konto) -> Vignette:
    """Legt einen finalisierbaren Entwurf für die Koautorschaftstests an."""
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    vignette: Vignette = Vignette.objects.anlegen(konto)
    vignette.fehlermuster_beschreibung = "Stellenwerte werden einzeln gezählt."
    vignette.lernauftrag_text = "Addiere 27 und 15."
    vignette.arbeitsheft_text = "27 + 15 = 312"
    vignette.schuelerin_name = "Mia"
    vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.lehrperson_name = "Frau Weber"
    vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.fach = "Mathematik"
    vignette.thema = "Addition"
    vignette.klassenstufe = "5"
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 5
    vignette.save()
    return vignette


def _vignette_mit_eigentuemerinnen(*konten: Konto) -> Vignette:
    """Legt eine Vignette mit dem angegebenen Eigentümer-Kreis an."""
    historie: Vignettenhistorie = Vignettenhistorie.objects.create()
    historie.eigentuemerinnen.add(*konten)
    return Vignette.objects._erstellen(historie=historie)


class VignetteAnlegenViewTests(TestCase):
    """Das Anlegeformular ist die HTTP-Naht zum Vignetten-Manager."""

    def test_speichert_ueberschriebene_akteure_und_zeigt_gepinnten_kern(self) -> None:
        """Die Oberfläche legt einen Entwurf mit dem automatisch gepinnten Kern an."""
        ada: Konto = _autorin("ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:anlegen"),
            {
                "fehlermuster_beschreibung": "Zählt Stellenwerte einzeln.",
                "lernauftrag_text": "Addiere 27 und 15.",
                "arbeitsheft_bildbeschreibung": "27 + 15 = 312",
                "arbeitsheft_text": "27 + 15 = 312",
                "schuelerin_name": "Mia",
                "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
                "lehrperson_name": "Weber",
                "lehrperson_geschlecht": Vignette.Geschlecht.MAENNLICH,
                "fach": "Mathematik",
                "thema": "Addition",
                "klassenstufe": "5",
                "referenzdiagnose": "Stellenwerte werden nicht ausgerichtet.",
                "budget_typ": Vignette.BudgetTyp.SCHRITTE,
                "budget_wert": 5,
            },
        )

        vignette: Vignette = Vignette.objects.get()
        self.assertRedirects(response, reverse("vignetten:detail", args=[vignette.pk]))
        self.assertEqual(vignette.schuelerin_name, "Mia")
        self.assertEqual(vignette.lehrperson_geschlecht, Vignette.Geschlecht.MAENNLICH)
        self.assertEqual(vignette.gepinnter_kern, kern)
        self.assertEqual(list(vignette.historie.eigentuemerinnen.all()), [ada])
        detail_response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )
        self.assertContains(detail_response, f"Gepinnter Simulationskern: {kern.pk}")

    def test_formular_belegt_akteure_vor_und_bietet_keine_kernwahl(self) -> None:
        """Akteure sind als Komfort vorausgefüllt; der Kern bleibt nicht wählbar."""
        ada: Konto = _autorin("ada")
        self.client.force_login(ada)

        with patch(
            "vignetten.models.random.choice",
            side_effect=[
                ("Mia", Vignette.Geschlecht.WEIBLICH),
                ("Koch", Vignette.Geschlecht.MAENNLICH),
            ],
        ):
            response: HttpResponse = self.client.get(reverse("vignetten:anlegen"))

        self.assertContains(response, 'name="schuelerin_name" value="Mia"')
        self.assertContains(response, '<option value="weiblich" selected>')
        self.assertContains(response, 'name="lehrperson_name" value="Koch"')
        self.assertContains(response, '<option value="männlich" selected>')
        self.assertNotContains(response, 'name="gepinnter_kern"')

    def test_formular_unterbindet_die_browserseitige_wiederherstellung(self) -> None:
        """Beim Neuladen darf der Browser die vorbelegten Akteure nicht entkoppeln."""
        ada: Konto = _autorin("ada")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:anlegen"))

        self.assertContains(response, 'autocomplete="off"')


class VignetteListeViewTests(TestCase):
    """Die Liste bleibt lesbar, auch wenn eine Historie ihre Fassungen verloren hat."""

    def test_fassungslose_historie_legt_die_liste_nicht_lahm(self) -> None:
        """Eine Historie ohne Fassung wird übersprungen statt die Seite zu sprengen."""
        ada: Konto = _autorin("ada")
        belegte: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Bruchrechnung"
        )
        belegte.eigentuemerinnen.add(ada)
        Vignette.objects._erstellen(historie=belegte)
        fassungslose: Vignettenhistorie = Vignettenhistorie.objects.create()
        fassungslose.eigentuemerinnen.add(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bruchrechnung")

    def test_jede_historie_erscheint_trotz_mehrerer_fassungen_einmal(self) -> None:
        """Der Join auf die Fassungen darf die Historie nicht vervielfachen."""
        ada: Konto = _autorin("ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Bruchrechnung"
        )
        historie.eigentuemerinnen.add(ada)
        erste: Vignette = Vignette.objects._erstellen(
            historie=historie, gepinnter_kern=kern
        )
        Vignette.objects._erstellen(
            historie=historie,
            vorgaengerin=erste,
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="1/2 + 1/3 = 2/5",
            gepinnter_kern=kern,
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count("Bruchrechnung"), 1)


class VignetteDetailViewTests(TestCase):
    """Die Detailansicht zeigt den Aufgabenkontext einer sichtbaren Fassung."""

    def test_zeigt_die_eigentuemerin_der_historie(self) -> None:
        """Die Detailansicht macht den Eigentümer-Kreis der Vignette sichtbar."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "Eigentümer:innen")
        self.assertContains(response, "Eigentümer:in hinzufügen")
        self.assertContains(response, ada.username)

    def test_rendert_die_rohfelder_des_aufgabenkontexts(self) -> None:
        """Die Ansicht zeigt Lernauftrag und Arbeitsheft ohne Rahmen-Rendering."""
        ada: Konto = _autorin("ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            lernauftrag_text="Addiere 27 und 15.",
            arbeitsheft_text="27 + 15 = 312",
            arbeitsheft_bildbeschreibung="Die Zahlen stehen untereinander.",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "Addiere 27 und 15.")
        self.assertContains(response, "27 + 15 = 312")
        self.assertContains(response, "Die Zahlen stehen untereinander.")

    def test_rendert_lernauftrag_und_arbeitsheft_als_szenentext(self) -> None:
        """Markdown wirkt, Link-Syntax bleibt wörtlich, Nebenfelder bleiben roh."""
        ada: Konto = _autorin("ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            lernauftrag_text="Addiere **27** und 15.\n[Tafel](https://example.org)",
            lernauftrag_simulationshinweise="Hinweis **roh**",
            arbeitsheft_text="27 + 15\n= 312",
            arbeitsheft_bildbeschreibung="Die *Zahlen* stehen untereinander.",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "Addiere <strong>27</strong> und 15.<br>")
        self.assertContains(response, "[Tafel](https://example.org)")
        self.assertNotContains(response, 'href="https://example.org"')
        self.assertContains(response, "<p>27 + 15<br>\n= 312</p>", html=False)
        self.assertContains(response, "Hinweis **roh**")
        self.assertContains(response, "Die *Zahlen* stehen untereinander.")
        self.assertContains(response, '<div class="markdown-text')

    def test_rendert_simulationshinweise(self) -> None:
        """Die Ansicht zeigt beide Simulationshinweise in ihren Abschnitten."""
        ada: Konto = _autorin("ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            lernauftrag_simulationshinweise="Hinweis Lernauftrag",
            arbeitsheft_simulationshinweise="Hinweis Arbeitsheft",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "Hinweis Lernauftrag")
        self.assertContains(response, "Hinweis Arbeitsheft")

    def _entwurf_mit_ueberholtem_kern(self, konto: Konto) -> Vignette:
        # Überholt den gepinnten Kern durch eine finalisierte Nachfolgefassung.
        vignette: Vignette = _vollstaendige_vignette(konto)
        kern: Simulationskern = vignette.gepinnter_kern
        kern.bearbeiten().finalisieren()
        return vignette

    def test_zeigt_den_hinweis_am_entwurf_mit_ueberholtem_kern(self) -> None:
        """Der Entwurf sagt, dass der Pin überholt und trotzdem tragfähig ist."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = self._entwurf_mit_ueberholtem_kern(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "überholte Kern-Fassung gepinnt")
        self.assertContains(response, "lässt sich so finalisieren und spielen")

    def test_zeigt_keinen_hinweis_am_entwurf_mit_aktuellem_kern(self) -> None:
        """Ein aktueller Pin ist der Normalfall und bleibt unkommentiert."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = _vollstaendige_vignette(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertNotContains(response, "überholte Kern-Fassung gepinnt")

    def test_zeigt_keinen_hinweis_an_nicht_vorspulbaren_fassungen(self) -> None:
        """Finale und archivierte Fassungen sind gepinnt (ADR-0004), nicht vorspulbar."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = self._entwurf_mit_ueberholtem_kern(ada)
        vignette.finalisieren()
        self.client.force_login(ada)

        finale_antwort: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )
        self.assertNotContains(finale_antwort, "überholte Kern-Fassung gepinnt")

        vignette.archivieren()
        archivierte_antwort: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )
        self.assertNotContains(archivierte_antwort, "überholte Kern-Fassung gepinnt")

    def test_versteckt_fremde_fassung(self) -> None:
        """Detail-URLs geben keine Fassungen anderer Eigentümerinnen preis."""
        ada: Konto = _autorin("ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(grace)
        fremde_vignette: Vignette = Vignette.objects._erstellen(historie=historie)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[fremde_vignette.pk])
        )

        self.assertEqual(response.status_code, 404)


class VignetteKoautorschaftViewTests(TestCase):
    """Der Editor teilt eine Vignettenhistorie mit gleichrangigen Autorinnen."""

    def test_hinzufuegen_gibt_koautorin_listenzugriff(self) -> None:
        """Eine hinzugefügte Autorin sieht die Vignettenhistorie in ihrer Liste."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:eigentuemerin_hinzufuegen", args=[vignette.pk]),
            {"konto": grace.pk},
        )

        self.assertRedirects(response, reverse("vignetten:detail", args=[vignette.pk]))
        self.client.force_login(grace)
        self.assertContains(
            self.client.get(reverse("vignetten:liste")),
            reverse("vignetten:detail", args=[vignette.pk]),
        )

    def test_selbstentfernung_uebergibt_die_historie(self) -> None:
        """Eine Autorin kann sich bei verbleibender Ko-Autorin entfernen."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada, grace)
        self.client.force_login(ada)

        self.client.post(
            reverse("vignetten:eigentuemerin_entfernen", args=[vignette.pk, ada.pk])
        )
        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_entfernen_der_letzten_eigentuemerin_wird_verweigert(self) -> None:
        """Eine Vignettenhistorie behält ihre letzte Eigentümerin."""
        grace: Konto = _autorin("grace")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(grace)
        self.client.force_login(grace)
        self.client.post(
            reverse("vignetten:eigentuemerin_entfernen", args=[vignette.pk, grace.pk])
        )
        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(
            response,
            grace.username,
        )

    def test_koautorin_kann_einen_entwurf_bearbeiten(self) -> None:
        """Eine geteilte Vignette bleibt für beide Autorinnen bearbeitbar."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace")
        vignette: Vignette = _vollstaendige_vignette(ada)
        self.client.force_login(ada)
        self.client.post(
            reverse("vignetten:eigentuemerin_hinzufuegen", args=[vignette.pk]),
            {"konto": grace.pk},
        )
        self.client.force_login(grace)

        bearbeiten: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[vignette.pk])
        )
        self.assertEqual(bearbeiten.status_code, 200)

    def test_koautorin_kann_einen_entwurf_finalisieren(self) -> None:
        """Eine geteilte Vignette bleibt für beide Autorinnen finalisierbar."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace")
        vignette: Vignette = _vollstaendige_vignette(ada)
        self.client.force_login(ada)
        self.client.post(
            reverse("vignetten:eigentuemerin_hinzufuegen", args=[vignette.pk]),
            {"konto": grace.pk},
        )
        self.client.force_login(grace)

        finalisieren: HttpResponse = self.client.post(
            reverse("vignetten:finalisieren", args=[vignette.pk])
        )

        self.assertRedirects(
            finalisieren, reverse("vignetten:detail", args=[vignette.pk])
        )
        self.assertContains(
            self.client.get(reverse("vignetten:detail", args=[vignette.pk])),
            "Final",
        )

    def test_nur_autorinnen_oder_administration_koennen_hinzugefuegt_werden(
        self,
    ) -> None:
        """Teilen vergibt keine Rollen und akzeptiert nur berechtigte Konten."""
        ada: Konto = _autorin("ada")
        ohne_rolle: Konto = get_user_model().objects.create_user(username="linus")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:eigentuemerin_hinzufuegen", args=[vignette.pk]),
            {"konto": ohne_rolle.pk},
        )

        self.assertEqual(response.status_code, 404)
        self.client.force_login(ohne_rolle)
        self.assertEqual(self.client.get(reverse("vignetten:liste")).status_code, 403)

    def test_administration_kann_fremde_historie_uebergeben(self) -> None:
        """Die Administration kann eine fremde Autorin durch eine Nachfolgerin ablösen."""
        grace: Konto = _autorin("grace")
        ada: Konto = _autorin("ada")
        administratorin: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        vignette: Vignette = _vignette_mit_eigentuemerinnen(grace)
        self.client.force_login(administratorin)

        self.assertContains(
            self.client.get(reverse("vignetten:detail", args=[vignette.pk])),
            f'<option value="{administratorin.pk}">{administratorin.username}</option>',
            html=True,
        )
        self.client.post(
            reverse("vignetten:eigentuemerin_hinzufuegen", args=[vignette.pk]),
            {"konto": ada.pk},
        )
        response: HttpResponse = self.client.post(
            reverse("vignetten:eigentuemerin_entfernen", args=[vignette.pk, grace.pk])
        )

        self.assertRedirects(response, reverse("vignetten:detail", args=[vignette.pk]))
        self.client.force_login(grace)
        self.assertNotContains(
            self.client.get(reverse("vignetten:liste")),
            reverse("vignetten:detail", args=[vignette.pk]),
        )

    def test_nicht_eigentuemerin_loest_keinen_selbst_redirect_aus(self) -> None:
        """Eine fremde Administration bleibt bei der Vignette, wenn sie niemanden entfernt."""
        ada: Konto = _autorin("ada")
        grace: Konto = _autorin("grace")
        administratorin: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada, grace)
        self.client.force_login(administratorin)

        response: HttpResponse = self.client.post(
            reverse(
                "vignetten:eigentuemerin_entfernen",
                args=[vignette.pk, administratorin.pk],
            )
        )

        self.assertRedirects(response, reverse("vignetten:detail", args=[vignette.pk]))

    def test_eigentuemerin_hinzufuegen_ist_nur_per_post_erreichbar(self) -> None:
        """Das Hinzufügen weist GET-Anfragen ab."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada)
        self.client.force_login(ada)

        hinzufuegen: HttpResponse = self.client.get(
            reverse("vignetten:eigentuemerin_hinzufuegen", args=[vignette.pk])
        )
        self.assertEqual(hinzufuegen.status_code, 405)

    def test_eigentuemerin_entfernen_ist_nur_per_post_erreichbar(self) -> None:
        """Das Entfernen weist GET-Anfragen ab."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = _vignette_mit_eigentuemerinnen(ada)
        self.client.force_login(ada)

        entfernen: HttpResponse = self.client.get(
            reverse("vignetten:eigentuemerin_entfernen", args=[vignette.pk, ada.pk])
        )

        self.assertEqual(entfernen.status_code, 405)


class VignetteBearbeitenViewTests(TestCase):
    """Der Editor ändert ausschließlich eigene Entwürfe."""

    def setUp(self) -> None:
        """Legt einen angemeldeten Eigentümer mit offenem Entwurf an."""
        ada: Konto = _autorin("ada")
        self.historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        self.historie.eigentuemerinnen.add(ada)
        self.vignette: Vignette = Vignette.objects._erstellen(historie=self.historie)
        self.client.force_login(ada)

    def _geschlechter(self) -> dict[str, Vignette.Geschlecht]:
        """Liefert die beim Teil-POST stets mitgesendeten Pflichtfelder."""
        return {
            "schuelerin_geschlecht": self.vignette.schuelerin_geschlecht,
            "lehrperson_geschlecht": self.vignette.lehrperson_geschlecht,
        }

    def test_leeres_geschlecht_zeigt_formularfehler(self) -> None:
        """Das Leeren eines Geschlechts bleibt eine verständliche Formularmeldung."""
        response: HttpResponse = self.client.post(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
            {**self._geschlechter(), "schuelerin_geschlecht": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dieses Feld ist zwingend erforderlich.")
        self.vignette.refresh_from_db()
        self.assertEqual(
            self.vignette.schuelerin_geschlecht, Vignette.Geschlecht.WEIBLICH
        )

    def test_speichert_entwurf_mit_leeren_inhaltsfeldern(self) -> None:
        """Entwürfe bleiben beim Bearbeiten bewusst lückentolerant."""
        self.vignette.lernauftrag_text = "Wird gelöscht."
        self.vignette.save()

        response: HttpResponse = self.client.post(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
            self._geschlechter(),
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.vignette.refresh_from_db()
        self.assertEqual(self.vignette.lernauftrag_text, "")

    def test_detail_verlinkt_editor_fuer_entwurf(self) -> None:
        """Die Detailansicht bietet für einen Entwurf den Editor an."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.vignette.pk])
        )

        self.assertContains(
            response, reverse("vignetten:bearbeiten", args=[self.vignette.pk])
        )

    def test_formular_akzeptiert_datei_uploads(self) -> None:
        """Das Bearbeitungsformular überträgt Dateien als mehrteilige Formulardaten."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk])
        )

        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_formular_unterbindet_die_browserseitige_wiederherstellung(self) -> None:
        """Beim Neuladen sind die Serverwerte des Entwurfs maßgeblich, nicht die alten."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk])
        )

        self.assertContains(response, 'autocomplete="off"')

    def test_formular_zeigt_dieselbe_gliederung_wie_das_anlegeformular(self) -> None:
        """Editor und Anlegeformular teilen sich Sektionen und Abbrechen-Weg."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk])
        )

        self.assertContains(response, "Fehlermuster")
        self.assertContains(response, "Gesprächsbudget")
        self.assertContains(
            response, reverse("vignetten:detail", args=[self.vignette.pk])
        )

    def test_lagert_hochgeladenes_bild_unter_media_root_ab(self) -> None:
        """Ein Bild aus dem Entwurf wird dauerhaft unter MEDIA_ROOT gespeichert."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "arbeitsheft_bild": _gif_upload()},
            )

            self.vignette.refresh_from_db()
            self.assertTrue(
                Path(media_root, self.vignette.arbeitsheft_bild.name).is_file()
            )

    def test_lagert_hochgeladenes_lernauftrag_bild_unter_media_root_ab(self) -> None:
        """Ein Lernauftrag-Bild wird dauerhaft unter MEDIA_ROOT gespeichert."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "lernauftrag_bild": _gif_upload()},
            )

            self.vignette.refresh_from_db()
            self.assertTrue(
                Path(media_root, self.vignette.lernauftrag_bild.name).is_file()
            )

    def test_zeigt_hochgeladenes_bild_im_detail(self) -> None:
        """Die Detailansicht referenziert das hochgeladene Arbeitsheft-Bild."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/"),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "arbeitsheft_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()

            response: HttpResponse = self.client.get(
                reverse("vignetten:detail", args=[self.vignette.pk])
            )

            self.assertContains(response, self.vignette.arbeitsheft_bild.url)

    def test_zeigt_hochgeladenes_lernauftrag_bild_im_detail(self) -> None:
        """Die Detailansicht referenziert das hochgeladene Lernauftrag-Bild."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/"),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "lernauftrag_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()

            response: HttpResponse = self.client.get(
                reverse("vignetten:detail", args=[self.vignette.pk])
            )

            self.assertContains(response, self.vignette.lernauftrag_bild.url)

    def test_bildwechsel_erstellt_neue_datei_und_erhaelt_die_alte(self) -> None:
        """Die nur ergänzende Ablage überschreibt oder löscht kein Bild."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "arbeitsheft_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()
            erster_pfad: str = self.vignette.arbeitsheft_bild.name

            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "arbeitsheft_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()

            self.assertNotEqual(self.vignette.arbeitsheft_bild.name, erster_pfad)
            self.assertTrue(Path(media_root, erster_pfad).is_file())
            self.assertTrue(
                Path(media_root, self.vignette.arbeitsheft_bild.name).is_file()
            )

    def test_lernauftrag_bildwechsel_erstellt_neue_datei_und_erhaelt_die_alte(
        self,
    ) -> None:
        """Ein Wechsel des Lernauftrag-Bildes erzeugt eine neue Datei."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "lernauftrag_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()
            erster_pfad: str = self.vignette.lernauftrag_bild.name

            self.client.post(
                bearbeiten_url,
                {**self._geschlechter(), "lernauftrag_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()

            self.assertNotEqual(self.vignette.lernauftrag_bild.name, erster_pfad)
            self.assertTrue(Path(media_root, erster_pfad).is_file())
            self.assertTrue(
                Path(media_root, self.vignette.lernauftrag_bild.name).is_file()
            )

    def test_versteckt_fremden_entwurf(self) -> None:
        """Entwürfe anderer Eigentümerinnen bleiben über den Editor unsichtbar."""
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(grace)
        fremde_vignette: Vignette = Vignette.objects._erstellen(
            historie=fremde_historie
        )

        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[fremde_vignette.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_versteckt_eigene_finale_fassung(self) -> None:
        """Finale Fassungen bleiben auch für ihre Eigentümerinnen unveränderlich."""
        finale_vignette: Vignette = Vignette.objects._erstellen(
            historie=self.historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )

        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[finale_vignette.pk])
        )

        self.assertEqual(response.status_code, 404)


class VignetteAutovervollstaendigungViewTests(TestCase):
    """Die Editoren erhalten das gemeinsame Unterrichtsvokabular."""

    def test_liefert_finale_fach_und_thema_werte_dedupliziert_an_beide_editoren(
        self,
    ) -> None:
        """Entwürfe und Archiviertes erweitern den globalen Vorschlagspool nicht."""
        ada: Konto = _autorin("ada")
        eigene_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        eigene_historie.eigentuemerinnen.add(ada)
        entwurf: Vignette = Vignette.objects._erstellen(historie=eigene_historie)
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        Vignette.objects._erstellen(
            historie=fremde_historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Finaler Inhalt",
            fach="Mathematik",
            thema="Bruchrechnung",
        )
        Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Weiterer finaler Inhalt",
            fach="Mathematik",
            thema="Addition",
        )
        Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fach="Entwurf-Fach",
            thema="Entwurf-Thema",
        )
        Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Archivierter Inhalt",
            fach="Archiv-Fach",
            thema="Archiv-Thema",
        )
        self.client.force_login(ada)

        responses: tuple[HttpResponse, ...] = (
            self.client.get(reverse("vignetten:anlegen")),
            self.client.get(reverse("vignetten:bearbeiten", args=[entwurf.pk])),
        )

        for response in responses:
            self.assertCountEqual(response.context["fach_werte"], ["Mathematik"])
            self.assertCountEqual(
                response.context["thema_werte"], ["Bruchrechnung", "Addition"]
            )


class VignetteFormularSeiteTests(TestCase):
    """Anlegen und Bearbeiten teilen sich ein Formular-Template."""

    def test_geschlechter_sind_pflichtfelder(self) -> None:
        """Leere Geschlechter werden im Formular verständlich zurückgewiesen."""
        form: VignetteForm = VignetteForm(data={})

        self.assertFalse(form.is_valid())
        self.assertCountEqual(
            form.errors,
            ["schuelerin_geschlecht", "lehrperson_geschlecht"],
        )

    def test_beide_editoren_rendern_alle_formularfelder(self) -> None:
        """Das gemeinsame Template darf beim Erweitern kein Feld unterschlagen."""
        ada: Konto = _autorin("ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        entwurf: Vignette = Vignette.objects._erstellen(historie=historie)
        self.client.force_login(ada)

        responses: tuple[HttpResponse, ...] = (
            self.client.get(reverse("vignetten:anlegen")),
            self.client.get(reverse("vignetten:bearbeiten", args=[entwurf.pk])),
        )

        for response in responses:
            for feldname in VignetteForm().fields:
                self.assertContains(response, f'name="{feldname}"')


class VignetteMarkdownVorschauViewTests(TestCase):
    """Lernauftrag und Arbeitsheft bieten Markdown-Hinweis und Vorschau."""

    def setUp(self) -> None:
        """Legt einen angemeldeten Eigentümer mit Markdown im Entwurf an."""
        ada: Konto = _autorin("ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        self.vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            lernauftrag_text="Addiere **27** und 15.",
            arbeitsheft_text="27 \\* 15\n= 405",
        )
        self.client.force_login(ada)

    def test_beide_editoren_bieten_hinweis_und_umschalter_im_szenentext(self) -> None:
        """Beide Szenentextfelder holen ihre Vorschau im Profil Szenentext."""
        for url in (
            reverse("vignetten:anlegen"),
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
        ):
            response: HttpResponse = self.client.get(url)

            self.assertContains(response, ">Bearbeiten</button>", count=2)
            self.assertContains(response, ">Vorschau</button>", count=2)
            self.assertContains(
                response, f'hx-post="{reverse("texte:vorschau")}"', count=2
            )
            self.assertContains(response, '"profil": "szenentext"', count=2)
            self.assertContains(response, 'id="id_lernauftrag_text_vorschau"')
            self.assertContains(response, 'id="id_arbeitsheft_text_vorschau"')
            self.assertContains(response, "per Backslash escapen", count=2)
            self.assertNotContains(response, "[Linktext](https://…)")

    def test_felder_behalten_hilfetext_und_beschreibung(self) -> None:
        """Hilfetext und Markdown-Hinweis beschreiben das Feld gemeinsam."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk])
        )

        self.assertContains(response, 'aria-describedby="id_lernauftrag_text_helptext"')
        self.assertContains(response, 'id="id_lernauftrag_text_helptext"')
        self.assertContains(response, "allein auf einer Zeile")
        self.assertContains(response, "27 \\* 15\n= 405</textarea>")

    def test_vorschau_entspricht_der_anzeige_der_vignette(self) -> None:
        """Endpunkt und Anzeige liefern für den Arbeitsheft-Text dasselbe Rendering."""
        vorschau: HttpResponse = self.client.post(
            reverse("texte:vorschau"),
            {"profil": "szenentext", "quelle": self.vignette.arbeitsheft_text},
        )
        detail: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.vignette.pk])
        )

        fragment: str = vorschau.content.decode().strip()
        inhalt: str = fragment.removeprefix('<div class="markdown-text">')
        self.assertIn("<p>27 * 15<br>", inhalt)
        self.assertContains(
            detail, f'<div class="markdown-text aufgabenkontext-inhalt">{inhalt}'
        )


class VignetteFinalisierenViewTests(TestCase):
    """Entwürfe lassen sich mit lesbaren Fehlermeldungen finalisieren."""

    def setUp(self) -> None:
        """Legt eine eingeloggte Autorin mit vollständigem Entwurf an."""
        ada: Konto = _autorin("ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.vignette: Vignette = Vignette.objects.anlegen(ada)
        self.vignette.fehlermuster_beschreibung = "Zählt Stellenwerte einzeln."
        self.vignette.lernauftrag_text = "Addiere 27 und 15."
        self.vignette.arbeitsheft_bildbeschreibung = "27 + 15 = 312"
        self.vignette.arbeitsheft_text = "27 + 15 = 312"
        self.vignette.schuelerin_name = "Mia"
        self.vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.vignette.lehrperson_name = "Frau Weber"
        self.vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.vignette.fach = "Mathematik"
        self.vignette.thema = "Addition"
        self.vignette.klassenstufe = "5"
        self.vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
        self.vignette.budget_wert = 5
        self.vignette.save()
        self.client.force_login(ada)

    def _assert_finalisieren_zeigt_fehler(
        self, feldname: str, wert: object, fehlermeldung: str
    ) -> None:
        # Prüft eine abgelehnte Finalisierung über die sichtbare Antwort.
        setattr(self.vignette, feldname, wert)
        self.vignette.save()

        response: HttpResponse = self.client.post(
            reverse("vignetten:finalisieren", args=[self.vignette.pk]), follow=True
        )

        self.assertContains(response, fehlermeldung)

    def test_zeigt_finalisieren_und_vorspulen_aktionen(self) -> None:
        """Der Entwurf bietet seine beiden zulässigen Lebenszyklus-Aktionen an."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.assertContains(
            response,
            reverse("vignetten:finalisieren", args=[self.vignette.pk]),
        )
        self.assertContains(
            response,
            reverse("vignetten:vorspulen", args=[self.vignette.pk]),
        )

    def test_finalisiert_vollstaendigen_eigenen_entwurf(self) -> None:
        """Ein vollständiger Entwurf wird über HTTP zur finalen Fassung."""

        response: HttpResponse = self.client.post(
            reverse("vignetten:finalisieren", args=[self.vignette.pk]), follow=True
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.assertContains(response, "badge--final")

    def test_finalisieren_ist_ohne_simulationshinweise_moeglich(self) -> None:
        """Simulationshinweise sind optional und blockieren das Finalisieren nicht."""
        self.vignette.lernauftrag_simulationshinweise = ""
        self.vignette.arbeitsheft_simulationshinweise = ""
        self.vignette.save()

        response: HttpResponse = self.client.post(
            reverse("vignetten:finalisieren", args=[self.vignette.pk]), follow=True
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.assertContains(response, "badge--final")

    def test_zeigt_fehler_fuer_leeren_lernauftrag(self) -> None:
        """Ein Lernauftrag ohne Text oder Bild wird verständlich abgelehnt."""
        self._assert_finalisieren_zeigt_fehler("lernauftrag_text", "", "Lernauftrag")

    def test_zeigt_fehler_fuer_lernauftrag_bild_ohne_bildbeschreibung(self) -> None:
        """Ein Lernauftrag-Bild ohne Bildbeschreibung wird beim Finalisieren abgelehnt."""
        self.vignette.lernauftrag_bild = "vignettenbilder/auftrag.gif"
        self.vignette.lernauftrag_bildbeschreibung = ""
        self._assert_finalisieren_zeigt_fehler(
            "lernauftrag_bildbeschreibung", "", "Lernauftrag-Bild"
        )

    def test_zeigt_fehler_fuer_leeres_arbeitsheft(self) -> None:
        """Ein leeres Arbeitsheft wird verständlich benannt."""
        self._assert_finalisieren_zeigt_fehler("arbeitsheft_text", "", "Arbeitsheft")

    def test_zeigt_fehler_fuer_arbeitsheft_bild_ohne_bildbeschreibung(self) -> None:
        """Ein Arbeitsheft-Bild ohne Bildbeschreibung wird beim Finalisieren abgelehnt."""
        self.vignette.arbeitsheft_bild = "vignettenbilder/heft.gif"
        self.vignette.arbeitsheft_bildbeschreibung = ""
        self._assert_finalisieren_zeigt_fehler(
            "arbeitsheft_bildbeschreibung", "", "Arbeitsheft-Bild"
        )

    def test_zeigt_fehler_fuer_budget_null(self) -> None:
        """Ein Budget von null wird verständlich abgelehnt."""
        self._assert_finalisieren_zeigt_fehler("budget_wert", 0, "größer als 0")

    def test_zeigt_fehler_fuer_fehlenden_kern_pin(self) -> None:
        """Ohne gepinnten Kern wird verständlich abgelehnt."""
        self._assert_finalisieren_zeigt_fehler("gepinnter_kern", None, "fehlt ein")

    def test_finalisiert_einen_entwurf_mit_ueberholtem_kern_pin(self) -> None:
        """Ein überholter Pin hält das Finalisieren über HTTP nicht auf."""
        kern: Simulationskern = self.vignette.gepinnter_kern
        kern.bearbeiten().finalisieren()

        response: HttpResponse = self.client.post(
            reverse("vignetten:finalisieren", args=[self.vignette.pk]), follow=True
        )

        self.assertContains(response, "badge--final")


class VignetteNeueFassungViewTests(TestCase):
    """Finale Fassungen können über den Editor erneut als Entwurf beginnen."""

    _GEERBTE_FELDER: tuple[str, ...] = (
        "historie",
        "fehlermuster_beschreibung",
        "lernauftrag_text",
        "lernauftrag_bild",
        "lernauftrag_bildbeschreibung",
        "lernauftrag_simulationshinweise",
        "arbeitsheft_text",
        "arbeitsheft_bild",
        "arbeitsheft_bildbeschreibung",
        "arbeitsheft_simulationshinweise",
        "schuelerin_name",
        "schuelerin_geschlecht",
        "lehrperson_name",
        "lehrperson_geschlecht",
        "fach",
        "thema",
        "klassenstufe",
        "referenzdiagnose",
        "budget_typ",
        "budget_wert",
        "gepinnter_kern",
    )

    def setUp(self) -> None:
        """Legt eine eingeloggte Autorin mit finaler Vignette an."""
        self.ada: Konto = _autorin("ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.finale: Vignette = Vignette.objects.anlegen(self.ada)
        self.finale.fehlermuster_beschreibung = "Zählt Stellenwerte einzeln."
        self.finale.lernauftrag_text = "Addiere 27 und 15."
        self.finale.lernauftrag_bild = "vignettenbilder/lernauftrag-datei.gif"
        self.finale.lernauftrag_bildbeschreibung = "Arbeitsblatt mit Addition"
        self.finale.lernauftrag_simulationshinweise = "Hinweis Lernauftrag"
        self.finale.arbeitsheft_bildbeschreibung = "27 + 15 = 312"
        self.finale.arbeitsheft_text = "27 + 15 = 312"
        self.finale.arbeitsheft_bild = "vignettenbilder/finale-datei.gif"
        self.finale.arbeitsheft_simulationshinweise = "Hinweis Arbeitsheft"
        self.finale.schuelerin_name = "Mia"
        self.finale.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.finale.lehrperson_name = "Frau Weber"
        self.finale.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.finale.fach = "Mathematik"
        self.finale.thema = "Addition"
        self.finale.klassenstufe = "5"
        self.finale.referenzdiagnose = "Stellenwerte werden nicht ausgerichtet."
        self.finale.budget_typ = Vignette.BudgetTyp.SCHRITTE
        self.finale.budget_wert = 5
        self.finale.save()
        self.finale.finalisieren()
        self.client.force_login(self.ada)

    def _geerbte_werte(self, vignette: Vignette) -> dict[str, object]:
        # Bündelt den vollständigen Vererbungsvertrag für einen Vergleich.
        werte: dict[str, object] = {
            feldname: getattr(vignette, feldname) for feldname in self._GEERBTE_FELDER
        }
        werte["arbeitsheft_bild"] = vignette.arbeitsheft_bild.name
        werte["lernauftrag_bild"] = vignette.lernauftrag_bild.name
        return werte

    def test_zieht_aus_finaler_fassung_einen_entwurf_mit_geerbtem_bildpfad(
        self,
    ) -> None:
        """Re-Versionieren führt zum Folgeentwurf derselben Vignettenhistorie."""
        response: HttpResponse = self.client.post(
            reverse("vignetten:neue_fassung", args=[self.finale.pk])
        )

        entwurf: Vignette = Vignette.objects.get(vorgaengerin=self.finale)
        self.assertRedirects(response, reverse("vignetten:detail", args=[entwurf.pk]))
        self.assertEqual(entwurf.zustand, Vignette.Zustand.ENTWURF)
        self.assertEqual(self._geerbte_werte(entwurf), self._geerbte_werte(self.finale))

    def test_laesst_die_finale_fassung_unveraendert(self) -> None:
        """Re-Versionieren verändert Zustand und Bildpfad der Quelle nicht."""
        self.client.post(reverse("vignetten:neue_fassung", args=[self.finale.pk]))

        self.finale.refresh_from_db()
        self.assertEqual(
            (self.finale.zustand, self.finale.arbeitsheft_bild.name),
            (Vignette.Zustand.FINAL, "vignettenbilder/finale-datei.gif"),
        )

    def test_detail_bietet_die_neue_fassung_aktion_nur_fuer_finale_fassungen(
        self,
    ) -> None:
        """Die finale Detailansicht führt sichtbar zur Aktion Neue Fassung."""
        entwurf: Vignette = Vignette.objects.anlegen(self.ada)

        finale_response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.finale.pk])
        )
        entwurf_response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[entwurf.pk])
        )

        self.assertContains(
            finale_response,
            reverse("vignetten:neue_fassung", args=[self.finale.pk]),
        )
        self.assertNotContains(entwurf_response, "Neue Fassung")

    def test_erneute_aktion_oeffnet_den_bereits_vorhandenen_entwurf(self) -> None:
        """Ein doppelter Klick erzeugt keinen zweiten Entwurf derselben Historie."""
        vorhandener_entwurf: Vignette = self.finale.bearbeiten()

        response: HttpResponse = self.client.post(
            reverse("vignetten:neue_fassung", args=[self.finale.pk])
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[vorhandener_entwurf.pk])
        )
        self.assertEqual(
            Vignette.objects.filter(historie=self.finale.historie).count(), 2
        )

    def test_nachfolgerin_verhindert_neue_fassung_mit_fehlermeldung(self) -> None:
        """Eine ältere finale Fassung führt nicht auf eine Fehlerseite."""
        nachfolgerin: Vignette = self.finale.bearbeiten()
        nachfolgerin.finalisieren()

        response: HttpResponse = self.client.post(
            reverse("vignetten:neue_fassung", args=[self.finale.pk]), follow=True
        )

        self.assertEqual(
            response.redirect_chain,
            [(reverse("vignetten:detail", args=[self.finale.pk]), 302)],
        )
        self.assertContains(response, "Nachfolgerin")

    def test_detail_verbirgt_neue_fassung_bei_nicht_archivierter_nachfolgerin(
        self,
    ) -> None:
        """Nur die jüngste finale Fassung bietet eine neue Fassung an."""
        nachfolgerin: Vignette = self.finale.bearbeiten()
        nachfolgerin.finalisieren()

        alte_fassung: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.finale.pk])
        )
        juengste_fassung: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[nachfolgerin.pk])
        )

        self.assertNotContains(
            alte_fassung,
            reverse("vignetten:neue_fassung", args=[self.finale.pk]),
        )
        self.assertContains(
            juengste_fassung,
            reverse("vignetten:neue_fassung", args=[nachfolgerin.pk]),
        )


class VignetteArchivierenViewTests(TestCase):
    """Finale Fassungen lassen sich im Editor archivieren."""

    def test_archiviert_eigene_finale_fassung_ueber_post(self) -> None:
        """Die Archivierungs-URL ruft den Lebenszyklus nur für Eigentümer:innen auf."""
        ada: Konto = _autorin("ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        finale: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="27 + 15 = 312",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:archivieren", args=[finale.pk])
        )

        self.assertRedirects(response, reverse("vignetten:detail", args=[finale.pk]))
        finale.refresh_from_db()
        self.assertEqual(finale.zustand, Vignette.Zustand.ARCHIVIERT)

    def test_entarchiviert_eigene_archivierte_fassung_ueber_post(self) -> None:
        """Eine archivierte Fassung wird über die Gegenaktion wieder final."""
        ada: Konto = _autorin("ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        archivierte: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="27 + 15 = 312",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:entarchivieren", args=[archivierte.pk])
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[archivierte.pk])
        )
        archivierte.refresh_from_db()
        self.assertEqual(archivierte.zustand, Vignette.Zustand.FINAL)

    def test_aktionen_sind_post_only_und_fuer_fremde_historien_unsichtbar(self) -> None:
        """Jede Aktion schützt Methode und Eigentümer-Kreis an der HTTP-Naht."""
        ada: Konto = _autorin("ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        eigene_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        eigene_historie.eigentuemerinnen.add(ada)
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(grace)
        eigene_fassungen: tuple[tuple[str, Vignette], ...] = (
            (
                "finalisieren",
                Vignette.objects._erstellen(historie=eigene_historie),
            ),
            (
                "vorspulen",
                Vignette.objects._erstellen(
                    historie=Vignettenhistorie.objects.create()
                ),
            ),
            (
                "archivieren",
                Vignette.objects._erstellen(
                    historie=Vignettenhistorie.objects.create(),
                    zustand=Vignette.Zustand.FINAL,
                    finalisiert_am=timezone.now(),
                    lernauftrag_text="Lernauftrag",
                    arbeitsheft_text="Inhalt",
                ),
            ),
            (
                "entarchivieren",
                Vignette.objects._erstellen(
                    historie=Vignettenhistorie.objects.create(),
                    zustand=Vignette.Zustand.ARCHIVIERT,
                    finalisiert_am=timezone.now(),
                    lernauftrag_text="Lernauftrag",
                    arbeitsheft_text="Inhalt",
                ),
            ),
            (
                "neue_fassung",
                Vignette.objects._erstellen(
                    historie=Vignettenhistorie.objects.create(),
                    zustand=Vignette.Zustand.FINAL,
                    finalisiert_am=timezone.now(),
                    lernauftrag_text="Lernauftrag",
                    arbeitsheft_text="Inhalt",
                ),
            ),
        )
        for _, vignette in eigene_fassungen[1:]:
            vignette.historie.eigentuemerinnen.add(ada)
        fremde_finale: Vignette = Vignette.objects._erstellen(
            historie=fremde_historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Inhalt",
        )
        self.client.force_login(ada)

        for name, vignette in eigene_fassungen:
            self.assertEqual(
                self.client.get(
                    reverse(f"vignetten:{name}", args=[vignette.pk])
                ).status_code,
                405,
            )
        self.assertEqual(
            self.client.post(
                reverse("vignetten:archivieren", args=[fremde_finale.pk])
            ).status_code,
            404,
        )


class VignettenLoginTests(TestCase):
    """Alle Editor-Einstiege verlangen eine Anmeldung."""

    def test_anonyme_zugriffe_werden_zum_login_geleitet(self) -> None:
        """Liste, Anlegen und Detail sind ausschließlich eingeloggten Personen offen."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        vignette: Vignette = Vignette.objects._erstellen(historie=historie)

        urls: tuple[str, ...] = (
            reverse("vignetten:liste"),
            reverse("vignetten:anlegen"),
            reverse("vignetten:detail", args=[vignette.pk]),
            reverse("vignetten:bearbeiten", args=[vignette.pk]),
            reverse("vignetten:finalisieren", args=[vignette.pk]),
            reverse("vignetten:archivieren", args=[vignette.pk]),
            reverse("vignetten:entarchivieren", args=[vignette.pk]),
            reverse("vignetten:vorspulen", args=[vignette.pk]),
            reverse("vignetten:neue_fassung", args=[vignette.pk]),
            reverse("vignetten:reversionieren", args=[vignette.pk]),
        )
        for url in urls:
            response: HttpResponse = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/accounts/login/?next="))


class VignettenRollenTests(TestCase):
    """Der Editor schützt auch direkte URLs mit der Autorenrolle."""

    def test_teilnehmerin_erhaelt_auf_alle_editor_urls_403(self) -> None:
        """Das Verstecken in der Sidebar ist nicht die einzige Zugriffssperre."""
        teilnehmerin: Konto = get_user_model().objects.create_user(username="studi")
        self.client.force_login(teilnehmerin)

        for name in (
            "liste",
            "anlegen",
            "detail",
            "bearbeiten",
            "finalisieren",
            "archivieren",
            "entarchivieren",
            "vorspulen",
            "neue_fassung",
            "reversionieren",
        ):
            args = [] if name in {"liste", "anlegen"} else [1]
            self.assertEqual(
                self.client.get(reverse(f"vignetten:{name}", args=args)).status_code,
                403,
            )

    def test_administratorin_erreicht_den_editor(self) -> None:
        """Djangos Superuser ist der serverseitige Override."""
        administratorin: Konto = get_user_model().objects.create_user(username="linus")
        administratorin.is_superuser = True
        administratorin.save()
        self.client.force_login(administratorin)

        self.assertEqual(self.client.get(reverse("vignetten:liste")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vignetten:anlegen")).status_code, 200)

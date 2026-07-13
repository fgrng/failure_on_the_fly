"""HTTP-Tests für den Vignetten-Editor."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from simulation.models import Simulationskern
from vignetten.models import Vignette, Vignettenhistorie


_GIF_INHALT: bytes = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def _gif_upload() -> SimpleUploadedFile:
    """Erzeugt eine gültige kleine GIF-Datei für einen Formular-Upload."""
    return SimpleUploadedFile("arbeitsblatt.gif", _GIF_INHALT, content_type="image/gif")


class VignettenlisteTests(TestCase):
    """Die Liste zeigt nur Vignetten aus dem eigenen Eigentümer-Kreis."""

    def test_zeigt_eigene_historie_mit_fallback_label_und_versteckt_fremde(
        self,
    ) -> None:
        """Autor:innen sehen nur ihre Historien, auch ohne vergebenen Namen."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        eigene_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        eigene_historie.eigentuemerinnen.add(ada)
        Vignette.objects._erstellen(
            historie=eigene_historie,
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="1 + 1 = 3",
            fach="Mathematik",
            thema="Addition",
            klassenstufe="4",
        )
        neueste_fassung: Vignette = Vignette.objects._erstellen(
            historie=eigene_historie,
            fach="Mathematik",
            thema="Brüche",
            klassenstufe="5",
        )
        benannte_historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Addition mit Übertrag"
        )
        benannte_historie.eigentuemerinnen.add(ada)
        Vignette.objects._erstellen(historie=benannte_historie)
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Versteckte Vignette"
        )
        fremde_historie.eigentuemerinnen.add(grace)
        Vignette.objects._erstellen(historie=fremde_historie)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertContains(response, "Mathematik: Brüche (Klasse 5)")
        self.assertContains(
            response,
            reverse("vignetten:detail", args=[neueste_fassung.pk]),
        )
        self.assertNotContains(response, "Mathematik: Addition (Klasse 4)")
        self.assertContains(response, "Addition mit Übertrag")
        self.assertNotContains(response, "Versteckte Vignette")
        self.assertContains(response, reverse("vignetten:anlegen"))


class VignetteAnlegenViewTests(TestCase):
    """Das Anlegeformular ist die HTTP-Naht zum Vignetten-Manager."""

    def test_speichert_ueberschriebene_akteure_und_zeigt_gepinnten_kern(self) -> None:
        """Die Oberfläche legt einen Entwurf mit dem automatisch gepinnten Kern an."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:anlegen"),
            {
                "fehlermuster_beschreibung": "Zählt Stellenwerte einzeln.",
                "lernauftrag": "Addiere 27 und 15.",
                "arbeitsheft_beschreibung": "27 + 15 = 312",
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
        ada: Konto = get_user_model().objects.create_user(username="ada")
        self.client.force_login(ada)

        with patch(
            "vignetten.forms.random.choice",
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


class VignetteDetailViewTests(TestCase):
    """Die Detailansicht zeigt den Aufgabenkontext einer sichtbaren Fassung."""

    def test_rendert_die_rohfelder_des_aufgabenkontexts(self) -> None:
        """Die Ansicht zeigt Lernauftrag und Arbeitsheft ohne Rahmen-Rendering."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(ada)
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            lernauftrag="Addiere 27 und 15.",
            arbeitsheft_text="27 + 15 = 312",
            arbeitsheft_beschreibung="Die Zahlen stehen untereinander.",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "Addiere 27 und 15.")
        self.assertContains(response, "27 + 15 = 312")
        self.assertContains(response, "Die Zahlen stehen untereinander.")

    def test_versteckt_fremde_fassung(self) -> None:
        """Detail-URLs geben keine Fassungen anderer Eigentümerinnen preis."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        historie.eigentuemerinnen.add(grace)
        fremde_vignette: Vignette = Vignette.objects._erstellen(historie=historie)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[fremde_vignette.pk])
        )

        self.assertEqual(response.status_code, 404)


class VignetteBearbeitenViewTests(TestCase):
    """Der Editor ändert ausschließlich eigene Entwürfe."""

    def setUp(self) -> None:
        """Legt einen angemeldeten Eigentümer mit offenem Entwurf an."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        self.historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        self.historie.eigentuemerinnen.add(ada)
        self.vignette: Vignette = Vignette.objects._erstellen(historie=self.historie)
        self.client.force_login(ada)

    def test_speichert_entwurf_mit_leeren_inhaltsfeldern(self) -> None:
        """Entwürfe bleiben beim Bearbeiten bewusst lückentolerant."""
        self.vignette.lernauftrag = "Wird gelöscht."
        self.vignette.save()

        response: HttpResponse = self.client.post(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
            {},
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.vignette.refresh_from_db()
        self.assertEqual(self.vignette.lernauftrag, "")

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

    def test_lagert_hochgeladenes_bild_unter_media_root_ab(self) -> None:
        """Ein Bild aus dem Entwurf wird dauerhaft unter MEDIA_ROOT gespeichert."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(bearbeiten_url, {"arbeitsheft_bild": _gif_upload()})

            self.vignette.refresh_from_db()
            self.assertTrue(
                Path(media_root, self.vignette.arbeitsheft_bild.name).is_file()
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
            self.client.post(bearbeiten_url, {"arbeitsheft_bild": _gif_upload()})
            self.vignette.refresh_from_db()

            response: HttpResponse = self.client.get(
                reverse("vignetten:detail", args=[self.vignette.pk])
            )

            self.assertContains(response, self.vignette.arbeitsheft_bild.url)

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
                {"arbeitsheft_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()
            erster_pfad: str = self.vignette.arbeitsheft_bild.name

            self.client.post(
                bearbeiten_url,
                {"arbeitsheft_bild": _gif_upload()},
            )
            self.vignette.refresh_from_db()

            self.assertNotEqual(self.vignette.arbeitsheft_bild.name, erster_pfad)
            self.assertTrue(Path(media_root, erster_pfad).is_file())
            self.assertTrue(
                Path(media_root, self.vignette.arbeitsheft_bild.name).is_file()
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
            arbeitsheft_text="Bearbeitung",
        )

        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[finale_vignette.pk])
        )

        self.assertEqual(response.status_code, 404)


class VignetteFinalisierenViewTests(TestCase):
    """Entwürfe lassen sich mit lesbaren Fehlermeldungen finalisieren."""

    def setUp(self) -> None:
        """Legt eine eingeloggte Autorin mit vollständigem Entwurf an."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.vignette: Vignette = Vignette.objects.anlegen(ada)
        self.vignette.fehlermuster_beschreibung = "Zählt Stellenwerte einzeln."
        self.vignette.lernauftrag = "Addiere 27 und 15."
        self.vignette.arbeitsheft_beschreibung = "27 + 15 = 312"
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
            reverse("vignetten:finalisieren", args=[self.vignette.pk])
        )

        self.assertContains(response, fehlermeldung)

    def test_zeigt_finalisieren_aber_keine_vorspulen_aktion(self) -> None:
        """Der Entwurf bietet nur die vorgesehene Lebenszyklus-Aktion an."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.assertContains(
            response,
            reverse("vignetten:finalisieren", args=[self.vignette.pk]),
        )
        self.assertNotContains(response, "vorspulen")

    def test_finalisiert_vollstaendigen_eigenen_entwurf(self) -> None:
        """Ein vollständiger Entwurf wird über HTTP zur finalen Fassung."""

        response: HttpResponse = self.client.post(
            reverse("vignetten:finalisieren", args=[self.vignette.pk])
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[self.vignette.pk])
        )
        detail_response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.assertContains(detail_response, "Finale Fassung")

    def test_zeigt_fehler_fuer_fehlendes_pflichtfeld(self) -> None:
        """Ein fehlendes Pflichtfeld wird verständlich benannt."""
        self._assert_finalisieren_zeigt_fehler("lernauftrag", "", "lernauftrag")

    def test_zeigt_fehler_fuer_leeres_arbeitsheft(self) -> None:
        """Ein leeres Arbeitsheft wird verständlich benannt."""
        self._assert_finalisieren_zeigt_fehler(
            "arbeitsheft_text", "", "Arbeitsheft"
        )

    def test_zeigt_fehler_fuer_budget_null(self) -> None:
        """Ein Budget von null wird verständlich abgelehnt."""
        self._assert_finalisieren_zeigt_fehler("budget_wert", 0, "größer als 0")

    def test_zeigt_fehler_fuer_nicht_finalen_kern_pin(self) -> None:
        """Ein nicht finaler Kern-Pin wird verständlich abgelehnt."""
        kern: Simulationskern = self.vignette.gepinnter_kern.bearbeiten()

        self._assert_finalisieren_zeigt_fehler(
            "gepinnter_kern", kern, "nicht final"
        )

    def test_zeigt_fehler_fuer_archivierten_kern_pin(self) -> None:
        """Ein archivierter Kern-Pin wird verständlich abgelehnt."""
        kern: Simulationskern = self.vignette.gepinnter_kern
        kern.archivieren()

        self._assert_finalisieren_zeigt_fehler(
            "gepinnter_kern", kern, "archiviert"
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
        )
        for url in urls:
            response: HttpResponse = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/accounts/login/?next="))

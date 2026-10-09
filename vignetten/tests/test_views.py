"""HTTP-Tests für den Vignetten-Editor."""

from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from pytest_django.asserts import assertContains

from config.tests.aufbau import (
    finale_vignette,
    finaler_kern,
    konto_mit_rollen,
    vignetten_entwurf,
)
from config.tests.formular import submit_knoepfe
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
    return konto_mit_rollen(username, "Autor:in")


def _entwurf(konto: Konto, **felder: object) -> Vignette:
    """Legt einen Entwurf an und speichert die übergebenen Inhaltsfelder."""
    vignette: Vignette = vignetten_entwurf(konto)
    for feld, wert in felder.items():
        setattr(vignette, feld, wert)
    vignette.save()
    return vignette


def _vignette_mit_eigentuemerinnen(erste: Konto, *weitere: Konto) -> Vignette:
    """Legt einen Entwurf an, dessen Historie mehrere Eigentümerinnen teilen."""
    vignette: Vignette = vignetten_entwurf(erste)
    vignette.historie.eigentuemerinnen.add(*weitere)
    return vignette


class _Formularleser(HTMLParser):
    """Liest Formular-Attribute, Feldwerte und gewählte Optionen einer Seite."""

    def __init__(self) -> None:
        super().__init__()
        self.formulare: dict[str, dict[str, str | None]] = {}
        self.werte: dict[str, str] = {}
        self._auswahl: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute: dict[str, str | None] = dict(attrs)
        name: str | None = attribute.get("name")
        if tag == "form" and attribute.get("id"):
            self.formulare[attribute["id"] or ""] = attribute
        elif tag == "input" and name:
            self.werte[name] = attribute.get("value") or ""
        elif tag == "select" and name:
            self._auswahl = name
            self.werte[name] = ""
        elif tag == "option" and self._auswahl and "selected" in attribute:
            self.werte[self._auswahl] = attribute.get("value") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._auswahl = None


def _formular_lesen(antwort: HttpResponse) -> _Formularleser:
    """Liefert, was die Formulare der Seite tragen."""
    leser: _Formularleser = _Formularleser()
    leser.feed(antwort.content.decode())
    return leser


class VignetteAnlegenViewTests(TestCase):
    """Das Anlegeformular ist die HTTP-Naht zum Vignetten-Manager."""

    def test_speichert_ueberschriebene_akteure_und_zeigt_gepinnten_kern(self) -> None:
        """Die Formularwerte ersetzen die Vorbelegung; die Seite nennt den Kern."""
        ada: Konto = _autorin("ada")
        kern: Simulationskern = finaler_kern()
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:anlegen"),
            {
                "fehlermuster_beschreibung": "Zählt Stellenwerte einzeln.",
                "lernauftrag_text": "Addiere 27 und 15.",
                "arbeitsheft_bildbeschreibung": "27 + 15 = 312",
                "arbeitsheft_text": "27 + 15 = 312",
                "schuelerin_name": "Mia",
                "schuelerin_geschlecht": "weiblich",
                "lehrperson_name": "Weber",
                "lehrperson_geschlecht": "männlich",
                "fach": "Mathematik",
                "thema": "Addition",
                "klassenstufe": "5",
                "referenzdiagnose": "Stellenwerte werden nicht ausgerichtet.",
                "budget_typ": "schritte",
                "budget_wert": 5,
            },
            follow=True,
        )

        self.assertTemplateUsed(response, "vignetten/detail.html")
        for beschriftung, wert in (
            ("Vorname der Schüler:in", "Mia"),
            ("Lehrperson Nachname (Frau/Herr …)", "Weber"),
            ("Lehrperson Geschlecht", "Männlich"),
        ):
            self.assertContains(
                response,
                f"<div><dt>{beschriftung}</dt><dd>{wert}</dd></div>",
                html=True,
            )
        self.assertContains(response, f"Gepinnter Simulationskern: {kern.pk}")

    def test_formular_belegt_akteure_vor_und_bietet_keine_kernwahl(self) -> None:
        """Akteure sind als Komfort vorausgefüllt; der Kern bleibt nicht wählbar."""
        ada: Konto = _autorin("ada")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:anlegen"))

        werte: dict[str, str] = _formular_lesen(response).werte
        for feldname in (
            "schuelerin_name",
            "schuelerin_geschlecht",
            "lehrperson_name",
            "lehrperson_geschlecht",
        ):
            with self.subTest(feldname=feldname):
                self.assertTrue(werte[feldname])
        self.assertNotContains(response, 'name="gepinnter_kern"')


class VignetteListeViewTests(TestCase):
    """Die Liste bleibt lesbar, auch wenn eine Historie ihre Fassungen verloren hat."""

    def test_fassungslose_historie_legt_die_liste_nicht_lahm(self) -> None:
        """Eine Historie ohne Fassung wird übersprungen statt die Seite zu sprengen."""
        ada: Konto = _autorin("ada")
        finale_vignette(ada, name="Kopfrechnen")
        fassungslose: Vignettenhistorie = Vignettenhistorie.objects.create()
        fassungslose.eigentuemerinnen.add(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kopfrechnen")

    def test_jede_historie_erscheint_trotz_mehrerer_fassungen_einmal(self) -> None:
        """Der Join auf die Fassungen darf die Historie nicht vervielfachen."""
        ada: Konto = _autorin("ada")
        finale: Vignette = finale_vignette(ada, name="Kopfrechnen")
        finale.bearbeiten()
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count("Kopfrechnen"), 1)

    def test_zeilen_sind_ueber_den_namen_verlinkt(self) -> None:
        """Die Zeile nennt den Namen und führt auf die Detailseite."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = finale_vignette(ada, name="Kopfrechnen")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertContains(response, "Kopfrechnen")
        self.assertContains(response, reverse("vignetten:detail", args=[vignette.pk]))
        self.assertContains(response, "table--zeilenlink")


class VignetteDetailViewTests(TestCase):
    """Die Detailansicht zeigt den Aufgabenkontext einer sichtbaren Fassung."""

    def test_zeigt_die_eigentuemerin_der_historie(self) -> None:
        """Die Detailansicht benennt, wofür der Eigentümer-Kreis der Vignette steht."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = vignetten_entwurf(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "Wer diese Vignette sehen und bearbeiten darf")

    def test_rendert_lernauftrag_und_arbeitsheft_als_szenentext(self) -> None:
        """Markdown wirkt, Link-Syntax bleibt wörtlich, Nebenfelder bleiben roh."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = _entwurf(
            ada,
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
        vignette: Vignette = _entwurf(
            ada,
            lernauftrag_simulationshinweise="Hinweis Lernauftrag",
            arbeitsheft_simulationshinweise="Hinweis Arbeitsheft",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "Hinweis Lernauftrag")
        self.assertContains(response, "Hinweis Arbeitsheft")

    def _kern_ueberholen(self, vignette: Vignette) -> Vignette:
        # Überholt den gepinnten Kern durch eine finalisierte Nachfolgefassung.
        vignette.gepinnter_kern.bearbeiten().finalisieren()
        return vignette

    def test_zeigt_den_hinweis_am_entwurf_mit_ueberholtem_kern(self) -> None:
        """Der Entwurf sagt, dass der Pin überholt und trotzdem tragfähig ist."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = self._kern_ueberholen(vignetten_entwurf(ada))
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertContains(response, "überholte Kern-Fassung gepinnt")
        self.assertContains(response, "lässt sich so finalisieren und spielen")

    def test_zeigt_keinen_hinweis_am_entwurf_mit_aktuellem_kern(self) -> None:
        """Ein aktueller Pin ist der Normalfall und bleibt unkommentiert."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = vignetten_entwurf(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        self.assertNotContains(response, "überholte Kern-Fassung gepinnt")

    def test_zeigt_keinen_hinweis_an_nicht_vorspulbaren_fassungen(self) -> None:
        """Finale und archivierte Fassungen sind gepinnt (ADR-0004), nicht vorspulbar."""
        ada: Konto = _autorin("ada")
        vignette: Vignette = self._kern_ueberholen(finale_vignette(ada))
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
        fremde_vignette: Vignette = vignetten_entwurf(konto_mit_rollen("grace"))
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

        austritt: HttpResponse = self.client.post(
            reverse("vignetten:eigentuemerin_entfernen", args=[vignette.pk, ada.pk])
        )
        self.assertRedirects(austritt, reverse("vignetten:liste"))
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

    def test_nur_autorinnen_oder_administration_koennen_hinzugefuegt_werden(
        self,
    ) -> None:
        """Teilen vergibt keine Rollen und akzeptiert nur berechtigte Konten."""
        ada: Konto = _autorin("ada")
        ohne_rolle: Konto = konto_mit_rollen("linus")
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
        administratorin: Konto = konto_mit_rollen("linus", is_superuser=True)
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
        administratorin: Konto = konto_mit_rollen("linus", is_superuser=True)
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
        self.ada: Konto = _autorin("ada")
        self.vignette: Vignette = vignetten_entwurf(self.ada)
        self.client.force_login(self.ada)

    def _geschlechter(self) -> dict[str, Vignette.Geschlecht]:
        """Liefert die beim Teil-POST stets mitgesendeten Pflichtfelder."""
        return {
            "schuelerin_geschlecht": self.vignette.schuelerin_geschlecht,
            "lehrperson_geschlecht": self.vignette.lehrperson_geschlecht,
        }

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

    def test_bild_entfernen_leert_auch_die_bildbeschreibung(self) -> None:
        """Ohne Bild bleibt keine Bildbeschreibung für die Simulation zurück."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {
                    **self._geschlechter(),
                    "arbeitsheft_bild": _gif_upload(),
                    "arbeitsheft_bildbeschreibung": "27 + 15 = 312",
                },
            )
            self.vignette.refresh_from_db()
            self.assertEqual(
                self.vignette.arbeitsheft_bildbeschreibung, "27 + 15 = 312"
            )

            self.client.post(
                bearbeiten_url,
                {
                    **self._geschlechter(),
                    "arbeitsheft_bild-clear": "on",
                    "arbeitsheft_bildbeschreibung": "27 + 15 = 312",
                },
            )
            self.vignette.refresh_from_db()

            self.assertFalse(self.vignette.arbeitsheft_bild)
            self.assertEqual(self.vignette.arbeitsheft_bildbeschreibung, "")

    def test_rueckgaengig_vor_dem_speichern_behaelt_bild_und_beschreibung(
        self,
    ) -> None:
        """Ohne <name>-clear bleiben Bild und Bildbeschreibung erhalten."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            bearbeiten_url: str = reverse(
                "vignetten:bearbeiten", args=[self.vignette.pk]
            )
            self.client.post(
                bearbeiten_url,
                {
                    **self._geschlechter(),
                    "arbeitsheft_bild": _gif_upload(),
                    "arbeitsheft_bildbeschreibung": "27 + 15 = 312",
                },
            )
            self.vignette.refresh_from_db()
            bildname: str = self.vignette.arbeitsheft_bild.name

            # Rückgängig nimmt das Häkchen zurück und stellt die Beschreibung
            # wieder her; der Browser schickt also den alten Stand.
            self.client.post(
                bearbeiten_url,
                {
                    **self._geschlechter(),
                    "arbeitsheft_bildbeschreibung": "27 + 15 = 312",
                },
            )
            self.vignette.refresh_from_db()

            self.assertEqual(self.vignette.arbeitsheft_bild.name, bildname)
            self.assertEqual(
                self.vignette.arbeitsheft_bildbeschreibung, "27 + 15 = 312"
            )

    def test_zeigt_bildkarte_statt_eigenem_feld_bildbeschreibung(self) -> None:
        """Bild und Bildbeschreibung stehen je Teil in einem fieldset."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk])
        )

        inhalt: str = response.content.decode()
        for teil in ("lernauftrag", "arbeitsheft"):
            # Die Karte reicht vom fieldset vor dem Dateifeld bis zu seinem Ende.
            vor_dem_feld, nach_dem_feld = inhalt.split(f'name="{teil}_bild"')
            karte: str = (
                vor_dem_feld.rsplit('<fieldset class="bildkarte', 1)[1]
                + nach_dem_feld.split("</fieldset>", 1)[0]
            )
            self.assertIn(f'data-text-id="id_{teil}_text"', karte)
            self.assertIn('data-zustand="leer"', karte)
            self.assertIn(f'for="id_{teil}_bildbeschreibung"', karte)
            self.assertEqual(inhalt.count(f'for="id_{teil}_bildbeschreibung"'), 1)

    def test_markiert_datei_ohne_bild_als_fehler(self) -> None:
        """Eine Datei, die kein Bild ist, zeigt die Karte rot mit Meldung."""
        response: HttpResponse = self.client.post(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
            {
                **self._geschlechter(),
                "lernauftrag_bild": SimpleUploadedFile(
                    "notizen.txt", b"kein Bild", content_type="text/plain"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-zustand="fehler"')
        self.assertContains(response, "notizen.txt")

    def test_zeigt_gespeichertes_bild_als_vorschau_statt_als_pfad(self) -> None:
        """Das Bildfeld zeigt das vorhandene Bild, nicht Djangos »Derzeit:«-Zeile."""
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

            response: HttpResponse = self.client.get(bearbeiten_url)

            self.assertContains(
                response, f'data-gespeichert="{self.vignette.lernauftrag_bild.url}"'
            )
            self.assertContains(response, 'name="lernauftrag_bild-clear"')
            self.assertNotContains(
                response, f'href="{self.vignette.lernauftrag_bild.url}"'
            )

    def test_nennt_nach_formularfehler_die_verlorene_datei(self) -> None:
        """Ein Upload geht beim erneuten Anzeigen verloren und wird deshalb genannt."""
        response: HttpResponse = self.client.post(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
            {"schuelerin_geschlecht": "", "arbeitsheft_bild": _gif_upload()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "arbeitsblatt.gif")

    def test_versteckt_fremden_entwurf(self) -> None:
        """Entwürfe anderer Eigentümerinnen bleiben über den Editor unsichtbar."""
        fremde_vignette: Vignette = vignetten_entwurf(konto_mit_rollen("grace"))

        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[fremde_vignette.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_versteckt_eigene_finale_fassung(self) -> None:
        """Finale Fassungen bleiben auch für ihre Eigentümerinnen unveränderlich."""
        finale: Vignette = finale_vignette(self.ada)

        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[finale.pk])
        )

        self.assertEqual(response.status_code, 404)


def _angemeldeter_entwurf(client: Client) -> Vignette:
    """Meldet eine Autorin an und liefert ihren Entwurf."""
    ada: Konto = _autorin("ada")
    client.force_login(ada)
    return vignetten_entwurf(ada)


def _geschlechter(vignette: Vignette) -> dict[str, str]:
    """Liefert die bei jedem Speichern mitgesendeten Pflichtfelder."""
    return {
        "schuelerin_geschlecht": vignette.schuelerin_geschlecht,
        "lehrperson_geschlecht": vignette.lehrperson_geschlecht,
    }


@pytest.mark.django_db
@pytest.mark.parametrize("feld", ["schuelerin_geschlecht", "lehrperson_geschlecht"])
def test_leeres_geschlecht_zeigt_formularfehler(client: Client, feld: str) -> None:
    """Das Leeren eines Geschlechts bleibt eine verständliche Formularmeldung."""

    vignette: Vignette = _angemeldeter_entwurf(client)
    vorher: str = getattr(vignette, feld)

    response: HttpResponse = client.post(
        reverse("vignetten:bearbeiten", args=[vignette.pk]),
        {**_geschlechter(vignette), feld: ""},
    )

    assertContains(response, "Dieses Feld ist zwingend erforderlich.")
    vignette.refresh_from_db()
    assert getattr(vignette, feld) == vorher


@pytest.mark.django_db
@pytest.mark.parametrize("teil", ["lernauftrag", "arbeitsheft"])
def test_zeigt_hochgeladenes_bild_im_detail(client: Client, teil: str) -> None:
    """Nach dem Upload referenziert die Detailansicht das Bild des Teils."""

    vignette: Vignette = _angemeldeter_entwurf(client)
    with (
        TemporaryDirectory() as media_root,
        override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/"),
    ):
        client.post(
            reverse("vignetten:bearbeiten", args=[vignette.pk]),
            {**_geschlechter(vignette), f"{teil}_bild": _gif_upload()},
        )
        vignette.refresh_from_db()

        response: HttpResponse = client.get(
            reverse("vignetten:detail", args=[vignette.pk])
        )

        assertContains(response, getattr(vignette, f"{teil}_bild").url)


@pytest.mark.django_db
@pytest.mark.parametrize("teil", ["lernauftrag", "arbeitsheft"])
def test_bildwechsel_erstellt_neue_datei_und_erhaelt_die_alte(
    client: Client, teil: str
) -> None:
    """Die nur ergänzende Ablage überschreibt oder löscht kein Bild."""

    vignette: Vignette = _angemeldeter_entwurf(client)
    bearbeiten_url: str = reverse("vignetten:bearbeiten", args=[vignette.pk])
    with (
        TemporaryDirectory() as media_root,
        override_settings(MEDIA_ROOT=media_root),
    ):
        client.post(
            bearbeiten_url, {**_geschlechter(vignette), f"{teil}_bild": _gif_upload()}
        )
        vignette.refresh_from_db()
        erster_pfad: str = getattr(vignette, f"{teil}_bild").name

        client.post(
            bearbeiten_url, {**_geschlechter(vignette), f"{teil}_bild": _gif_upload()}
        )
        vignette.refresh_from_db()

        zweiter_pfad: str = getattr(vignette, f"{teil}_bild").name
        assert zweiter_pfad != erster_pfad
        assert Path(media_root, erster_pfad).is_file()
        assert Path(media_root, zweiter_pfad).is_file()


class VignetteAutovervollstaendigungViewTests(TestCase):
    """Die Editoren erhalten das gemeinsame Unterrichtsvokabular."""

    def test_liefert_finale_fach_und_thema_werte_dedupliziert_an_beide_editoren(
        self,
    ) -> None:
        """Entwürfe und Archiviertes erweitern den globalen Vorschlagspool nicht."""
        ada: Konto = _autorin("ada")
        entwurf: Vignette = vignetten_entwurf(ada)
        finale_vignette(
            konto_mit_rollen("grace"), fach="Mathematik", thema="Bruchrechnung"
        )
        finale_vignette(ada, fach="Mathematik", thema="Addition")
        _entwurf(ada, fach="Entwurf-Fach", thema="Entwurf-Thema")
        finale_vignette(ada, fach="Archiv-Fach", thema="Archiv-Thema").archivieren()
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

    def test_formular_unterbindet_die_browserseitige_wiederherstellung(self) -> None:
        """Beim Neuladen darf der Browser keine alten Werte in die Felder tragen."""
        ada: Konto = _autorin("ada")
        entwurf: Vignette = vignetten_entwurf(ada)
        self.client.force_login(ada)

        for url in (
            reverse("vignetten:anlegen"),
            reverse("vignetten:bearbeiten", args=[entwurf.pk]),
        ):
            with self.subTest(url=url):
                response: HttpResponse = self.client.get(url)
                formular: dict[str, str | None] = _formular_lesen(response).formulare[
                    "vignette-formular"
                ]
                self.assertEqual(formular.get("autocomplete"), "off")

    def test_beide_editoren_rendern_alle_formularfelder(self) -> None:
        """Das gemeinsame Template darf beim Erweitern kein Feld unterschlagen."""
        ada: Konto = _autorin("ada")
        entwurf: Vignette = vignetten_entwurf(ada)
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
        self.vignette: Vignette = _entwurf(
            ada,
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


_GEKOPPELTE_BESCHRIFTUNGEN: tuple[str, ...] = (
    "Fehlermuster-Beschreibung",
    "Lernauftrag-Text",
    "Lernauftrag-Simulationshinweise (optional)",
    "Arbeitsheft-Text",
    "Arbeitsheft-Simulationshinweise (optional)",
    "Vorname der Schüler:in",
    "Budget-Typ",
    "Budget-Wert",
)


class VignetteFeldbeschriftungenTests(TestCase):
    """Formular und Detailansicht schreiben die Beschriftungen gekoppelt (#314)."""

    def setUp(self) -> None:
        """Legt einen eigenen Entwurf mit Bildern an."""
        self.ada: Konto = _autorin("ada")
        self.entwurf: Vignette = _entwurf(
            self.ada,
            lernauftrag_bild="vignettenbilder/auftrag.gif",
            arbeitsheft_bild="vignettenbilder/heft.gif",
        )
        self.client.force_login(self.ada)

    def test_formulare_zeigen_gekoppelte_beschriftungen(self) -> None:
        """Anlegen und Bearbeiten nennen die Felder wie GLOSSARY.md."""
        for url in (
            reverse("vignetten:anlegen"),
            reverse("vignetten:bearbeiten", args=[self.entwurf.pk]),
        ):
            response: HttpResponse = self.client.get(url)
            for beschriftung in _GEKOPPELTE_BESCHRIFTUNGEN:
                self.assertContains(response, beschriftung)
            for teil in ("Lernauftrag", "Arbeitsheft"):
                self.assertContains(response, f"<legend>{teil}-Bild</legend>")
                self.assertContains(response, f"{teil}-Bildbeschreibung</label>")

    def test_detail_zeigt_dieselben_beschriftungen(self) -> None:
        """Die Detailansicht nutzt die Beschriftungen des Formulars."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.entwurf.pk])
        )

        for beschriftung in (
            *_GEKOPPELTE_BESCHRIFTUNGEN,
            "Lernauftrag-Bildbeschreibung",
            "Arbeitsheft-Bildbeschreibung",
        ):
            self.assertContains(response, beschriftung)


class VignetteLangeTexteViewTests(TestCase):
    """Große Texte stehen im Formular zum Lesen und öffnen sich einzeln (#315)."""

    _TEXTE: tuple[str, ...] = (
        "lernauftrag_text",
        "lernauftrag_simulationshinweise",
        "arbeitsheft_text",
        "arbeitsheft_simulationshinweise",
        "fehlermuster_beschreibung",
        "referenzdiagnose",
    )

    def setUp(self) -> None:
        """Legt einen angemeldeten Eigentümer mit teils gefülltem Entwurf an."""
        ada: Konto = _autorin("ada")
        self.vignette: Vignette = _entwurf(
            ada,
            lernauftrag_text="Addiere **27** und 15.",
            fehlermuster_beschreibung="Zählt **Stellen**\neinzeln.",
        )
        self.client.force_login(ada)

    def test_texte_erscheinen_gerendert_mit_bearbeiten_oder_text_schreiben(
        self,
    ) -> None:
        """Markdown wird gerendert, Klartext bleibt wörtlich, leere laden ein."""
        response: HttpResponse = self.client.get(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk])
        )

        self.assertContains(response, "Addiere <strong>27</strong> und 15.")
        self.assertContains(response, "<p>Zählt **Stellen**<br>einzeln.</p>")
        self.assertContains(
            response, 'page-field--wide markdown-lesefeld"', count=len(self._TEXTE)
        )
        self.assertContains(response, "Noch kein Text", count=4)
        self.assertContains(response, ">Text schreiben</button>", count=4)
        self.assertContains(response, ">Bearbeiten</button>", count=2 + 2)
        self.assertNotContains(response, 'id="id_referenzdiagnose_vorschau"')

    def test_anlegen_zeigt_nur_leere_texte(self) -> None:
        """Beim Anlegen gibt es noch nichts zu lesen, jeder Text lädt ein."""
        response: HttpResponse = self.client.get(reverse("vignetten:anlegen"))

        self.assertContains(
            response, ">Text schreiben</button>", count=len(self._TEXTE)
        )

    def test_jeder_speichern_knopf_speichert_die_ganze_vignette(self) -> None:
        """Alle Speichern-Knöpfe senden dasselbe Formular mit allen Feldern."""
        for url in (
            reverse("vignetten:anlegen"),
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
        ):
            response: HttpResponse = self.client.get(url)

            speichern: list[str | None] = [
                formular
                for beschriftung, formular in submit_knoepfe(response)
                if beschriftung.endswith(("speichern", "Speichern", "anlegen"))
            ]
            self.assertEqual(len(speichern), len(self._TEXTE) + 1)
            self.assertEqual(set(speichern), {"vignette-formular"})

        response = self.client.post(
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
            {
                "lernauftrag_text": "Neuer Lernauftrag",
                "referenzdiagnose": "Neue Diagnose",
                "schuelerin_geschlecht": self.vignette.schuelerin_geschlecht,
                "lehrperson_geschlecht": self.vignette.lehrperson_geschlecht,
                "fach": "Deutsch",
            },
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[self.vignette.pk])
        )
        self.vignette.refresh_from_db()
        self.assertEqual(
            (
                self.vignette.lernauftrag_text,
                self.vignette.referenzdiagnose,
                self.vignette.fehlermuster_beschreibung,
                self.vignette.fach,
            ),
            ("Neuer Lernauftrag", "Neue Diagnose", "", "Deutsch"),
        )

    def test_seite_warnt_vor_dem_verlassen_mit_ungespeicherten_aenderungen(
        self,
    ) -> None:
        """Das Formular meldet sich für die Verlassen-Warnung an."""
        for url in (
            reverse("vignetten:anlegen"),
            reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
        ):
            response: HttpResponse = self.client.get(url)

            self.assertContains(response, "js/ungespeichert.js")
            self.assertContains(response, 'id="vignette-formular"')
            self.assertContains(response, "data-ungespeichert-warnen")


class VignetteFinalisierenViewTests(TestCase):
    """Entwürfe lassen sich mit lesbaren Fehlermeldungen finalisieren."""

    def setUp(self) -> None:
        """Legt eine eingeloggte Autorin mit vollständigem Entwurf an."""
        ada: Konto = _autorin("ada")
        self.vignette: Vignette = _entwurf(
            ada,
            fehlermuster_beschreibung="Zählt Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            arbeitsheft_bildbeschreibung="27 + 15 = 312",
            arbeitsheft_text="27 + 15 = 312",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Frau Weber",
            lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=5,
        )
        self.client.force_login(ada)

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

    def test_nennt_fehlende_pflichtfelder_mit_ihrer_beschriftung(self) -> None:
        """Die Meldung nutzt die Beschriftungen des Formulars, keine Feldnamen."""
        self.vignette.schuelerin_name = ""
        self.vignette.fehlermuster_beschreibung = ""
        self.vignette.save()

        response: HttpResponse = self.client.post(
            reverse("vignetten:finalisieren", args=[self.vignette.pk]), follow=True
        )

        self.assertContains(
            response,
            "Zum Finalisieren fehlen: Fehlermuster-Beschreibung, Vorname der Schüler:in.",
        )


class VignetteNeueFassungViewTests(TestCase):
    """Finale Fassungen können über den Editor erneut als Entwurf beginnen."""

    def setUp(self) -> None:
        """Legt eine eingeloggte Autorin mit finaler Vignette an."""
        self.ada: Konto = _autorin("ada")
        self.finale: Vignette = finale_vignette(
            self.ada, fehlermuster_beschreibung="Zählt Stellenwerte einzeln."
        )
        self.client.force_login(self.ada)

    def test_zieht_aus_finaler_fassung_einen_entwurf_mit_geerbtem_bildpfad(
        self,
    ) -> None:
        """Neue Fassung führt auf die Detailseite eines Entwurfs mit dem Inhalt."""
        response: HttpResponse = self.client.post(
            reverse("vignetten:neue_fassung", args=[self.finale.pk]), follow=True
        )

        self.assertTemplateUsed(response, "vignetten/detail.html")
        self.assertContains(
            response, '<span class="badge badge--draft">Entwurf</span>', html=True
        )
        self.assertContains(response, "Zählt Stellenwerte einzeln.")

    def test_detail_bietet_die_neue_fassung_aktion_nur_fuer_finale_fassungen(
        self,
    ) -> None:
        """Die finale Detailansicht führt sichtbar zur Aktion Neue Fassung."""
        entwurf: Vignette = vignetten_entwurf(self.ada)

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
        """Nach dem Archivieren zeigt die Detailseite den Zustand und die Gegenaktion."""
        ada: Konto = _autorin("ada")
        finale: Vignette = finale_vignette(ada)
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:archivieren", args=[finale.pk]), follow=True
        )

        self.assertRedirects(response, reverse("vignetten:detail", args=[finale.pk]))
        self.assertContains(
            response, '<span class="badge badge--archived">Archiviert</span>', html=True
        )
        self.assertIn(
            "Entarchivieren", [knopf for knopf, _ in submit_knoepfe(response)]
        )

    def test_entarchiviert_eigene_archivierte_fassung_ueber_post(self) -> None:
        """Eine archivierte Fassung wird über die Gegenaktion wieder final."""
        ada: Konto = _autorin("ada")
        archivierte: Vignette = finale_vignette(ada)
        archivierte.archivieren()
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("vignetten:entarchivieren", args=[archivierte.pk]), follow=True
        )

        self.assertRedirects(
            response, reverse("vignetten:detail", args=[archivierte.pk])
        )
        self.assertContains(
            response, '<span class="badge badge--final">Final</span>', html=True
        )
        self.assertIn("Archivieren", [knopf for knopf, _ in submit_knoepfe(response)])

    def test_aktionen_sind_post_only_und_fuer_fremde_historien_unsichtbar(self) -> None:
        """Jede Aktion schützt Methode und Eigentümer-Kreis an der HTTP-Naht."""
        ada: Konto = _autorin("ada")
        archivierte: Vignette = finale_vignette(ada)
        archivierte.archivieren()
        eigene_fassungen: tuple[tuple[str, Vignette], ...] = (
            ("finalisieren", vignetten_entwurf(ada)),
            ("vorspulen", vignetten_entwurf(ada)),
            ("archivieren", finale_vignette(ada)),
            ("entarchivieren", archivierte),
            ("neue_fassung", finale_vignette(ada)),
        )
        fremde_finale: Vignette = finale_vignette(konto_mit_rollen("grace"))
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
        vignette: Vignette = vignetten_entwurf(_autorin("ada"))

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
        )
        for url in urls:
            response: HttpResponse = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/accounts/login/?next="))


class VignettenRollenTests(TestCase):
    """Der Editor schützt auch direkte URLs mit der Autorenrolle."""

    def test_teilnehmerin_erhaelt_auf_alle_editor_urls_403(self) -> None:
        """Das Verstecken in der Sidebar ist nicht die einzige Zugriffssperre."""
        teilnehmerin: Konto = konto_mit_rollen("studi")
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
        ):
            args = [] if name in {"liste", "anlegen"} else [1]
            self.assertEqual(
                self.client.get(reverse(f"vignetten:{name}", args=args)).status_code,
                403,
            )

    def test_administratorin_erreicht_den_editor(self) -> None:
        """Djangos Superuser ist der serverseitige Override."""
        administratorin: Konto = konto_mit_rollen("linus", is_superuser=True)
        self.client.force_login(administratorin)

        self.assertEqual(self.client.get(reverse("vignetten:liste")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vignetten:anlegen")).status_code, 200)

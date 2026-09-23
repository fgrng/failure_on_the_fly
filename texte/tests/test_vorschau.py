"""HTTP-Tests für den Vorschau-Endpunkt der Markdown-Texte."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto


class VorschauTests(TestCase):
    """Der Endpunkt rendert je Profil und steht nur Autor:innen und Forschenden offen."""

    def _konto(self, name: str, *rollen: str) -> Konto:
        # Legt ein angemeldetes Konto mit den genannten Rollen an.

        konto: Konto = get_user_model().objects.create_user(username=name)
        for rolle in rollen:
            konto.groups.add(Group.objects.get(name=rolle))
        self.client.force_login(konto)
        return konto

    def _vorschau(self, profil: str, quelle: str) -> HttpResponse:
        return self.client.post(
            reverse("texte:vorschau"), {"profil": profil, "quelle": quelle}
        )

    def test_informationstext_rendert_links_im_eigenen_container(self) -> None:
        """Das Fragment entspricht dem Rendering der Teilnahmeseite."""

        self._konto("ada", "Forschende:r")

        antwort: HttpResponse = self._vorschau(
            "informationstext", "# Zweck\n**fett** [Info](https://example.org)"
        )

        self.assertEqual(antwort.status_code, 200)
        self.assertContains(antwort, '<div class="markdown-text">')
        self.assertContains(antwort, "<h3>Zweck</h3>")
        self.assertContains(antwort, "<strong>fett</strong>")
        self.assertContains(antwort, 'href="https://example.org" target="_blank"')

    def test_szenentext_laesst_link_syntax_woertlich_stehen(self) -> None:
        """Im Szenentext bleibt ein Link Text."""

        self._konto("grace", "Autor:in")

        antwort: HttpResponse = self._vorschau(
            "szenentext", "*kursiv* [Info](https://example.org)"
        )

        self.assertEqual(antwort.status_code, 200)
        self.assertContains(antwort, "<em>kursiv</em>")
        self.assertContains(antwort, "[Info](https://example.org)")
        self.assertNotContains(antwort, "<a ")

    def test_unbekanntes_profil_wird_abgewiesen(self) -> None:
        """Ohne gültiges Profil gibt es kein Fragment."""

        self._konto("ada", "Forschende:r")

        self.assertEqual(self._vorschau("roh", "text").status_code, 400)

    def test_nicht_angemeldete_erhalten_kein_fragment(self) -> None:
        """Der Endpunkt ist kein offener Renderdienst."""

        antwort: HttpResponse = self._vorschau("informationstext", "**fett**")

        self.assertEqual(antwort.status_code, 302)
        self.assertNotContains(antwort, "<strong>", status_code=302)

    def test_konto_ohne_passende_rolle_erhaelt_403(self) -> None:
        """Weder rollenlose Konten noch Ausbilder:innen rendern Vorschauen."""

        self._konto("linus")
        self.assertEqual(self._vorschau("szenentext", "x").status_code, 403)

        self._konto("barbara", "Ausbilder:in")
        self.assertEqual(self._vorschau("szenentext", "x").status_code, 403)

    def test_administration_darf_vorschauen(self) -> None:
        """Die Administration erbt beide Rollen."""

        admin: Konto = get_user_model().objects.create_superuser(username="root")
        self.client.force_login(admin)

        self.assertEqual(self._vorschau("szenentext", "x").status_code, 200)

    def test_get_wird_abgewiesen(self) -> None:
        """Die Quelle kommt im Formularkörper, nicht in der URL."""

        self._konto("ada", "Forschende:r")

        antwort: HttpResponse = self.client.get(reverse("texte:vorschau"))

        self.assertEqual(antwort.status_code, 405)

"""HTTP-Tests der blauen Seite für Modell-Konfigurationen."""

import re
from collections.abc import Callable
from unittest.mock import Mock, patch

import httpx
from django.db.models import QuerySet
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from config.tests.aufbau import erklaerte, konto_mit_rollen
from config.tests.formular import submit_knoepfe
from simulation.forms import ModellKonfigurationForm
from simulation.models import (
    AktiveModellKonfiguration,
    Anbieter,
    ModellKonfiguration,
    Verwendung,
)
from simulation.modellverzeichnis import Naht

TOKEN: str = "sk-or-v1-geheimnis-wxyz"


def _openrouter(sprachmodell: str, token: str = TOKEN) -> ModellKonfiguration:
    """Legt eine gültige Konfiguration an, wie sie die Seite auflistet."""
    return ModellKonfiguration.objects.create(
        bezeichnung=f"Bezeichnung {sprachmodell}",
        anbieter=Anbieter.OPENROUTER,
        sprachmodell=sprachmodell,
        anbieter_token=token,
    )


def _aktivieren_url(konfiguration: ModellKonfiguration, verwendung: str) -> str:
    """Liefert die Route, die eine Verwendung auf die Konfiguration richtet."""
    return reverse(
        "simulation:modell_konfiguration_aktivieren",
        args=[konfiguration.pk, verwendung],
    )


def _anlegedaten(**werte: object) -> dict[str, object]:
    """Liefert einen gültigen Formularbeutel, geändert um die Testwerte."""
    return {
        "bezeichnung": "Opus für die Schüler:in",
        "anbieter": Anbieter.OPENROUTER,
        "sprachmodell": "openrouter/anthropic/claude-opus-4-8",
        "anbieter_basis_url": "",
        "anbieter_token": TOKEN,
        "parameter": '{"temperature": 0.2}',
        **werte,
    }


def _erklaeren_url(konfiguration: ModellKonfiguration) -> str:
    """Liefert die Route, die an der Konfiguration die Erklärung abgibt."""
    return reverse("simulation:modell_konfiguration_erklaeren", args=[konfiguration.pk])


class ModellKonfigurationRollenTests(TestCase):
    """Die Betriebseinstellungen der Instanz hängen an der Administrationsrolle."""

    def test_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Eine Autorin ohne Administrationsrolle darf die Seite nicht öffnen."""
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertEqual(response.status_code, 403)

    def test_weist_nicht_angemeldetes_konto_ab(self) -> None:
        """Auch anonyme Anfragen erhalten die geforderte Zugriffsverweigerung."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertEqual(response.status_code, 403)

    def test_editor_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Den Editor öffnet und nutzt nur die Administration."""
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

        for response in (
            self.client.get(reverse("simulation:modell_konfiguration_neu")),
            self.client.post(
                reverse("simulation:modell_konfiguration_neu"), _anlegedaten()
            ),
        ):
            self.assertEqual(response.status_code, 403)
        self.assertFalse(ModellKonfiguration.objects.exists())

    def test_editor_weist_nicht_angemeldetes_konto_ab(self) -> None:
        """Ohne Anmeldung legt niemand eine Konfiguration an."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"), _anlegedaten()
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ModellKonfiguration.objects.exists())

    def test_aktivieren_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Auch die Aktivieren-Geste bleibt der Administration vorbehalten."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

        response: HttpResponse = self.client.post(
            _aktivieren_url(konfiguration, Verwendung.BEWERTER)
        )

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(ModellKonfiguration.objects.aktive(Verwendung.BEWERTER))

    def test_aktivieren_weist_nicht_angemeldetes_konto_ab(self) -> None:
        """Ohne Anmeldung schaltet niemand eine Verwendung um."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")

        response: HttpResponse = self.client.post(
            _aktivieren_url(konfiguration, Verwendung.SCHUELERIN)
        )

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN))

    def test_erklaeren_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Nur die Administration gibt eine Zero-Retention-Erklärung ab."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")
        self.client.force_login(konto_mit_rollen("ada", "Autor:in", "Forschende:r"))

        response: HttpResponse = self.client.post(
            _erklaeren_url(konfiguration), {"zero_retention_beleg": "AVV"}
        )

        self.assertEqual(response.status_code, 403)
        konfiguration.refresh_from_db()
        self.assertFalse(konfiguration.zero_retention_erklaert)

    def test_erklaeren_weist_nicht_angemeldetes_konto_ab(self) -> None:
        """Ohne Anmeldung erklärt niemand eine Zusage."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")

        response: HttpResponse = self.client.post(
            _erklaeren_url(konfiguration), {"zero_retention_beleg": "AVV"}
        )

        self.assertEqual(response.status_code, 403)
        konfiguration.refresh_from_db()
        self.assertFalse(konfiguration.zero_retention_erklaert)


class ZweiFassungenTestCase(TestCase):
    """Zwei angelegte Fassungen, die ältere aktiv, als Administratorin gesehen."""

    def setUp(self) -> None:
        """Legt zwei erklärte Konfigurationen an und aktiviert die ältere."""
        self.aeltere: ModellKonfiguration = erklaerte(
            _openrouter("openrouter/altes-modell")
        )
        self.neuere: ModellKonfiguration = erklaerte(
            _openrouter("openrouter/neues-modell")
        )
        ModellKonfiguration.objects.aktivieren(self.aeltere, Verwendung.SCHUELERIN)
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))


class ModellKonfigurationListeTests(ZweiFassungenTestCase):
    """Die Liste zeigt alle je angelegten Fassungen und die aktive."""

    def test_listet_alle_je_angelegten_konfigurationen(self) -> None:
        """Auch überholte Fassungen bleiben sichtbar."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "openrouter/altes-modell")
        self.assertContains(response, "openrouter/neues-modell")

    def test_zeigt_die_bezeichnung_jeder_konfiguration(self) -> None:
        """Man erkennt eine Fassung an ihrem Namen, nicht nur am Modell."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "Bezeichnung openrouter/altes-modell")
        self.assertContains(response, "Bezeichnung openrouter/neues-modell")

    def test_nennt_die_kuerzel_der_verwendungen_je_zeile(self) -> None:
        """Die Tabelle sagt, für welche Verwendungen eine Zeile gerade aktiv ist."""
        ModellKonfiguration.objects.aktivieren(self.aeltere, Verwendung.BEWERTER)
        ModellKonfiguration.objects.aktivieren(self.neuere, Verwendung.LEHRPERSON)

        seite: str = self.client.get(
            reverse("simulation:modell_konfiguration")
        ).content.decode()
        kuerzel: dict[str, list[str]] = {
            re.findall(r"<strong>(.*?)</strong>", zeile)[0]: re.findall(
                r'<abbr class="verwendungskuerzel" title="[^"]+">(.)</abbr>', zeile
            )
            for zeile in re.findall(
                r"<tr class=\"modell-konfigurationen__zeile.*?</tr>", seite, re.S
            )
        }

        self.assertEqual(
            kuerzel,
            {
                "Bezeichnung openrouter/altes-modell": ["S", "B"],
                "Bezeichnung openrouter/neues-modell": ["L"],
            },
        )

    def test_nennt_den_anbieter_je_zeile(self) -> None:
        """Gleichnamige Fassungen unterscheidet auch der Anbieter."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "<td>OpenRouter</td>", count=2, html=True)

    def test_nennt_das_anlagedatum(self) -> None:
        """Gleichnamige Fassungen unterscheidet das Anlagedatum."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(
            response, timezone.localtime(self.neuere.angelegt_am).strftime("%d.%m.%Y")
        )

    def test_zeigt_fuer_den_bestand_ohne_anlagedatum_einen_strich(self) -> None:
        """Ein fehlendes Datum wird nicht erfunden."""
        # Bestand vor dem Anlagedatum; die Sperre des QuerySets umgeht der Test.
        QuerySet.update(ModellKonfiguration.objects.all(), angelegt_am=None)

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "<td>—</td>", count=2, html=True)
        self.assertContains(response, "angelegt —")


class ModellKonfigurationDetailTests(ZweiFassungenTestCase):
    """Rechts steht das Detail der gewählten Zeile."""

    def test_zeigt_ohne_wahl_die_konfiguration_der_schuelerin(self) -> None:
        """Ohne Angabe beginnt die Seite bei dem, was Teilnehmende spielen."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, f"Nr. {self.aeltere.pk} ·")
        self.assertNotContains(response, f"Nr. {self.neuere.pk} ·")

    def test_zeigt_die_gewaehlte_zeile(self) -> None:
        """Die Zeile der Tabelle führt über die Anfrage ins Detail."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration"),
            {"konfiguration": self.neuere.pk},
        )

        self.assertContains(response, f"Nr. {self.neuere.pk} ·")
        self.assertNotContains(response, f"Nr. {self.aeltere.pk} ·")
        self.assertContains(response, f'href="?konfiguration={self.aeltere.pk}"')

    def test_faellt_bei_unbekannter_wahl_auf_die_schuelerin_zurueck(self) -> None:
        """Eine veraltete oder unsinnige Angabe führt nicht auf eine Fehlerseite."""
        for genannt in ("999", "abc"):
            response: HttpResponse = self.client.get(
                reverse("simulation:modell_konfiguration"), {"konfiguration": genannt}
            )

            self.assertContains(response, f"Nr. {self.aeltere.pk} ·")

    def test_zeigt_ohne_aktive_schuelerin_die_neueste(self) -> None:
        """Solange nichts aktiv ist, steht die zuletzt angelegte im Detail."""
        AktiveModellKonfiguration.objects.all().delete()

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, f"Nr. {self.neuere.pk} ·")
        self.assertNotContains(response, f"Nr. {self.aeltere.pk} ·")

    def test_bietet_je_verwendung_einen_knopf(self) -> None:
        """Unbelegte Verwendungen nennen keinen abgelösten Vorgänger."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration"),
            {"konfiguration": self.neuere.pk},
        )

        self.assertContains(
            response,
            "Für Schüler:in aktivieren (statt Bezeichnung openrouter/altes-modell)",
        )
        self.assertContains(response, "Für Lehrperson aktivieren</button>")
        self.assertContains(response, "Für Bewerter aktivieren</button>")
        self.assertContains(
            response, f'action="{_aktivieren_url(self.neuere, Verwendung.BEWERTER)}"'
        )

    def test_zeigt_eine_schon_aktive_verwendung_als_deaktivierten_knopf(self) -> None:
        """Wofür die Konfiguration schon aktiv ist, lässt sich nicht erneut schalten."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(
            response,
            '<button class="button" type="button" disabled>Aktiv für Schüler:in</button>',
            html=True,
        )
        self.assertNotContains(
            response,
            f'action="{_aktivieren_url(self.aeltere, Verwendung.SCHUELERIN)}"',
        )

    def test_zeigt_einen_leerhinweis_ohne_konfiguration(self) -> None:
        """Ohne Konfiguration gibt es weder Tabelle noch Detail."""
        AktiveModellKonfiguration.objects.all().delete()
        ModellKonfiguration.objects.all().delete()

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "Noch keine Modell-Konfiguration angelegt.")

    def test_bietet_weder_bearbeiten_noch_loeschen_an(self) -> None:
        """Die Oberfläche verspricht nicht, was das append-only-Modell verbietet."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        gesten: list[str] = [
            beschriftung
            for beschriftung, _ in submit_knoepfe(response)
            if beschriftung != "Abmelden"
        ]
        self.assertTrue(gesten)
        for beschriftung in gesten:
            self.assertRegex(beschriftung, r"^Für .+ aktivieren")

    def test_zeigt_das_token_nur_maskiert(self) -> None:
        """Der Klartext des Tokens erscheint nirgends im Antwortkörper."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertNotContains(response, TOKEN)
        self.assertContains(response, "••••••••wxyz")

    def test_zeigt_einen_leerhinweis_ohne_token(self) -> None:
        """Eine Konfiguration ohne Zugangsdaten fällt vor dem ersten Aufruf auf."""
        ohne_token: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test", sprachmodell="fake"
        )

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration"),
            {"konfiguration": ohne_token.pk},
        )

        self.assertContains(response, "Kein Token hinterlegt")


class ModellKonfigurationAnlegenTests(TestCase):
    """Die Anlegen-Geste erzeugt eine neue Fassung und prüft am Feld."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def test_legt_eine_neue_konfiguration_an(self) -> None:
        """Das Formular schreibt eine Zeile und kehrt zur Liste zurück."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"), _anlegedaten()
        )

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertRedirects(
            response,
            f"{reverse('simulation:modell_konfiguration')}"
            f"?konfiguration={konfiguration.pk}",
        )
        self.assertEqual(konfiguration.bezeichnung, "Opus für die Schüler:in")
        self.assertEqual(konfiguration.anbieter, Anbieter.OPENROUTER)
        self.assertEqual(konfiguration.anbieter_token, TOKEN)
        self.assertEqual(konfiguration.parameter, {"temperature": 0.2})

    def test_gibt_das_token_nach_dem_speichern_nicht_zurueck(self) -> None:
        """Der Klartext erscheint weder im Formular noch in der Liste."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"), _anlegedaten(), follow=True
        )

        self.assertNotContains(response, TOKEN)

    def test_meldet_ungueltiges_json_am_feld(self) -> None:
        """Ein Syntaxfehler steht dort, wo er entstanden ist."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(parameter="{kaputt"),
        )

        self.assertFormError(
            response.context["form"], "parameter", "Bitte gültiges JSON eintragen."
        )
        self.assertNotIn("__all__", response.context["form"].errors)

    def test_meldet_unbekannten_parameter_schluessel_mit_erlaubten_werten(self) -> None:
        """Die Meldung am Feld sagt auch, was erlaubt gewesen wäre."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(parameter='{"mock_response": "Ich addiere."}'),
        )

        fehler: str = response.context["form"].errors["parameter"][0]
        self.assertIn("mock_response", fehler)
        self.assertIn("temperature", fehler)
        self.assertFalse(ModellKonfiguration.objects.exists())

    def test_meldet_fehlendes_token_am_feld(self) -> None:
        """Ein Verstoß gegen die Anbieterbindung steht am jeweiligen Feld."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(anbieter_token=""),
        )

        self.assertFormError(
            response.context["form"],
            "anbieter_token",
            "Ohne Token bedient der Anbieter keinen Aufruf.",
        )

    def test_verlangt_eine_bezeichnung(self) -> None:
        """Ohne Bezeichnung entsteht keine Fassung."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"), _anlegedaten(bezeichnung="")
        )

        self.assertFormError(
            response.context["form"],
            "bezeichnung",
            "Dieses Feld ist zwingend erforderlich.",
        )
        self.assertFalse(ModellKonfiguration.objects.exists())

    def test_meldet_fehlendes_praefix_am_modellnamen(self) -> None:
        """Der Modellname trägt die Anbieterbindung, die er verletzt."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(sprachmodell="claude-opus-4-8"),
        )

        self.assertFormError(
            response.context["form"],
            "sprachmodell",
            "Dieser Anbieter verlangt das Präfix »openrouter/«.",
        )

    def test_gibt_den_klartext_bei_einem_fehler_nicht_zurueck(self) -> None:
        """Auch das erneut gezeigte Formular trägt das Token nicht."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(sprachmodell="claude-opus-4-8"),
        )

        self.assertNotContains(response, TOKEN)


class ModellKonfigurationEditorTests(ZweiFassungenTestCase):
    """Der getrennte Editor legt an, füllt aus einer Vorlage vor, aktiviert nichts."""

    def _editor(self, **abfrage: object) -> HttpResponse:
        # Öffnet den Editor, auf Wunsch mit Abfrageparametern wie der Vorlage.

        return self.client.get(reverse("simulation:modell_konfiguration_neu"), abfrage)

    def test_die_liste_traegt_kein_anlegeformular_mehr(self) -> None:
        """Statt des Formulars führt ein Knopf in den Editor."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(
            response,
            f'href="{reverse("simulation:modell_konfiguration_neu")}"',
        )
        self.assertContains(response, "Neue Konfiguration")

    def test_das_detail_bietet_die_gewaehlte_als_vorlage_an(self) -> None:
        """Der Knopf im Detail nennt die gewählte Zeile als Vorlage."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration"),
            {"konfiguration": self.neuere.pk},
        )

        self.assertContains(
            response,
            f'href="{reverse("simulation:modell_konfiguration_neu")}'
            f'?vorlage={self.neuere.pk}"',
        )
        self.assertContains(response, "Als Vorlage für eine neue Konfiguration")

    def test_startet_ohne_vorlage_leer(self) -> None:
        """Ohne Vorlage ist nichts vorgefüllt."""
        response: HttpResponse = self._editor()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].initial)

    def test_fuellt_aus_der_vorlage_alles_ausser_dem_token_vor(self) -> None:
        """Anbieter, Basis-URL, Sprachmodell und Parameter kommen aus der Vorlage."""
        vorlage: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Opus warm",
            anbieter=Anbieter.OPENROUTER,
            sprachmodell="openrouter/anthropic/claude-opus",
            anbieter_basis_url="https://example.test/api/v1",
            anbieter_token=TOKEN,
            parameter={"temperature": 0.7},
        )

        response: HttpResponse = self._editor(vorlage=vorlage.pk)
        form: ModellKonfigurationForm = response.context["form"]

        self.assertEqual(form["bezeichnung"].value(), "Opus warm (Kopie)")
        self.assertEqual(form["anbieter"].value(), Anbieter.OPENROUTER)
        self.assertEqual(
            form["anbieter_basis_url"].value(), "https://example.test/api/v1"
        )
        self.assertEqual(
            form["sprachmodell"].value(), "openrouter/anthropic/claude-opus"
        )
        self.assertEqual(form["parameter"].value(), '{"temperature": 0.7}')
        self.assertContains(response, 'value="Opus warm (Kopie)"')

    def test_das_token_der_vorlage_steht_nirgends_im_html(self) -> None:
        """Das Tokenfeld ist leer, der Klartext erreicht weder Seite noch Kontext."""
        response: HttpResponse = self._editor(vorlage=self.aeltere.pk)

        self.assertFalse(response.context["form"]["anbieter_token"].value())
        self.assertNotContains(response, TOKEN)
        self.assertNotContains(response, TOKEN[-4:])

    def test_lehnt_eine_unbekannte_vorlage_ab(self) -> None:
        """Eine Vorlage, die es nicht gibt, ergibt 404."""
        for genannt in ("999999", "keine-zahl"):
            with self.subTest(vorlage=genannt):
                self.assertEqual(self._editor(vorlage=genannt).status_code, 404)

    def test_anlegen_aktiviert_nichts(self) -> None:
        """Alle Aktiv-Zeiger bleiben, wie sie waren."""
        ModellKonfiguration.objects.aktivieren(self.neuere, Verwendung.BEWERTER)
        vorher: dict[str, int] = ModellKonfiguration.objects.aktive_je_verwendung()

        self.client.post(reverse("simulation:modell_konfiguration_neu"), _anlegedaten())

        self.assertEqual(ModellKonfiguration.objects.count(), 3)
        self.assertEqual(ModellKonfiguration.objects.aktive_je_verwendung(), vorher)

    def test_bietet_kein_gleich_aktivieren_an(self) -> None:
        """Aktiviert wird allein in der Liste."""
        response: HttpResponse = self._editor(vorlage=self.aeltere.pk)

        self.assertEqual(
            [beschriftung for beschriftung, _ in submit_knoepfe(response)],
            ["Abmelden", "Konfiguration anlegen"],
        )

    def test_meldet_das_anlegen_auf_der_liste(self) -> None:
        """Nach dem Anlegen steht die neue Konfiguration im Detail der Liste."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(),
            follow=True,
        )

        self.assertContains(response, "»Opus für die Schüler:in« ist angelegt.")
        self.assertContains(response, "<h3>Opus für die Schüler:in</h3>", html=True)

    def test_markiert_den_sidebar_eintrag(self) -> None:
        """Der Editor gehört zur Seite der Modell-Konfiguration."""
        response: HttpResponse = self._editor()

        self.assertContains(
            response,
            '<a href="/system/modell-konfiguration/" aria-current="page">'
            "Modell-Konfiguration</a>",
            html=False,
        )


class ModellKonfigurationAktivierenTests(ZweiFassungenTestCase):
    """Das Umschalten je Verwendung läuft über die Manager-Geste."""

    def test_aktiviert_fuer_die_genannte_verwendung(self) -> None:
        """Danach liefert aktive() genau diese, das Detail bleibt bei ihr."""
        for verwendung in Verwendung:
            with self.subTest(verwendung=verwendung):
                response: HttpResponse = self.client.post(
                    _aktivieren_url(self.neuere, verwendung)
                )

                self.assertRedirects(
                    response,
                    f"{reverse('simulation:modell_konfiguration')}"
                    f"?konfiguration={self.neuere.pk}",
                )
                self.assertEqual(
                    ModellKonfiguration.objects.aktive(verwendung), self.neuere
                )

    def test_lehnt_eine_unbekannte_verwendung_ab(self) -> None:
        """Nur die drei festen Verwendungen haben einen Zeiger."""
        response: HttpResponse = self.client.post(
            _aktivieren_url(self.neuere, "hausmeister")
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(AktiveModellKonfiguration.objects.count(), 1)

    def test_lehnt_eine_unbekannte_konfiguration_ab(self) -> None:
        """Ein Zeiger zeigt nur auf eine bestehende Konfiguration."""
        response: HttpResponse = self.client.post(
            reverse(
                "simulation:modell_konfiguration_aktivieren",
                args=[999, Verwendung.BEWERTER],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(ModellKonfiguration.objects.aktive(Verwendung.BEWERTER))

    def test_aktivieren_ist_der_post_route_vorbehalten(self) -> None:
        """Eine Zustandsänderung entsteht nicht durch einen Aufruf per GET."""
        response: HttpResponse = self.client.get(
            _aktivieren_url(self.neuere, Verwendung.SCHUELERIN)
        )

        self.assertEqual(response.status_code, 405)


class ModellKonfigurationNavigationTests(TestCase):
    """Die Sidebar führt auf die Seite statt einen Platzhalter zu tragen."""

    def test_verlinkt_die_seite_in_der_gruppe_system(self) -> None:
        """Der `geplant`-Platzhalter ist durch einen echten Link ersetzt."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(
            response,
            '<a href="/system/modell-konfiguration/" aria-current="page">Modell-Konfiguration</a>',
            html=False,
        )


class ModellKonfigurationFakeTests(TestCase):
    """Ohne Anbieter läuft die Instanz weiter ohne Netz und ohne Zugangsdaten."""

    def test_legt_eine_fake_konfiguration_ohne_parameter_an(self) -> None:
        """Ein leer gelassenes Parameter-Feld ist ein leerer Beutel."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            {
                "bezeichnung": "Offline",
                "anbieter": Anbieter.FAKE,
                "sprachmodell": "fake",
                "anbieter_basis_url": "",
                "anbieter_token": "",
                "parameter": "",
            },
        )

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertRedirects(
            response,
            f"{reverse('simulation:modell_konfiguration')}"
            f"?konfiguration={konfiguration.pk}",
        )
        self.assertEqual(konfiguration.parameter, {})


class ModellKonfigurationFormularTests(TestCase):
    """Die Seite führt die Felder in der Eingabefolge."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def test_haelt_die_eingabefolge(self) -> None:
        """Erst die Bezeichnung, dann der Zugang, den der Ladeknopf braucht."""
        seite: str = self.client.get(
            reverse("simulation:modell_konfiguration_neu")
        ).content.decode()

        stellen: list[int] = [
            seite.index(f'name="{feld}"')
            for feld in (
                "bezeichnung",
                "anbieter",
                "anbieter_token",
                "anbieter_basis_url",
                "sprachmodell",
                "parameter",
            )
        ]
        self.assertEqual(stellen, sorted(stellen))


OPENROUTER_LISTE: dict[str, object] = {
    "data": [{"id": "anthropic/claude-opus-4.8", "name": "Anthropic: Claude Opus"}]
}
INFOMANIAK_LISTE: dict[str, object] = {
    "result": "success",
    "data": [{"id": 4711, "name": "swiss-ai/Apertus", "type": "llm"}],
}
INFOMANIAK_PRODUKTE: dict[str, object] = {
    "result": "success",
    "data": [{"product_name": "Ai-Tools", "product_id": 314159, "status": "ok"}],
}
WURZEL: str = "https://api.infomaniak.com/2/ai/314159/openai/v1"


def _je_url(antworten: dict[str, object]) -> Callable[..., Mock]:
    """Beantwortet jede URL mit ihrer Nutzlast oder wirft die genannte Ausnahme."""

    def abrufen(url: str, **_: object) -> Mock:
        antwort: object = antworten[url]
        if isinstance(antwort, Exception):
            raise antwort
        geliefert: Mock = Mock()
        geliefert.json.return_value = antwort
        return geliefert

    return abrufen


def _abrufdaten(**werte: object) -> dict[str, object]:
    """Liefert den Beutel, den der Ladeknopf mitschickt."""
    return {
        "anbieter": Anbieter.OPENROUTER,
        "naht": Naht.SPRACHMODELL,
        "anbieter_token": TOKEN,
        **werte,
    }


class ModellvorschlaegeEndpunktTests(TestCase):
    """Der Endpunkt liefert ausschließlich die normalisierte Vorschlagsliste."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def _openrouter_vorschlaege_holen(self, **werte: object) -> HttpResponse:
        """Ruft die Vorschläge ab, während OpenRouter seine Liste liefert."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.return_value.json.return_value = (
                OPENROUTER_LISTE
            )
            return self.client.post(
                reverse("simulation:modellvorschlaege"), _abrufdaten(**werte)
            )

    def test_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Der Abruf hängt an derselben Rolle wie die Seite (ADR-0039)."""
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

        response: HttpResponse = self.client.post(
            reverse("simulation:modellvorschlaege"), _abrufdaten()
        )

        self.assertEqual(response.status_code, 403)

    def test_ist_der_post_route_vorbehalten(self) -> None:
        """Das getippte Token gehört nicht in eine URL."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modellvorschlaege")
        )

        self.assertEqual(response.status_code, 405)

    def test_liefert_die_vorschlaege_des_verzeichnisses(self) -> None:
        """Die Liste des Anbieters erscheint mit Anzeige und fertigem Wert."""
        response: HttpResponse = self._openrouter_vorschlaege_holen()

        self.assertContains(response, "Anthropic: Claude Opus")
        self.assertContains(response, "openrouter/anthropic/claude-opus-4.8")

    def test_gibt_das_getippte_token_nicht_zurueck(self) -> None:
        """Das Token bleibt im Formular; die Antwort trägt es nicht."""
        response: HttpResponse = self._openrouter_vorschlaege_holen()

        self.assertNotContains(response, TOKEN)

    def test_meldet_einen_gescheiterten_abruf_verstaendlich(self) -> None:
        """Ein stummer Anbieter erzeugt eine Meldung, keinen Serverfehler."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.side_effect = httpx.ConnectError(
                "keine Verbindung"
            )

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"), _abrufdaten()
            )

        self.assertContains(response, "OpenRouter ist nicht erreichbar.")

    def test_setzt_den_vorschlag_in_das_feld_des_formulars(self) -> None:
        """Die Naht nennt das Feld, das das Formular für das Sprachmodell rendert."""
        response: HttpResponse = self._openrouter_vorschlaege_holen()

        self.assertContains(response, "id_sprachmodell")
        self.assertNotContains(response, "id_transkriptionsmodell")

    def test_setzt_den_vorschlag_der_transkription_in_ihr_eigenes_feld(self) -> None:
        """Die Naht nennt das Feld, das das Formular für die Transkription rendert."""
        response: HttpResponse = self._openrouter_vorschlaege_holen(
            naht=Naht.TRANSKRIPTION
        )

        self.assertContains(response, "id_transkriptionsmodell")
        self.assertNotContains(response, "id_sprachmodell")

    def test_holt_infomaniaks_liste_allein_mit_dem_getippten_token(self) -> None:
        """Beim Anlegen gibt es weder gespeichertes Token noch Basis-URL (ADR-0056)."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.return_value.json.return_value = {
                "result": "success",
                "data": [{"id": 4711, "name": "swiss-ai/Apertus", "type": "llm"}],
            }

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.INFOMANIAK),
            )

        self.assertEqual(
            httpx_client.call_args.kwargs["headers"],
            {"Authorization": f"Bearer {TOKEN}"},
        )
        httpx_client.return_value.get.assert_any_call(
            "https://api.infomaniak.com/1/ai/models"
        )
        self.assertEqual(ModellKonfiguration.objects.count(), 0)
        self.assertContains(response, "openai/swiss-ai/Apertus")
        self.assertNotContains(response, TOKEN)

    def test_meldet_den_anbieter_fake_ohne_netzaufruf(self) -> None:
        """Beim Anbieter »fake« gibt es nichts abzurufen."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.FAKE, anbieter_token=""),
            )

        httpx_client.assert_not_called()
        self.assertContains(response, "keine Modellliste")

    def test_fuellt_bei_infomaniak_die_leere_basis_url_in_derselben_geste(self) -> None:
        """Ein Druck, zwei Felder: Modellliste und Produktabfrage in einem Zug."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.side_effect = _je_url(
                {
                    "https://api.infomaniak.com/1/ai/models": INFOMANIAK_LISTE,
                    "https://api.infomaniak.com/1/ai": INFOMANIAK_PRODUKTE,
                }
            )

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.INFOMANIAK, anbieter_basis_url=""),
            )

        self.assertContains(response, WURZEL)
        self.assertContains(response, "openai/swiss-ai/Apertus")

    def test_ueberschreibt_eine_getippte_basis_url_nicht(self) -> None:
        """Eine bewusst abweichende Angabe bleibt erhalten."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.side_effect = _je_url(
                {
                    "https://api.infomaniak.com/1/ai/models": INFOMANIAK_LISTE,
                    "https://api.infomaniak.com/1/ai": INFOMANIAK_PRODUKTE,
                }
            )

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(
                    anbieter=Anbieter.INFOMANIAK,
                    anbieter_basis_url="https://eigene.wurzel/v1",
                ),
            )

        self.assertNotIn(
            "https://api.infomaniak.com/1/ai",
            [aufruf.args[0] for aufruf in httpx_client.return_value.get.call_args_list],
        )
        self.assertNotContains(response, WURZEL)
        self.assertContains(response, "openai/swiss-ai/Apertus")

    def test_haelt_die_vorschlaege_wenn_allein_die_produktabfrage_scheitert(
        self,
    ) -> None:
        """Der eine Teil reißt den anderen nicht mit."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.side_effect = _je_url(
                {
                    "https://api.infomaniak.com/1/ai/models": INFOMANIAK_LISTE,
                    "https://api.infomaniak.com/1/ai": httpx.ConnectError(
                        "keine Verbindung"
                    ),
                }
            )

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.INFOMANIAK, anbieter_basis_url=""),
            )

        self.assertContains(response, "openai/swiss-ai/Apertus")
        self.assertNotContains(response, "anbieter_basis_url")

    def test_fragt_bei_openrouter_kein_produkt_ab(self) -> None:
        """Dort ist die Basis-URL optional und hat ihre Vorgabe am Profil."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.return_value.json.return_value = {"data": []}

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter_basis_url=""),
            )

        httpx_client.return_value.get.assert_called_once_with(
            "https://openrouter.ai/api/v1/models",
            params={"supported_parameters": "structured_outputs"},
        )
        self.assertNotContains(response, "anbieter_basis_url")

    def test_traegt_den_kontoklarnamen_der_produktabfrage_nicht(self) -> None:
        """Der Klarname steht neben der Kennung und erreicht keine Oberfläche."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.return_value.json.return_value = {
                "result": "success",
                "data": [
                    {
                        "product_name": "Ai-Tools",
                        "product_id": 314159,
                        "account_name": "Frida Musterfrau",
                        "status": "ok",
                    }
                ],
            }

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.INFOMANIAK, anbieter_basis_url=""),
            )

        self.assertNotContains(response, "Frida")
        self.assertContains(response, "314159")


class ModellvorschlaegeSeitenTests(TestCase):
    """Die Seite trägt den Knopf, holt aber beim Rendern nichts."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def _seite(self) -> HttpResponse:
        # Ruft die Seite ab, auf der der Knopf neben dem Sprachmodell steht.

        return self.client.get(reverse("simulation:modell_konfiguration_neu"))

    def test_traegt_den_knopf_neben_dem_sprachmodell(self) -> None:
        """Der Knopf ist der einzige Auslöser des Abrufs."""
        response: HttpResponse = self._seite()

        self.assertContains(response, "Modelle und Basis-URL laden")
        self.assertContains(
            response, f'hx-post="{reverse("simulation:modellvorschlaege")}"'
        )

    def test_schickt_die_getippte_basis_url_mit(self) -> None:
        """Nur so kann der Abruf ein gefülltes Feld unangetastet lassen."""
        response: HttpResponse = self._seite()

        self.assertContains(response, "[name='anbieter_basis_url']")

    def test_holt_beim_rendern_keine_modellliste(self) -> None:
        """Eine Systemseite rendert ohne Netzaufruf."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            self._seite()

        httpx_client.assert_not_called()


class ZeroRetentionErklaerungTests(TestCase):
    """Die Zero-Retention-Erklärung entsteht beim Anlegen oder nachträglich."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.linus = konto_mit_rollen("linus", is_superuser=True)
        self.client.force_login(self.linus)

    def test_gibt_die_erklaerung_beim_anlegen_ab(self) -> None:
        """Zeitpunkt und Konto schreibt die Anlegen-Geste selbst mit."""
        self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(
                zero_retention_erklaert="on",
                zero_retention_beleg="OpenRouter: nur ZDR-Endpunkte, Stand 10/2026",
            ),
        )

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertTrue(konfiguration.zero_retention_erklaert)
        self.assertEqual(
            konfiguration.zero_retention_beleg,
            "OpenRouter: nur ZDR-Endpunkte, Stand 10/2026",
        )
        self.assertEqual(konfiguration.zero_retention_erklaert_von, self.linus)
        self.assertIsNotNone(konfiguration.zero_retention_erklaert_am)

    def test_legt_ohne_haekchen_eine_nicht_erklaerte_konfiguration_an(self) -> None:
        """Die Erklärung ist eine eigene Geste, kein Nebenprodukt des Belegs."""
        self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(zero_retention_beleg="AVV"),
        )

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertFalse(konfiguration.zero_retention_erklaert)
        self.assertEqual(konfiguration.zero_retention_beleg, "")

    def test_meldet_den_fehlenden_beleg_beim_anlegen_am_feld(self) -> None:
        """Ein Häkchen ohne Beleg ist nicht nachprüfbar."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(zero_retention_erklaert="on", zero_retention_beleg=""),
        )

        self.assertFormError(
            response.context["form"],
            "zero_retention_beleg",
            "Ohne Beleg der Zusage ist die Erklärung nicht nachprüfbar.",
        )
        self.assertFalse(ModellKonfiguration.objects.exists())

    def test_weist_die_erklaerung_bei_fake_beim_anlegen_ab(self) -> None:
        """Über einen Auftragsverarbeiter, den es nicht gibt, wird nichts erklärt."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"),
            _anlegedaten(
                anbieter=Anbieter.FAKE,
                sprachmodell="fake",
                anbieter_token="",
                parameter="",
                zero_retention_erklaert="on",
                zero_retention_beleg="AVV",
            ),
        )

        self.assertIn("zero_retention_beleg", response.context["form"].errors)
        self.assertFalse(ModellKonfiguration.objects.exists())

    def test_gibt_die_erklaerung_nachtraeglich_ab(self) -> None:
        """Eine Fassung ohne Erklärung bekommt sie im Detail der Liste."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")

        response: HttpResponse = self.client.post(
            _erklaeren_url(konfiguration), {"zero_retention_beleg": "AVV vom 01.10."}
        )

        self.assertRedirects(
            response,
            f"{reverse('simulation:modell_konfiguration')}"
            f"?konfiguration={konfiguration.pk}",
        )
        konfiguration.refresh_from_db()
        self.assertTrue(konfiguration.zero_retention_erklaert)
        self.assertEqual(konfiguration.zero_retention_beleg, "AVV vom 01.10.")
        self.assertEqual(konfiguration.zero_retention_erklaert_von, self.linus)

    def test_meldet_den_fehlenden_beleg_beim_nachtraeglichen_erklaeren(self) -> None:
        """Auch nachträglich gibt es keine Erklärung ohne Beleg."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")

        response: HttpResponse = self.client.post(
            _erklaeren_url(konfiguration), {"zero_retention_beleg": "  "}
        )

        self.assertFormError(
            response.context["erklaerungsformular"],
            "zero_retention_beleg",
            "Ohne Beleg der Zusage ist die Erklärung nicht nachprüfbar.",
        )
        konfiguration.refresh_from_db()
        self.assertFalse(konfiguration.zero_retention_erklaert)

    def test_weist_die_nachtraegliche_erklaerung_bei_fake_ab(self) -> None:
        """Die Regel gilt auch, wenn jemand die Geste ohne Formular aufruft."""
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Offline", sprachmodell="fake"
        )

        response: HttpResponse = self.client.post(
            _erklaeren_url(konfiguration), {"zero_retention_beleg": "AVV"}, follow=True
        )

        self.assertContains(response, "keine Zero-Retention-Erklärung zulässig")
        konfiguration.refresh_from_db()
        self.assertFalse(konfiguration.zero_retention_erklaert)

    def test_aendert_eine_abgegebene_erklaerung_nicht(self) -> None:
        """Beleg und Zeitpunkt der ersten Erklärung bleiben stehen."""
        konfiguration: ModellKonfiguration = erklaerte(
            _openrouter("openrouter/gpt-test")
        )
        beleg: str = konfiguration.zero_retention_beleg

        response: HttpResponse = self.client.post(
            _erklaeren_url(konfiguration),
            {"zero_retention_beleg": "Neuer Beleg"},
            follow=True,
        )

        self.assertContains(response, "lässt sich nicht ändern")
        konfiguration.refresh_from_db()
        self.assertEqual(konfiguration.zero_retention_beleg, beleg)

    def test_bietet_die_erklaerung_nur_an_einer_nicht_erklaerten_fassung_an(
        self,
    ) -> None:
        """Erklärte und `fake`-Fassungen zeigen kein Erklärungsformular."""
        offen: ModellKonfiguration = _openrouter("openrouter/offen")
        erklaert: ModellKonfiguration = erklaerte(_openrouter("openrouter/erklaert"))
        fake: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Offline", sprachmodell="fake"
        )

        for konfiguration, angeboten in (
            (offen, True),
            (erklaert, False),
            (fake, False),
        ):
            with self.subTest(konfiguration=konfiguration.sprachmodell):
                response: HttpResponse = self.client.get(
                    reverse("simulation:modell_konfiguration"),
                    {"konfiguration": konfiguration.pk},
                )

                if angeboten:
                    self.assertContains(response, _erklaeren_url(konfiguration))
                else:
                    self.assertNotContains(response, _erklaeren_url(konfiguration))

    def test_zeigt_den_beleg_einer_erklaerten_fassung_im_detail(self) -> None:
        """Wer die Liste liest, sieht, worauf sich die Zusage stützt."""
        konfiguration: ModellKonfiguration = erklaerte(
            _openrouter("openrouter/gpt-test")
        )

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration"),
            {"konfiguration": konfiguration.pk},
        )

        self.assertContains(response, konfiguration.zero_retention_beleg)
        self.assertContains(response, "zero-retention-erklaerende")


class ZeroRetentionTorTests(TestCase):
    """Für die Schüler:in braucht es eine erklärte Fassung oder `fake`."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def test_sperrt_die_aktivierung_fuer_die_schuelerin_mit_sichtbarem_grund(
        self,
    ) -> None:
        """Wer die Geste dennoch aufruft, liest, warum sie gesperrt ist."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")

        response: HttpResponse = self.client.post(
            _aktivieren_url(konfiguration, Verwendung.SCHUELERIN), follow=True
        )

        self.assertContains(response, "Zero-Retention-Erklärung aktivieren")
        self.assertIsNone(ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN))

    def test_zeigt_den_schalter_der_schuelerin_gesperrt_samt_grund(self) -> None:
        """Der Grund steht schon vor dem Klick am Schalter."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration"),
            {"konfiguration": konfiguration.pk},
        )

        self.assertNotContains(
            response, _aktivieren_url(konfiguration, Verwendung.SCHUELERIN)
        )
        self.assertContains(
            response, _aktivieren_url(konfiguration, Verwendung.BEWERTER)
        )
        self.assertContains(response, "Für Schüler:in erst nach der Erklärung")

    def test_aktiviert_lehrperson_und_bewerter_ohne_erklaerung(self) -> None:
        """Evals verarbeiten nur simulierte Gespräche."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")

        for verwendung in (Verwendung.LEHRPERSON, Verwendung.BEWERTER):
            self.client.post(_aktivieren_url(konfiguration, verwendung))

            self.assertEqual(
                ModellKonfiguration.objects.aktive(verwendung), konfiguration
            )

    def test_aktiviert_fake_fuer_die_schuelerin(self) -> None:
        """Entwicklung und Workshop laufen ohne externen Anbieter."""
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Offline", sprachmodell="fake"
        )

        self.client.post(_aktivieren_url(konfiguration, Verwendung.SCHUELERIN))

        self.assertEqual(
            ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN), konfiguration
        )


class ZeroRetentionUebersichtTests(TestCase):
    """Die Liste zeigt den Erklärungsstand und warnt beim Bestand."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def _zeilen(self) -> list[str]:
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )
        tabelle: str = (
            response.content.decode().split("<tbody>")[1].split("</tbody>")[0]
        )
        return tabelle.split("</tr>")[:-1]

    def test_zeigt_den_erklaerungsstand_je_zeile(self) -> None:
        """Erklärt, fehlend oder ohne Auftragsverarbeiter, auf einen Blick."""
        ModellKonfiguration.objects.create(bezeichnung="Offline", sprachmodell="fake")
        erklaerte(_openrouter("openrouter/erklaert"))
        _openrouter("openrouter/offen")

        offen, erklaert, fake = self._zeilen()

        self.assertIn("fehlt", offen)
        self.assertIn("erklärt", erklaert)
        self.assertIn("nicht nötig", fake)

    def test_warnt_bei_nicht_erklaerter_aktiver_schuelerin_konfiguration(
        self,
    ) -> None:
        """Eine Konfiguration aus dem Bestand bleibt aktiv, aber nicht unbemerkt."""
        AktiveModellKonfiguration.objects.create(
            konfiguration=_openrouter("openrouter/bestand"),
            verwendung=Verwendung.SCHUELERIN,
        )

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(
            response,
            "Der aktiven Konfiguration der Schüler:in fehlt die Zero-Retention-Erklärung",
        )

    def test_warnt_nicht_bei_erklaerter_oder_fake_schuelerin_konfiguration(
        self,
    ) -> None:
        """Der Hinweis erscheint nur, wo wirklich etwas fehlt."""
        for konfiguration in (
            erklaerte(_openrouter("openrouter/erklaert")),
            ModellKonfiguration.objects.create(
                bezeichnung="Offline", sprachmodell="fake"
            ),
        ):
            with self.subTest(konfiguration=konfiguration.sprachmodell):
                ModellKonfiguration.objects.aktivieren(
                    konfiguration, Verwendung.SCHUELERIN
                )

                response: HttpResponse = self.client.get(
                    reverse("simulation:modell_konfiguration")
                )

                self.assertNotContains(response, "fehlt die Zero-Retention-Erklärung")

"""HTTP-Tests der blauen Seite für Modell-Konfigurationen."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from simulation.forms import ModellKonfigurationForm
from simulation.models import (
    AktiveModellKonfiguration,
    Anbieter,
    ModellKonfiguration,
)
from simulation.modellverzeichnis import (
    AnbieterNichtErreichbar,
    Modellvorschlag,
    Naht,
)

TOKEN: str = "sk-or-v1-geheimnis-wxyz"


def _autorin(username: str) -> Konto:
    """Legt ein Konto ohne Administrationsrolle an."""
    konto: Konto = get_user_model().objects.create_user(username=username)
    konto.groups.add(Group.objects.get(name="Autor:in"))
    return konto


def _administratorin(username: str = "linus") -> Konto:
    """Legt ein Konto mit Administrationsrolle an."""
    return get_user_model().objects.create_user(username=username, is_superuser=True)


def _openrouter(sprachmodell: str, token: str = TOKEN) -> ModellKonfiguration:
    """Legt eine gültige Konfiguration an, wie sie die Seite auflistet."""
    return ModellKonfiguration.objects.create(
        anbieter=Anbieter.OPENROUTER,
        sprachmodell=sprachmodell,
        anbieter_token=token,
    )


def _formularfelder() -> list[str]:
    """Liefert die Feldnamen in der Reihenfolge, die das Formular führt."""
    return list(ModellKonfigurationForm().fields)


def _anlegedaten(**werte: object) -> dict[str, object]:
    """Liefert einen gültigen Formularbeutel, geändert um die Testwerte."""
    return {
        "anbieter": Anbieter.OPENROUTER,
        "sprachmodell": "openrouter/anthropic/claude-opus-4-8",
        "anbieter_basis_url": "",
        "anbieter_token": TOKEN,
        "parameter": '{"temperature": 0.2}',
        **werte,
    }


class ModellKonfigurationRollenTests(TestCase):
    """Die Betriebseinstellungen der Instanz hängen an der Administrationsrolle."""

    def test_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Eine Autorin ohne Administrationsrolle darf die Seite nicht öffnen."""
        self.client.force_login(_autorin("ada"))

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

    def test_aktivieren_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Auch die Aktivieren-Geste bleibt der Administration vorbehalten."""
        konfiguration: ModellKonfiguration = _openrouter("openrouter/gpt-test")
        self.client.force_login(_autorin("ada"))

        response: HttpResponse = self.client.post(
            reverse(
                "simulation:modell_konfiguration_aktivieren", args=[konfiguration.pk]
            )
        )

        self.assertEqual(response.status_code, 403)


class ZweiFassungenTestCase(TestCase):
    """Zwei angelegte Fassungen, die ältere aktiv, als Administratorin gesehen."""

    def setUp(self) -> None:
        """Legt zwei Konfigurationen an und aktiviert die ältere."""
        self.aeltere: ModellKonfiguration = _openrouter("openrouter/altes-modell")
        self.neuere: ModellKonfiguration = _openrouter("openrouter/neues-modell")
        ModellKonfiguration.objects.aktivieren(self.aeltere)
        self.client.force_login(_administratorin())


class ModellKonfigurationListeTests(ZweiFassungenTestCase):
    """Die Liste zeigt alle je angelegten Fassungen und die aktive."""

    def test_traegt_die_system_farbflaeche(self) -> None:
        """Die Seite gehört zum blauen System-Bereich."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, 'class="page system-page area--system"')

    def test_listet_alle_je_angelegten_konfigurationen(self) -> None:
        """Auch überholte Fassungen bleiben sichtbar."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "openrouter/altes-modell")
        self.assertContains(response, "openrouter/neues-modell")

    def test_markiert_die_aktive_konfiguration(self) -> None:
        """Die Liste sagt, welche Fassung neue Sitzungen bedient."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )
        zeilen: list[dict[str, object]] = response.context["konfigurationen"]

        self.assertContains(response, '<span class="badge badge--system">Aktiv</span>')
        self.assertEqual(
            {zeile["pk"] for zeile in zeilen if zeile["ist_aktiv"]},
            {self.aeltere.pk},
        )

    def test_bietet_weder_bearbeiten_noch_loeschen_an(self) -> None:
        """Die Oberfläche verspricht nicht, was das append-only-Modell verbietet."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertNotContains(response, "Bearbeiten")
        self.assertNotContains(response, "Löschen")

    def test_zeigt_das_token_nur_maskiert(self) -> None:
        """Der Klartext des Tokens erscheint nirgends im Antwortkörper."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertNotContains(response, TOKEN)
        self.assertContains(response, "••••••••wxyz")

    def test_gibt_den_klartext_nicht_in_den_kontext(self) -> None:
        """Nur der maskierte Wert erreicht die Vorlage."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertNotIn(TOKEN, str(response.context["konfigurationen"]))

    def test_zeigt_einen_leerhinweis_ohne_token(self) -> None:
        """Eine Konfiguration ohne Zugangsdaten fällt vor dem ersten Aufruf auf."""
        ModellKonfiguration.objects.create(sprachmodell="fake")

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "Kein Token hinterlegt")

    def test_benennt_die_betriebsfolgen(self) -> None:
        """Das Umschalten und die Rotation sind informierte Gesten."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertContains(response, "laufende Trainings sofort")
        self.assertContains(response, "laufende Erhebungen gar nicht")
        self.assertContains(response, "Anlegen plus Aktivieren")


class ModellKonfigurationAnlegenTests(TestCase):
    """Die Anlegen-Geste erzeugt eine neue Fassung und prüft am Feld."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(_administratorin())

    def test_legt_eine_neue_konfiguration_an(self) -> None:
        """Das Formular schreibt eine Zeile und kehrt zur Liste zurück."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration"), _anlegedaten()
        )

        self.assertRedirects(response, reverse("simulation:modell_konfiguration"))
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertEqual(konfiguration.anbieter, Anbieter.OPENROUTER)
        self.assertEqual(konfiguration.anbieter_token, TOKEN)
        self.assertEqual(konfiguration.parameter, {"temperature": 0.2})

    def test_gibt_das_token_nach_dem_speichern_nicht_zurueck(self) -> None:
        """Der Klartext erscheint weder im Formular noch in der Liste."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration"), _anlegedaten(), follow=True
        )

        self.assertNotContains(response, TOKEN)

    def test_meldet_ungueltiges_json_am_feld(self) -> None:
        """Ein Syntaxfehler steht dort, wo er entstanden ist."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration"),
            _anlegedaten(parameter="{kaputt"),
        )

        self.assertFormError(
            response.context["form"], "parameter", "Bitte gültiges JSON eintragen."
        )
        self.assertNotIn("__all__", response.context["form"].errors)

    def test_meldet_unbekannten_parameter_schluessel_mit_erlaubten_werten(self) -> None:
        """Die Meldung am Feld sagt auch, was erlaubt gewesen wäre."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration"),
            _anlegedaten(parameter='{"mock_response": "Ich addiere."}'),
        )

        fehler: str = response.context["form"].errors["parameter"][0]
        self.assertIn("mock_response", fehler)
        self.assertIn("temperature", fehler)
        self.assertFalse(ModellKonfiguration.objects.exists())

    def test_meldet_fehlendes_token_am_feld(self) -> None:
        """Ein Verstoß gegen die Anbieterbindung steht am jeweiligen Feld."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration"), _anlegedaten(anbieter_token="")
        )

        self.assertFormError(
            response.context["form"],
            "anbieter_token",
            "Ohne Token bedient der Anbieter keinen Aufruf.",
        )

    def test_meldet_fehlendes_praefix_am_modellnamen(self) -> None:
        """Der Modellname trägt die Anbieterbindung, die er verletzt."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration"),
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
            reverse("simulation:modell_konfiguration"),
            _anlegedaten(sprachmodell="claude-opus-4-8"),
        )

        self.assertNotContains(response, TOKEN)


class ModellKonfigurationAktivierenTests(ZweiFassungenTestCase):
    """Das Umschalten läuft über die Manager-Geste."""

    def test_aktiviert_eine_bestehende_konfiguration(self) -> None:
        """Nach dem Umschalten zeigt die Liste die neue als aktiv."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_aktivieren", args=[self.neuere.pk])
        )

        self.assertRedirects(response, reverse("simulation:modell_konfiguration"))
        self.assertEqual(ModellKonfiguration.objects.aktive(), self.neuere)

    def test_verschiebt_nur_den_zeiger_ohne_zeile_zu_mutieren(self) -> None:
        """Das Umschalten geht über aktivieren() und lässt beide Zeilen unberührt."""
        vorher: list[tuple[object, ...]] = list(
            ModellKonfiguration.objects.order_by("pk").values_list()
        )

        self.client.post(
            reverse("simulation:modell_konfiguration_aktivieren", args=[self.neuere.pk])
        )

        self.assertEqual(
            list(ModellKonfiguration.objects.order_by("pk").values_list()), vorher
        )
        self.assertEqual(AktiveModellKonfiguration.objects.count(), 1)

    def test_aktivieren_ist_der_post_route_vorbehalten(self) -> None:
        """Eine Zustandsänderung entsteht nicht durch einen Aufruf per GET."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration_aktivieren", args=[self.neuere.pk])
        )

        self.assertEqual(response.status_code, 405)


class ModellKonfigurationNavigationTests(TestCase):
    """Die Sidebar führt auf die Seite statt einen Platzhalter zu tragen."""

    def test_verlinkt_die_seite_in_der_gruppe_system(self) -> None:
        """Der `geplant`-Platzhalter ist durch einen echten Link ersetzt."""
        self.client.force_login(_administratorin())

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertNotContains(response, "Modell-Konfiguration <small>geplant</small>")
        self.assertContains(
            response,
            '<a href="/system/modell-konfiguration/" aria-current="page">Modell-Konfiguration</a>',
            html=False,
        )


class ModellKonfigurationFakeTests(TestCase):
    """Ohne Anbieter läuft die Instanz weiter ohne Netz und ohne Zugangsdaten."""

    def test_legt_eine_fake_konfiguration_ohne_parameter_an(self) -> None:
        """Ein leer gelassenes Parameter-Feld ist ein leerer Beutel."""
        self.client.force_login(_administratorin())

        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration"),
            {
                "anbieter": Anbieter.FAKE,
                "sprachmodell": "fake",
                "anbieter_basis_url": "",
                "anbieter_token": "",
                "parameter": "",
            },
        )

        self.assertRedirects(response, reverse("simulation:modell_konfiguration"))
        self.assertEqual(ModellKonfiguration.objects.get().parameter, {})


class ModellKonfigurationFormularTests(TestCase):
    """Die Seite nennt ihre Felder namentlich — vollständig und in Formularfolge."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(_administratorin())

    def test_nennt_jedes_feld_des_formulars(self) -> None:
        """Kein im Formular geführtes Feld fehlt auf der Seite."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        for feld in _formularfelder():
            self.assertContains(response, f'name="{feld}"')

    def test_haelt_die_reihenfolge_des_formulars(self) -> None:
        """Die namentliche Aufzählung ordnet die Felder wie das Formular."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )
        koerper: str = response.content.decode()

        stellen: list[int] = [
            koerper.index(f'name="{feld}"') for feld in _formularfelder()
        ]

        self.assertEqual(stellen, sorted(stellen))


def _vorschlag(anzeige: str = "Anthropic: Claude Opus") -> Modellvorschlag:
    """Liefert einen Vorschlag, wie ihn das Modellverzeichnis bildet."""
    return Modellvorschlag(
        wert="openrouter/anthropic/claude-opus-4.8",
        modellname="anthropic/claude-opus-4.8",
        anzeige=anzeige,
    )


def _abrufdaten(**werte: object) -> dict[str, object]:
    """Liefert den Beutel, den der Knopf »Modelle laden« mitschickt."""
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
        self.client.force_login(_administratorin())

    def test_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Der Abruf hängt an derselben Rolle wie die Seite (ADR-0033)."""
        self.client.force_login(_autorin("ada"))

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
        """Anbieter, Naht und Token erreichen das Verzeichnis, die Liste die Seite."""
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.return_value = [_vorschlag()]

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"), _abrufdaten()
            )

        verzeichnis.assert_called_once_with(Anbieter.OPENROUTER, TOKEN)
        verzeichnis.return_value.vorschlaege.assert_called_once_with(Naht.SPRACHMODELL)
        self.assertContains(response, "Anthropic: Claude Opus")
        self.assertContains(response, "openrouter/anthropic/claude-opus-4.8")

    def test_gibt_das_getippte_token_nicht_zurueck(self) -> None:
        """Das Token bleibt im Formular; die Antwort trägt es nicht."""
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.return_value = [_vorschlag()]

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"), _abrufdaten()
            )

        self.assertNotContains(response, TOKEN)

    def test_meldet_einen_gescheiterten_abruf_verstaendlich(self) -> None:
        """Ein stummer Anbieter erzeugt eine Meldung, keinen Serverfehler."""
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.side_effect = AnbieterNichtErreichbar(
                "OpenRouter ist nicht erreichbar."
            )

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"), _abrufdaten()
            )

        self.assertContains(response, "OpenRouter ist nicht erreichbar.")

    def test_setzt_den_vorschlag_in_das_feld_des_formulars(self) -> None:
        """Die Naht nennt das Feld, das das Formular für das Sprachmodell rendert."""
        feld: str = ModellKonfigurationForm()["sprachmodell"].auto_id
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.return_value = [_vorschlag()]

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"), _abrufdaten()
            )

        self.assertContains(response, f"getElementById('{feld}')")

    def test_meldet_den_anbieter_fake_ohne_netzaufruf(self) -> None:
        """Beim Anbieter »fake« gibt es nichts abzurufen."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.FAKE, anbieter_token=""),
            )

        httpx_client.assert_not_called()
        self.assertContains(response, "keine Modellliste")


class ModellvorschlaegeSeitenTests(TestCase):
    """Die Seite trägt den Knopf, holt aber beim Rendern nichts."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(_administratorin())

    def _seite(self) -> HttpResponse:
        # Ruft die Seite ab, auf der der Knopf neben dem Sprachmodell steht.

        return self.client.get(reverse("simulation:modell_konfiguration"))

    def test_traegt_den_knopf_neben_dem_sprachmodell(self) -> None:
        """Der Knopf ist der einzige Auslöser des Abrufs."""
        response: HttpResponse = self._seite()

        self.assertContains(response, "Modelle laden")
        self.assertContains(
            response, f'hx-post="{reverse("simulation:modellvorschlaege")}"'
        )

    def test_verbirgt_den_knopf_beim_anbieter_fake(self) -> None:
        """Ohne echten Anbieter gibt es keinen Knopf."""
        response: HttpResponse = self._seite()

        self.assertContains(response, "anbieter !== 'fake'")

    def test_holt_beim_rendern_keine_modellliste(self) -> None:
        """Eine Systemseite rendert ohne Netzaufruf."""
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            self._seite()

        verzeichnis.assert_not_called()

    def test_leert_die_liste_beim_anbieterwechsel(self) -> None:
        """Kein Vorschlag des vorigen Anbieters bleibt stehen."""
        response: HttpResponse = self._seite()

        self.assertContains(response, "$refs.modellvorschlaege.innerHTML = ''")

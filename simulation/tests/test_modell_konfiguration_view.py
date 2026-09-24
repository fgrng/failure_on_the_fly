"""HTTP-Tests der blauen Seite für Modell-Konfigurationen."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from simulation.forms import ModellKonfigurationForm, TranskriptionsKonfigurationForm
from simulation.models import (
    AktiveModellKonfiguration,
    Anbieter,
    ModellKonfiguration,
    Verwendung,
)
from simulation.modellverzeichnis import (
    INFOMANIAK_MODELLE_URL,
    OPENROUTER_MODELLE_URL,
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
        bezeichnung="Test",
        anbieter=Anbieter.OPENROUTER,
        sprachmodell=sprachmodell,
        anbieter_token=token,
    )


def _aktivieren_url(konfiguration: ModellKonfiguration, verwendung: str) -> str:
    """Die Aktivieren-Geste einer Konfiguration für eine Verwendung."""
    return reverse(
        "simulation:modell_konfiguration_aktivieren",
        args=[konfiguration.pk, verwendung],
    )


def _liste_mit(konfiguration: ModellKonfiguration) -> str:
    """Die Liste mit der Konfiguration im Detail."""
    return (
        f"{reverse('simulation:modell_konfiguration')}?konfiguration={konfiguration.pk}"
    )


def _formularfelder() -> list[str]:
    """Liefert die Feldnamen in der Reihenfolge, die das Formular führt."""
    return list(ModellKonfigurationForm().fields)


def _anlegedaten(**werte: object) -> dict[str, object]:
    """Liefert einen gültigen Formularbeutel, geändert um die Testwerte."""
    return {
        "bezeichnung": "Opus für Urteile",
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
                "simulation:modell_konfiguration_aktivieren",
                args=[konfiguration.pk, Verwendung.SCHUELERIN],
            )
        )

        self.assertEqual(response.status_code, 403)


class ZweiFassungenTestCase(TestCase):
    """Zwei angelegte Fassungen, die ältere aktiv, als Administratorin gesehen."""

    def setUp(self) -> None:
        """Legt zwei Konfigurationen an und aktiviert die ältere."""
        self.aeltere: ModellKonfiguration = _openrouter("openrouter/altes-modell")
        self.neuere: ModellKonfiguration = _openrouter("openrouter/neues-modell")
        ModellKonfiguration.objects.aktivieren(self.aeltere, Verwendung.SCHUELERIN)
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

    def test_markiert_die_aktiven_verwendungen_je_zeile(self) -> None:
        """Die Kürzel sagen je Zeile, für welche Verwendungen sie aktiv ist."""
        ModellKonfiguration.objects.aktivieren(self.neuere, Verwendung.BEWERTER)

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )
        zeilen: dict[object, dict[str, object]] = {
            zeile["pk"]: zeile for zeile in response.context["konfigurationen"]
        }

        self.assertEqual(
            [v["ist_aktiv"] for v in zeilen[self.aeltere.pk]["verwendungen"]],
            [True, False, False],
        )
        self.assertEqual(
            [v["ist_aktiv"] for v in zeilen[self.neuere.pk]["verwendungen"]],
            [False, False, True],
        )
        self.assertContains(response, 'title="Schüler:in: aktiv"')

    def test_zeigt_ohne_auswahl_die_konfiguration_der_schuelerin(self) -> None:
        """Das Detail beginnt bei der Konfiguration, auf der Sitzungen laufen."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration")
        )

        self.assertEqual(response.context["gewaehlt"]["pk"], self.aeltere.pk)

    def test_zeigt_die_gewaehlte_konfiguration_im_detail(self) -> None:
        """Die gewählte Zeile trägt das Detail samt Aktivieren je Verwendung."""
        response: HttpResponse = self.client.get(_liste_mit(self.neuere))

        self.assertEqual(response.context["gewaehlt"]["pk"], self.neuere.pk)
        self.assertContains(response, "Für Schüler:in aktivieren (statt Test)")
        self.assertContains(response, "Für Lehrperson aktivieren</button>")
        self.assertContains(response, _aktivieren_url(self.neuere, Verwendung.BEWERTER))

    def test_zeigt_die_aktive_verwendung_ohne_knopf(self) -> None:
        """Was schon aktiv ist, lässt sich nicht noch einmal aktivieren."""
        response: HttpResponse = self.client.get(_liste_mit(self.aeltere))

        self.assertContains(response, "✓ Aktiv für Schüler:in")
        self.assertNotContains(
            response, _aktivieren_url(self.aeltere, Verwendung.SCHUELERIN)
        )

    def test_verlinkt_die_gewaehlte_als_vorlage(self) -> None:
        """Aus dem Detail führt ein Weg zu einer neuen Konfiguration."""
        response: HttpResponse = self.client.get(_liste_mit(self.neuere))

        self.assertContains(
            response,
            f"{reverse('simulation:modell_konfiguration_neu')}?vorlage={self.neuere.pk}",
        )

    def test_nennt_den_leeren_bestand(self) -> None:
        """Ohne Konfiguration gibt es kein Detail, nur den Hinweis."""
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
        fake: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Offline", sprachmodell="fake"
        )

        response: HttpResponse = self.client.get(_liste_mit(fake))

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
            reverse("simulation:modell_konfiguration_neu"), _anlegedaten()
        )

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertRedirects(response, _liste_mit(konfiguration))
        self.assertEqual(konfiguration.bezeichnung, "Opus für Urteile")
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
    """Der getrennte Editor legt an, auf Wunsch aus einer Vorlage."""

    def test_verlangt_eine_bezeichnung(self) -> None:
        """Keine namenlose Konfiguration entsteht neu."""
        response: HttpResponse = self.client.post(
            reverse("simulation:modell_konfiguration_neu"), _anlegedaten(bezeichnung="")
        )

        self.assertFormError(
            response.context["form"],
            "bezeichnung",
            "Dieses Feld ist zwingend erforderlich.",
        )
        self.assertEqual(ModellKonfiguration.objects.count(), 2)

    def test_aktiviert_die_neue_konfiguration_nicht(self) -> None:
        """Aktiviert wird allein in der Liste."""
        self.client.post(reverse("simulation:modell_konfiguration_neu"), _anlegedaten())

        self.assertEqual(
            ModellKonfiguration.objects.aktive_je_verwendung(),
            {Verwendung.SCHUELERIN: self.aeltere.pk},
        )

    def test_fuellt_aus_der_vorlage_alles_ausser_dem_token_vor(self) -> None:
        """Das Token bleibt write-only und wird für jede Konfiguration neu getippt."""
        response: HttpResponse = self.client.get(
            f"{reverse('simulation:modell_konfiguration_neu')}?vorlage={self.neuere.pk}"
        )
        form: ModellKonfigurationForm = response.context["form"]

        self.assertEqual(form["bezeichnung"].value(), "Test (Kopie)")
        self.assertEqual(form["anbieter"].value(), Anbieter.OPENROUTER)
        self.assertEqual(form["sprachmodell"].value(), "openrouter/neues-modell")
        self.assertFalse(form["anbieter_token"].value())
        self.assertNotContains(response, TOKEN)
        self.assertContains(response, "das Token wird neu eingegeben")

    def test_laesst_die_vorlage_unveraendert(self) -> None:
        """Aus der Vorlage entsteht eine neue Zeile."""
        self.client.post(
            f"{reverse('simulation:modell_konfiguration_neu')}?vorlage={self.neuere.pk}",
            _anlegedaten(sprachmodell="openrouter/neues-modell"),
        )

        self.assertEqual(ModellKonfiguration.objects.count(), 3)
        self.neuere.refresh_from_db()
        self.assertEqual(self.neuere.bezeichnung, "Test")

    def test_weist_eine_unbekannte_vorlage_ab(self) -> None:
        """Eine Vorlage, die es nicht gibt, ist kein leerer Editor."""
        response: HttpResponse = self.client.get(
            f"{reverse('simulation:modell_konfiguration_neu')}?vorlage=999"
        )

        self.assertEqual(response.status_code, 404)

    def test_weist_autorin_ohne_administrationsrolle_ab(self) -> None:
        """Auch der Editor gehört zur Administration."""
        self.client.force_login(_autorin("ada"))

        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration_neu")
        )

        self.assertEqual(response.status_code, 403)


class ModellKonfigurationAktivierenTests(ZweiFassungenTestCase):
    """Das Umschalten läuft über die Manager-Geste."""

    def test_aktiviert_eine_bestehende_konfiguration(self) -> None:
        """Nach dem Umschalten zeigt die Liste die neue als aktiv."""
        response: HttpResponse = self.client.post(
            _aktivieren_url(self.neuere, Verwendung.SCHUELERIN)
        )

        self.assertRedirects(response, _liste_mit(self.neuere))
        self.assertEqual(
            ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN), self.neuere
        )

    def test_verschiebt_nur_den_zeiger_ohne_zeile_zu_mutieren(self) -> None:
        """Das Umschalten geht über aktivieren() und lässt beide Zeilen unberührt."""
        vorher: list[tuple[object, ...]] = list(
            ModellKonfiguration.objects.order_by("pk").values_list()
        )

        self.client.post(_aktivieren_url(self.neuere, Verwendung.SCHUELERIN))

        self.assertEqual(
            list(ModellKonfiguration.objects.order_by("pk").values_list()), vorher
        )
        self.assertEqual(AktiveModellKonfiguration.objects.count(), 1)

    def test_aktivieren_ist_der_post_route_vorbehalten(self) -> None:
        """Eine Zustandsänderung entsteht nicht durch einen Aufruf per GET."""
        response: HttpResponse = self.client.get(
            _aktivieren_url(self.neuere, Verwendung.SCHUELERIN)
        )

        self.assertEqual(response.status_code, 405)

    def test_schaltet_eine_verwendung_ohne_die_anderen_zu_beruehren(self) -> None:
        """Dieselbe Konfiguration darf zusätzlich einer weiteren Verwendung dienen."""
        self.client.post(_aktivieren_url(self.aeltere, Verwendung.BEWERTER))

        self.assertEqual(
            ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN), self.aeltere
        )
        self.assertEqual(
            ModellKonfiguration.objects.aktive(Verwendung.BEWERTER), self.aeltere
        )
        self.assertIsNone(ModellKonfiguration.objects.aktive(Verwendung.LEHRPERSON))

    def test_weist_eine_unbekannte_verwendung_ab(self) -> None:
        """Nur die drei festen Verwendungen tragen einen Zeiger."""
        response: HttpResponse = self.client.post(
            _aktivieren_url(self.neuere, "zuschauer")
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(AktiveModellKonfiguration.objects.count(), 1)


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

        fake: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertRedirects(response, _liste_mit(fake))
        self.assertEqual(fake.parameter, {})


class ModellKonfigurationFormularTests(TestCase):
    """Die Seite nennt ihre Felder namentlich — vollständig und in Formularfolge."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(_administratorin())

    def test_nennt_jedes_feld_des_formulars(self) -> None:
        """Kein im Formular geführtes Feld fehlt auf der Seite."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration_neu")
        )

        for feld in _formularfelder():
            self.assertContains(response, f'name="{feld}"')

    def test_haelt_die_reihenfolge_des_formulars(self) -> None:
        """Die namentliche Aufzählung ordnet die Felder wie das Formular."""
        response: HttpResponse = self.client.get(
            reverse("simulation:modell_konfiguration_neu")
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


WURZEL: str = "https://api.infomaniak.com/2/ai/314159/openai/v1"


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

    def test_setzt_den_vorschlag_der_transkription_in_ihr_eigenes_feld(self) -> None:
        """Die Naht nennt das Feld, das das Formular für die Transkription rendert."""
        feld: str = TranskriptionsKonfigurationForm()["transkriptionsmodell"].auto_id
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.return_value = [_vorschlag()]

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(naht=Naht.TRANSKRIPTION),
            )

        self.assertContains(response, f"getElementById('{feld}')")

    def test_holt_infomaniaks_liste_allein_mit_dem_getippten_token(self) -> None:
        """Beim Anlegen gibt es weder gespeichertes Token noch Basis-URL (ADR-0036)."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            httpx_client.return_value.get.return_value.json.return_value = {
                "result": "success",
                "data": [{"id": 4711, "name": "swiss-ai/Apertus", "type": "llm"}],
            }

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.INFOMANIAK),
            )

        httpx_client.return_value.get.assert_any_call(INFOMANIAK_MODELLE_URL)
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
        feld: str = ModellKonfigurationForm()["anbieter_basis_url"].auto_id
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.return_value = [_vorschlag()]
            verzeichnis.return_value.basis_url.return_value = WURZEL

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.INFOMANIAK, anbieter_basis_url=""),
            )

        verzeichnis.return_value.basis_url.assert_called_once_with(Naht.SPRACHMODELL)
        self.assertContains(response, f"getElementById('{feld}').value = '{WURZEL}'")
        self.assertContains(response, "Anthropic: Claude Opus")

    def test_ueberschreibt_eine_getippte_basis_url_nicht(self) -> None:
        """Eine bewusst abweichende Angabe bleibt erhalten."""
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.return_value = [_vorschlag()]
            verzeichnis.return_value.basis_url.return_value = WURZEL

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(
                    anbieter=Anbieter.INFOMANIAK,
                    anbieter_basis_url="https://eigene.wurzel/v1",
                ),
            )

        verzeichnis.return_value.basis_url.assert_not_called()
        self.assertNotContains(response, WURZEL)
        self.assertContains(response, "Anthropic: Claude Opus")

    def test_haelt_die_vorschlaege_wenn_allein_die_produktabfrage_scheitert(
        self,
    ) -> None:
        """Der eine Teil reißt den anderen nicht mit."""
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            verzeichnis.return_value.vorschlaege.return_value = [_vorschlag()]
            verzeichnis.return_value.basis_url.side_effect = AnbieterNichtErreichbar(
                "Infomaniak ist nicht erreichbar."
            )

            response: HttpResponse = self.client.post(
                reverse("simulation:modellvorschlaege"),
                _abrufdaten(anbieter=Anbieter.INFOMANIAK, anbieter_basis_url=""),
            )

        self.assertContains(response, "Anthropic: Claude Opus")
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
            OPENROUTER_MODELLE_URL,
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
        self.client.force_login(_administratorin())

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

    def test_verbirgt_den_knopf_beim_anbieter_fake(self) -> None:
        """Ohne echten Anbieter gibt es keinen Knopf."""
        response: HttpResponse = self._seite()

        self.assertContains(response, "anbieter !== 'fake'")

    def test_stellt_das_token_vor_das_sprachmodell(self) -> None:
        """Der Ladeknopf braucht das Token, also steht es beim Anbieter."""
        seite: str = self._seite().content.decode()

        self.assertLess(
            seite.index('name="anbieter_token"'), seite.index('name="sprachmodell"')
        )

    def test_holt_beim_rendern_keine_modellliste(self) -> None:
        """Eine Systemseite rendert ohne Netzaufruf."""
        with patch("simulation.views.modellverzeichnis") as verzeichnis:
            self._seite()

        verzeichnis.assert_not_called()

    def test_leert_die_liste_beim_anbieterwechsel(self) -> None:
        """Kein Vorschlag des vorigen Anbieters bleibt stehen."""
        response: HttpResponse = self._seite()

        self.assertContains(response, "$refs.modellvorschlaege.innerHTML = ''")

"""Anbieterbindung, Maskierung und die blaue Seite der Transkription."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen
from config.tests.formular import submit_knoepfe
from simulation.models import Anbieter, TranskriptionsKonfiguration
from simulation.transkription import transkriptions_anbieter

SEITE: str = "simulation:transkriptions_konfiguration"


def _eingabe(**werte: object) -> dict[str, object]:
    # Ein vollständig ausgefülltes Formular, geändert um die Testwerte.

    return {
        "anbieter": Anbieter.OPENROUTER,
        "anbieter_basis_url": "https://openrouter.ai/api/v1",
        "anbieter_token": "sk-or-supergeheim1234",
        "transkriptionsmodell": "whisper-large-v3",
        "sprache": "de",
        **werte,
    }


@pytest.mark.django_db
def test_fake_braucht_weder_modell_noch_zugangsdaten() -> None:
    """Die Vorgabe bleibt gültig, ohne dass jemand etwas einträgt."""

    TranskriptionsKonfiguration.objects.aktuelle().full_clean()


@pytest.mark.django_db
def test_openrouter_verlangt_modell_und_token() -> None:
    """Ohne Modell und Token bedient der Anbieter keinen Aufruf."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    konfiguration.anbieter = Anbieter.OPENROUTER

    with pytest.raises(ValidationError) as fehler:
        konfiguration.full_clean()

    assert set(fehler.value.message_dict) == {
        "transkriptionsmodell",
        "anbieter_token",
    }


@pytest.mark.django_db
def test_infomaniak_verlangt_zusaetzlich_die_endpunktwurzel() -> None:
    """Infomaniak antwortet nur an der Wurzel des eigenen Kontos."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    konfiguration.anbieter = Anbieter.INFOMANIAK
    konfiguration.transkriptionsmodell = "whisper"
    konfiguration.anbieter_token = "geheim"

    with pytest.raises(ValidationError) as fehler:
        konfiguration.full_clean()

    assert set(fehler.value.message_dict) == {"anbieter_basis_url"}


class TranskriptionsKonfigurationRollenTests(TestCase):
    """Die Betriebseinstellungen liegen hinter der Administrationsrolle."""

    def test_weist_autorin_ab(self) -> None:
        """Eine Autorin ohne Administrationsrolle darf die Seite nicht öffnen."""
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

        self.assertEqual(self.client.get(reverse(SEITE)).status_code, 403)

    def test_weist_nicht_angemeldetes_konto_ab(self) -> None:
        """Auch anonyme Anfragen erhalten die geforderte Zugriffsverweigerung."""
        self.assertEqual(self.client.get(reverse(SEITE)).status_code, 403)

    def test_weist_autorin_auch_beim_speichern_ab(self) -> None:
        """Die Schreibroute trägt dieselbe Rollenprüfung wie die Anzeige."""
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

        response: HttpResponse = self.client.post(reverse(SEITE), _eingabe())

        self.assertEqual(response.status_code, 403)


class TranskriptionsKonfigurationSeiteTests(TestCase):
    """Die Seite bearbeitet die eine Zeile und gibt kein Token zurück."""

    def setUp(self) -> None:
        """Meldet die Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def test_zeigt_die_felder_in_der_eingabefolge(self) -> None:
        """Erst Anbieter und Zugang, dann das Modell, wie in der Modell-Konfiguration."""
        seite: str = self.client.get(reverse(SEITE)).content.decode()

        stellen: list[int] = [
            seite.index(f'name="{feld}"')
            for feld in (
                "anbieter",
                "anbieter_token",
                "anbieter_basis_url",
                "transkriptionsmodell",
                "sprache",
            )
        ]
        self.assertEqual(stellen, sorted(stellen))

    def test_speichert_die_eingetragene_konfiguration(self) -> None:
        """Die Eingabe der Administratorin landet in der Datenbank."""
        self.client.post(reverse(SEITE), _eingabe())

        konfiguration: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.aktuelle()
        )
        self.assertEqual(konfiguration.anbieter, Anbieter.OPENROUTER)
        self.assertEqual(konfiguration.transkriptionsmodell, "whisper-large-v3")
        self.assertEqual(konfiguration.anbieter_token, "sk-or-supergeheim1234")

    def test_zweimaliges_speichern_erzeugt_keine_zweite_konfiguration(self) -> None:
        """Die Seite überschreibt dieselbe Zeile, statt Fassungen anzuhäufen."""
        self.client.post(reverse(SEITE), _eingabe())
        self.client.post(reverse(SEITE), _eingabe(transkriptionsmodell="whisper-1"))

        self.assertEqual(TranskriptionsKonfiguration.objects.count(), 1)
        self.assertEqual(
            TranskriptionsKonfiguration.objects.aktuelle().transkriptionsmodell,
            "whisper-1",
        )

    def test_meldet_die_verletzte_anbieterbindung_am_feld(self) -> None:
        """Ein fehlendes Token wird dort gemeldet, wo es hingehört."""
        response: HttpResponse = self.client.post(
            reverse(SEITE), _eingabe(anbieter_token="")
        )

        self.assertFormError(
            response.context["form"],
            "anbieter_token",
            ["Ohne Token bedient der Anbieter keinen Aufruf."],
        )

    def test_gibt_das_token_nach_dem_speichern_nicht_zurueck(self) -> None:
        """Das gesetzte Token verlässt die Anwendung nicht über die Oberfläche."""
        response: HttpResponse = self.client.post(
            reverse(SEITE), _eingabe(), follow=True
        )

        self.assertNotContains(response, "sk-or-supergeheim1234")

    def test_zeigt_das_hinterlegte_token_maskiert(self) -> None:
        """Die letzten vier Zeichen erlauben den Abgleich mit dem Dashboard."""
        self.client.post(reverse(SEITE), _eingabe())

        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertContains(response, "1234")
        self.assertNotContains(response, "supergeheim")

    def test_behaelt_das_token_wenn_das_feld_leer_bleibt(self) -> None:
        """Eine Änderung an der Sprache darf die Zugangsdaten nicht wegwerfen."""
        self.client.post(reverse(SEITE), _eingabe())

        self.client.post(reverse(SEITE), _eingabe(anbieter_token="", sprache="fr"))

        konfiguration: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.aktuelle()
        )
        self.assertEqual(konfiguration.sprache, "fr")
        self.assertEqual(konfiguration.anbieter_token, "sk-or-supergeheim1234")

    def test_bietet_weder_anlegen_noch_aktivieren_noch_eine_liste_an(self) -> None:
        """Ein veränderlicher Singleton kennt genau eine Geste: Bearbeiten."""
        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertEqual(
            [beschriftung for beschriftung, _ in submit_knoepfe(response)],
            ["Abmelden", "Änderungen speichern"],
        )

    def test_traegt_einen_eigenen_sidebar_eintrag(self) -> None:
        """Die Gruppe »System« führt die Transkription neben dem Sprachmodell."""
        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertContains(
            response,
            '<a href="/system/transkription/" aria-current="page">Transkriptions-Konfiguration</a>',
            html=False,
        )


class TranskriptionsKonfigurationVorschlaegeTests(TestCase):
    """Der Knopf steht neben dem Modellfeld und holt beim Rendern nichts."""

    def setUp(self) -> None:
        """Meldet die Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def test_traegt_den_knopf_neben_dem_transkriptionsmodell(self) -> None:
        """Derselbe Endpunkt wie an der Sprachmodell-Naht, dieselbe Geste."""
        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertContains(response, "Modelle und Basis-URL laden")
        self.assertContains(
            response, f'hx-post="{reverse("simulation:modellvorschlaege")}"'
        )
        self.assertContains(response, '"naht": "transkription"')

    def test_holt_beim_rendern_keine_modellliste(self) -> None:
        """Eine Systemseite rendert ohne Netzaufruf."""
        with patch("simulation.modellverzeichnis.httpx.Client") as httpx_client:
            self.client.get(reverse(SEITE))

        httpx_client.assert_not_called()


class TranskriptionsKonfigurationWirkungTests(TestCase):
    """Eine geänderte Konfiguration greift ohne Neustart."""

    def test_wirkt_bei_der_naechsten_anfrage(self) -> None:
        """Der Adapter entsteht je Anfrage aus der gespeicherten Zeile."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))
        self.assertEqual(
            transkriptions_anbieter().transkribieren(b"audio"),
            "Dies ist ein Platzhalter-Transkript.",
        )

        self.client.post(reverse(SEITE), _eingabe())

        with patch("simulation.transkription.OpenAI") as openai:
            openai.return_value.audio.transcriptions.create.return_value.text = "Hallo."
            transkriptions_anbieter().transkribieren(b"audio")

        self.assertEqual(
            openai.return_value.audio.transcriptions.create.call_args.kwargs["model"],
            "whisper-large-v3",
        )

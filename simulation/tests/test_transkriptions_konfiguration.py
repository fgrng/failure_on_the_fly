"""Anbieterbindung, Maskierung und die blaue Seite der Transkription."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen
from simulation.forms import TranskriptionsKonfigurationForm
from simulation.models import Anbieter, TranskriptionsKonfiguration
from simulation.transkription import transkriptions_anbieter

SEITE: str = "simulation:transkriptions_konfiguration"
AKTIVIEREN: str = "simulation:transkriptions_konfiguration_aktivieren"
TOKEN: str = "simulation:transkriptions_konfiguration_token"


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


def _openrouter_fassung(**werte: object) -> TranskriptionsKonfiguration:
    # Eine gespeicherte OpenRouter-Fassung, geändert um die Testwerte.

    return TranskriptionsKonfiguration.objects.create(
        **{
            "anbieter": Anbieter.OPENROUTER,
            "anbieter_token": "sk-or-supergeheim1234",
            "transkriptionsmodell": "whisper-large-v3",
            **werte,
        }
    )


@pytest.mark.django_db
def test_fake_braucht_weder_modell_noch_zugangsdaten() -> None:
    """Die Vorgabe bleibt gültig, ohne dass jemand etwas einträgt."""

    TranskriptionsKonfiguration.objects.aktive().full_clean()


@pytest.mark.django_db
def test_eine_frische_instanz_transkribiert_mit_fake() -> None:
    """Ohne Zutun ist die aktive Fassung `fake`, also keine Transkription."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktive()
    )

    assert konfiguration.anbieter == Anbieter.FAKE
    assert TranskriptionsKonfiguration.objects.aktive() == konfiguration


@pytest.mark.django_db
def test_aktivieren_wechselt_die_aktive_fassung() -> None:
    """Genau eine Fassung ist aktiv; die vorige bleibt erhalten."""

    vorige: TranskriptionsKonfiguration = TranskriptionsKonfiguration.objects.aktive()
    neue: TranskriptionsKonfiguration = _openrouter_fassung()

    TranskriptionsKonfiguration.objects.aktivieren(neue)

    assert TranskriptionsKonfiguration.objects.aktive() == neue
    assert TranskriptionsKonfiguration.objects.filter(pk=vorige.pk).exists()


@pytest.mark.django_db
def test_eine_fassung_ist_nicht_bearbeitbar() -> None:
    """Fassungen werden neu angelegt, nie geändert."""

    konfiguration: TranskriptionsKonfiguration = _openrouter_fassung()
    konfiguration.sprache = "fr"

    with pytest.raises(RuntimeError):
        konfiguration.save()
    with pytest.raises(RuntimeError):
        TranskriptionsKonfiguration.objects.filter(pk=konfiguration.pk).update(
            sprache="fr"
        )


@pytest.mark.django_db
def test_die_aktive_fassung_ist_nicht_loeschbar() -> None:
    """Der Zeiger hält seine Fassung fest."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktive()
    )

    with pytest.raises(ProtectedError):
        konfiguration.delete()


@pytest.mark.django_db
def test_das_token_rotiert_ohne_neue_fassung() -> None:
    """Die Tokenrotation ist der einzige Schreibvorgang an einer Fassung."""

    konfiguration: TranskriptionsKonfiguration = _openrouter_fassung()

    konfiguration.token_rotieren("  sk-or-neu5678  ")

    assert TranskriptionsKonfiguration.objects.get().anbieter_token == "sk-or-neu5678"


@pytest.mark.django_db
def test_die_rotation_verlangt_ein_token() -> None:
    """Ein leeres Token bediente keinen Aufruf mehr."""

    konfiguration: TranskriptionsKonfiguration = _openrouter_fassung()

    with pytest.raises(ValidationError) as fehler:
        konfiguration.token_rotieren(" ")

    assert fehler.value.message_dict == {
        "anbieter_token": ["Ohne Token bedient der Anbieter keinen Aufruf."]
    }
    assert TranskriptionsKonfiguration.objects.get().anbieter_token == (
        "sk-or-supergeheim1234"
    )


@pytest.mark.django_db
def test_fake_hat_kein_token_zu_rotieren() -> None:
    """Der Platzhalter braucht kein Token, also auch kein neues."""

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktive()
    )

    with pytest.raises(ValidationError, match="braucht kein Token"):
        konfiguration.token_rotieren("sk-or-neu5678")


@pytest.mark.django_db
def test_openrouter_verlangt_modell_und_token() -> None:
    """Ohne Modell und Token bedient der Anbieter keinen Aufruf."""

    konfiguration: TranskriptionsKonfiguration = TranskriptionsKonfiguration(
        anbieter=Anbieter.OPENROUTER
    )

    with pytest.raises(ValidationError) as fehler:
        konfiguration.full_clean()

    assert set(fehler.value.message_dict) == {
        "transkriptionsmodell",
        "anbieter_token",
    }


@pytest.mark.django_db
def test_infomaniak_verlangt_zusaetzlich_die_endpunktwurzel() -> None:
    """Infomaniak antwortet nur an der Wurzel des eigenen Kontos."""

    konfiguration: TranskriptionsKonfiguration = TranskriptionsKonfiguration(
        anbieter=Anbieter.INFOMANIAK,
        transkriptionsmodell="whisper",
        anbieter_token="geheim",
    )

    with pytest.raises(ValidationError) as fehler:
        konfiguration.full_clean()

    assert set(fehler.value.message_dict) == {"anbieter_basis_url"}


class TranskriptionsKonfigurationTokenTests(TestCase):
    """Ein leeres Tokenfeld übernimmt das Token nur am selben Endpunkt (#493)."""

    def setUp(self) -> None:
        """Aktiviert eine Infomaniak-Fassung mit Token."""
        self.vorlage: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.aktivieren(
                TranskriptionsKonfiguration.objects.create(
                    anbieter=Anbieter.INFOMANIAK,
                    anbieter_basis_url="https://api.infomaniak.com/1/ai/42",
                    anbieter_token="ik-supergeheim1234",
                    transkriptionsmodell="whisper",
                )
            )
        )

    def _formular(self, **werte: object) -> TranskriptionsKonfigurationForm:
        # Das Formular einer neuen Fassung über der aktiven.

        return TranskriptionsKonfigurationForm(
            data=_eingabe(
                **{
                    "anbieter": Anbieter.INFOMANIAK,
                    "anbieter_basis_url": "https://api.infomaniak.com/1/ai/42",
                    "anbieter_token": "",
                    "transkriptionsmodell": "whisper",
                    **werte,
                }
            ),
            vorlage=self.vorlage,
        )

    def test_gleicher_endpunkt_uebernimmt_das_token(self) -> None:
        """Modell und Sprache ändern sich, Anbieter und Basis-URL nicht."""
        formular: TranskriptionsKonfigurationForm = self._formular(
            transkriptionsmodell="whisper-large-v3", sprache="fr"
        )

        self.assertTrue(formular.is_valid(), formular.errors)
        self.assertEqual(formular.save().anbieter_token, "ik-supergeheim1234")

    def test_anbieterwechsel_ohne_token_ist_ungueltig(self) -> None:
        """Das Infomaniak-Token geht nicht an OpenRouter."""
        formular: TranskriptionsKonfigurationForm = self._formular(
            anbieter=Anbieter.OPENROUTER,
            anbieter_basis_url="https://openrouter.ai/api/v1",
            transkriptionsmodell="whisper-large-v3",
        )

        self.assertFalse(formular.is_valid())
        self.assertEqual(
            formular.errors["anbieter_token"],
            ["Ohne Token bedient der Anbieter keinen Aufruf."],
        )

    def test_endpunktwechsel_ohne_token_ist_ungueltig(self) -> None:
        """Das Token geht nicht an einen fremden Host."""
        formular: TranskriptionsKonfigurationForm = self._formular(
            anbieter_basis_url="https://fremd.example/1/ai/42"
        )

        self.assertFalse(formular.is_valid())
        self.assertEqual(
            formular.errors["anbieter_token"],
            ["Ohne Token bedient der Anbieter keinen Aufruf."],
        )

    def test_wechsel_mit_neuem_token_speichert_es(self) -> None:
        """Wer das Token bewusst neu einträgt, darf Anbieter und Endpunkt wechseln."""
        formular: TranskriptionsKonfigurationForm = self._formular(
            anbieter=Anbieter.OPENROUTER,
            anbieter_basis_url="https://openrouter.ai/api/v1",
            anbieter_token="sk-or-neu5678",
            transkriptionsmodell="whisper-large-v3",
        )

        self.assertTrue(formular.is_valid(), formular.errors)
        self.assertEqual(formular.save().anbieter_token, "sk-or-neu5678")

    def test_wechsel_auf_fake_traegt_kein_token(self) -> None:
        """Der Platzhalter bleibt über die Oberfläche erreichbar."""
        formular: TranskriptionsKonfigurationForm = self._formular(
            anbieter=Anbieter.FAKE,
            anbieter_basis_url="",
            transkriptionsmodell="",
        )

        self.assertTrue(formular.is_valid(), formular.errors)
        self.assertEqual(formular.save().anbieter_token, "")


class TranskriptionsKonfigurationRollenTests(TestCase):
    """Die Betriebseinstellungen liegen hinter der Administrationsrolle."""

    def setUp(self) -> None:
        """Meldet eine Autorin ohne Administrationsrolle an."""
        self.fassung: TranskriptionsKonfiguration = _openrouter_fassung()
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

    def test_weist_autorin_ab(self) -> None:
        """Eine Autorin ohne Administrationsrolle darf die Seite nicht öffnen."""
        self.assertEqual(self.client.get(reverse(SEITE)).status_code, 403)

    def test_leitet_nicht_angemeldetes_konto_zur_anmeldung(self) -> None:
        """Anonyme Anfragen werden zur Anmeldung weitergeleitet (#476)."""
        self.client.logout()

        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertRedirects(
            response,
            "/accounts/login/?next=/system/transkription/",
            fetch_redirect_response=False,
        )

    def test_weist_autorin_beim_anlegen_ab(self) -> None:
        """Die Schreibroute trägt dieselbe Rollenprüfung wie die Anzeige."""
        response: HttpResponse = self.client.post(reverse(SEITE), _eingabe())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(TranskriptionsKonfiguration.objects.count(), 1)

    def test_weist_autorin_beim_aktivieren_ab(self) -> None:
        """Nur die Administration wechselt die aktive Fassung."""
        response: HttpResponse = self.client.post(
            reverse(AKTIVIEREN, args=[self.fassung.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(TranskriptionsKonfiguration.objects.aktive(), self.fassung)

    def test_weist_autorin_beim_rotieren_ab(self) -> None:
        """Nur die Administration ersetzt ein Token."""
        response: HttpResponse = self.client.post(
            reverse(TOKEN, args=[self.fassung.pk]),
            {"rotation-anbieter_token": "sk-or-neu5678"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            TranskriptionsKonfiguration.objects.get(pk=self.fassung.pk).anbieter_token,
            "sk-or-supergeheim1234",
        )


class TranskriptionsKonfigurationSeiteTests(TestCase):
    """Die Seite listet Fassungen, legt neue an und gibt kein Token zurück."""

    def setUp(self) -> None:
        """Meldet die Administratorin an."""
        self.client.force_login(konto_mit_rollen("linus", is_superuser=True))

    def _neueste(self) -> TranskriptionsKonfiguration:
        # Die zuletzt angelegte Fassung.

        return TranskriptionsKonfiguration.objects.latest("pk")

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

    def test_legt_eine_neue_fassung_an_ohne_sie_zu_aktivieren(self) -> None:
        """Anlegen und Aktivieren sind zwei Gesten, wie bei der Modell-Konfiguration."""
        vorige: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.aktive()
        )

        response: HttpResponse = self.client.post(reverse(SEITE), _eingabe())

        neue: TranskriptionsKonfiguration = self._neueste()
        self.assertRedirects(
            response,
            f"{reverse(SEITE)}?fassung={neue.pk}",
            fetch_redirect_response=False,
        )
        self.assertEqual(
            (neue.anbieter, neue.transkriptionsmodell, neue.anbieter_token),
            (Anbieter.OPENROUTER, "whisper-large-v3", "sk-or-supergeheim1234"),
        )
        self.assertEqual(TranskriptionsKonfiguration.objects.aktive(), vorige)

    def test_jedes_anlegen_haengt_eine_fassung_an(self) -> None:
        """Keine Fassung wird überschrieben; jede, mit der transkribiert wurde, bleibt."""
        self.client.post(reverse(SEITE), _eingabe())
        erste: TranskriptionsKonfiguration = self._neueste()

        self.client.post(reverse(SEITE), _eingabe(transkriptionsmodell="whisper-1"))

        self.assertEqual(TranskriptionsKonfiguration.objects.count(), 3)
        self.assertEqual(
            TranskriptionsKonfiguration.objects.get(pk=erste.pk).transkriptionsmodell,
            "whisper-large-v3",
        )
        self.assertEqual(self._neueste().transkriptionsmodell, "whisper-1")

    def test_aktiviert_die_gewaehlte_fassung(self) -> None:
        """Der Zeiger wandert; die Seite zeigt den neuen Stand."""
        fassung: TranskriptionsKonfiguration = _openrouter_fassung()

        response: HttpResponse = self.client.post(
            reverse(AKTIVIEREN, args=[fassung.pk]), follow=True
        )

        self.assertEqual(TranskriptionsKonfiguration.objects.aktive(), fassung)
        self.assertContains(response, f"Die Fassung Nr. {fassung.pk} ist aktiv.")
        self.assertContains(
            response,
            '<button class="button" type="button" disabled>Aktiv</button>',
            html=True,
        )

    def test_listet_die_fassungen_mit_anbieter_modell_und_stand(self) -> None:
        """Jede Fassung steht in der Liste; die aktive ist als solche markiert."""
        fake: TranskriptionsKonfiguration = TranskriptionsKonfiguration.objects.aktive()
        fassung: TranskriptionsKonfiguration = _openrouter_fassung()
        TranskriptionsKonfiguration.objects.aktivieren(fassung)

        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertEqual(
            [
                (zeile.pk, zeile.anbieter, zeile.transkriptionsmodell, zeile.aktiv)
                for zeile in response.context["fassungen"]
            ],
            [
                (fassung.pk, "OpenRouter", "whisper-large-v3", True),
                (fake.pk, "Fake (ohne Netz)", "", False),
            ],
        )

    def test_rotiert_das_token_ohne_neue_fassung(self) -> None:
        """Die Rotation ändert das Token der Fassung und legt nichts an."""
        fassung: TranskriptionsKonfiguration = _openrouter_fassung()

        response: HttpResponse = self.client.post(
            reverse(TOKEN, args=[fassung.pk]),
            {"rotation-anbieter_token": "sk-or-neu5678"},
            follow=True,
        )

        self.assertEqual(
            TranskriptionsKonfiguration.objects.get(pk=fassung.pk).anbieter_token,
            "sk-or-neu5678",
        )
        self.assertEqual(TranskriptionsKonfiguration.objects.count(), 2)
        self.assertContains(
            response, f"Das Token der Fassung Nr. {fassung.pk} ist ersetzt."
        )
        self.assertNotContains(response, "sk-or-neu5678")

    def test_meldet_ein_leeres_token_an_der_rotation(self) -> None:
        """Die Domäne weist das leere Token ab; der Grund steht am Feld."""
        fassung: TranskriptionsKonfiguration = _openrouter_fassung()

        response: HttpResponse = self.client.post(
            reverse(TOKEN, args=[fassung.pk]), {"rotation-anbieter_token": ""}
        )

        self.assertFormError(
            response.context["rotationsformular"],
            "anbieter_token",
            ["Ohne Token bedient der Anbieter keinen Aufruf."],
        )

    def test_bietet_bei_fake_keine_rotation_an(self) -> None:
        """Der Platzhalter hat kein Token, das sich ersetzen ließe."""
        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertNotContains(response, "Token ersetzen")

    def test_meldet_die_abgewiesene_rotation_an_einer_fake_fassung(self) -> None:
        """Auch ohne Rotationsformular sieht die Administrator:in den Grund."""
        fake: TranskriptionsKonfiguration = TranskriptionsKonfiguration.objects.aktive()

        response: HttpResponse = self.client.post(
            reverse(TOKEN, args=[fake.pk]), {"rotation-anbieter_token": "sk-neu"}
        )

        self.assertContains(response, "Der Anbieter »fake« braucht kein Token.")

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

    def test_gibt_das_token_nach_dem_anlegen_nicht_zurueck(self) -> None:
        """Das gesetzte Token verlässt die Anwendung nicht über die Oberfläche."""
        response: HttpResponse = self.client.post(
            reverse(SEITE), _eingabe(), follow=True
        )

        self.assertNotContains(response, "sk-or-supergeheim1234")

    def test_zeigt_das_hinterlegte_token_maskiert(self) -> None:
        """Die letzten vier Zeichen erlauben den Abgleich mit dem Dashboard."""
        fassung: TranskriptionsKonfiguration = _openrouter_fassung()

        response: HttpResponse = self.client.get(
            reverse(SEITE), {"fassung": fassung.pk}
        )

        self.assertContains(response, "1234")
        self.assertNotContains(response, "supergeheim")

    def test_fuellt_die_neue_fassung_aus_der_aktiven_ohne_token(self) -> None:
        """Wer nur die Sprache wechselt, tippt den Rest nicht neu."""
        TranskriptionsKonfiguration.objects.aktivieren(_openrouter_fassung())

        formular = self.client.get(reverse(SEITE)).context["form"]

        self.assertEqual(
            (
                formular["anbieter"].value(),
                formular["transkriptionsmodell"].value(),
                formular["anbieter_token"].value(),
            ),
            (Anbieter.OPENROUTER, "whisper-large-v3", ""),
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
    """Der Adapter entsteht je Anfrage aus der übergebenen Fassung."""

    def test_bildet_den_adapter_aus_der_fassung(self) -> None:
        """Welche Fassung gilt, entscheidet der Aufrufer, nicht der Zeiger."""
        fassung: TranskriptionsKonfiguration = _openrouter_fassung()

        with patch("simulation.transkription.OpenAI") as openai:
            openai.return_value.audio.transcriptions.create.return_value.text = "Hallo."
            transkriptions_anbieter(fassung).transkribieren(b"audio")

        self.assertEqual(
            openai.return_value.audio.transcriptions.create.call_args.kwargs["model"],
            "whisper-large-v3",
        )

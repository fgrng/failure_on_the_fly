"""Die Zero-Retention-Erklärung an der Transkriptions-Fassung, über die Seite."""

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import erklaerte, konto_mit_rollen, transkriptions_fassung
from konten.models import Konto
from simulation.forms import ZERO_RETENTION_HAEKCHEN_FEHLT_FEHLERMELDUNG
from simulation.models import Anbieter, TranskriptionsKonfiguration

SEITE: str = "simulation:transkriptions_konfiguration"
ERKLAEREN: str = "simulation:transkriptions_konfiguration_erklaeren"
WIDERRUFEN: str = "simulation:transkriptions_konfiguration_widerrufen"
AKTIVIEREN: str = "simulation:transkriptions_konfiguration_aktivieren"


def _eingabe(**werte: object) -> dict[str, object]:
    # Ein vollständig ausgefülltes Formular einer neuen Fassung.

    return {
        "anbieter": Anbieter.OPENROUTER,
        "anbieter_token": "sk-or-supergeheim1234",
        "transkriptionsmodell": "whisper-large-v3",
        "sprache": "de",
        **werte,
    }


def _detail_url(fassung: TranskriptionsKonfiguration) -> str:
    # Die Seite mit der Fassung im Detail.

    return f"{reverse(SEITE)}?fassung={fassung.pk}"


class TranskriptionsErklaerungRollenTests(TestCase):
    """Erklären und Widerrufen liegen hinter der Administrationsrolle."""

    def setUp(self) -> None:
        """Meldet eine Autorin ohne Administrationsrolle an."""
        self.fassung: TranskriptionsKonfiguration = transkriptions_fassung()
        self.client.force_login(konto_mit_rollen("ada", "Autor:in"))

    def test_weist_autorin_beim_erklaeren_ab(self) -> None:
        """Nur die Administration gibt eine Erklärung ab."""
        response: HttpResponse = self.client.post(
            reverse(ERKLAEREN, args=[self.fassung.pk]),
            {"zero_retention_beleg": "AVV"},
        )

        self.assertEqual(response.status_code, 403)
        self.fassung.refresh_from_db()
        self.assertFalse(self.fassung.zero_retention_erklaert)

    def test_weist_autorin_beim_widerrufen_ab(self) -> None:
        """Nur die Administration widerruft eine Erklärung."""
        erklaerte(self.fassung)

        response: HttpResponse = self.client.post(
            reverse(WIDERRUFEN, args=[self.fassung.pk]),
            {"zero_retention_widerrufsgrund": "Zusage zurückgezogen"},
        )

        self.assertEqual(response.status_code, 403)
        self.fassung.refresh_from_db()
        self.assertTrue(self.fassung.zero_retention_erklaert)


class TranskriptionsErklaerungTests(TestCase):
    """Die Erklärung entsteht beim Anlegen oder nachträglich, nach denselben Regeln."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.linus: Konto = konto_mit_rollen("linus", is_superuser=True)
        self.client.force_login(self.linus)

    def test_gibt_die_erklaerung_beim_anlegen_ab(self) -> None:
        """Zeitpunkt und Konto schreibt die Anlegen-Geste selbst mit."""
        self.client.post(
            reverse(SEITE),
            _eingabe(
                zero_retention_erklaert="on", zero_retention_beleg="AVV vom 01.10."
            ),
        )

        fassung: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.latest("pk")
        )
        self.assertTrue(fassung.zero_retention_erklaert)
        self.assertEqual(fassung.zero_retention_beleg, "AVV vom 01.10.")
        self.assertEqual(fassung.zero_retention_erklaert_von, self.linus)
        self.assertIsNotNone(fassung.zero_retention_erklaert_am)

    def test_meldet_den_fehlenden_beleg_beim_anlegen_am_feld(self) -> None:
        """Ein Häkchen ohne Beleg ist nicht nachprüfbar."""
        response: HttpResponse = self.client.post(
            reverse(SEITE),
            _eingabe(zero_retention_erklaert="on", zero_retention_beleg=""),
        )

        self.assertFormError(
            response.context["form"],
            "zero_retention_beleg",
            "Ohne Beleg der Zusage ist die Erklärung nicht nachprüfbar.",
        )
        self.assertEqual(len(response.context["fassungen"]), 1)

    def test_meldet_den_beleg_ohne_haekchen_am_haekchen(self) -> None:
        """Die Erklärung ist eine eigene Geste; ein Beleg allein geht nicht verloren."""
        response: HttpResponse = self.client.post(
            reverse(SEITE), _eingabe(zero_retention_beleg="AVV")
        )

        self.assertFormError(
            response.context["form"],
            "zero_retention_erklaert",
            ZERO_RETENTION_HAEKCHEN_FEHLT_FEHLERMELDUNG,
        )
        self.assertEqual(len(response.context["fassungen"]), 1)

    def test_weist_die_erklaerung_bei_fake_beim_anlegen_ab(self) -> None:
        """Über einen Auftragsverarbeiter, den es nicht gibt, wird nichts erklärt."""
        response: HttpResponse = self.client.post(
            reverse(SEITE),
            _eingabe(
                anbieter=Anbieter.FAKE,
                anbieter_token="",
                transkriptionsmodell="",
                zero_retention_erklaert="on",
                zero_retention_beleg="AVV",
            ),
        )

        self.assertIn("zero_retention_beleg", response.context["form"].errors)
        self.assertEqual(len(response.context["fassungen"]), 1)

    def test_gibt_die_erklaerung_nachtraeglich_ab(self) -> None:
        """Eine Fassung ohne Erklärung bekommt sie im Detail."""
        fassung: TranskriptionsKonfiguration = transkriptions_fassung()

        response: HttpResponse = self.client.post(
            reverse(ERKLAEREN, args=[fassung.pk]),
            {"zero_retention_beleg": "AVV vom 01.10."},
            follow=True,
        )

        self.assertRedirects(response, _detail_url(fassung))
        self.assertContains(
            response,
            f"Für die Fassung Nr. {fassung.pk} ist die Zero-Retention-Erklärung "
            "abgegeben.",
        )
        fassung.refresh_from_db()
        self.assertTrue(fassung.zero_retention_erklaert)
        self.assertEqual(fassung.zero_retention_erklaert_von, self.linus)

    def test_meldet_den_fehlenden_beleg_beim_nachtraeglichen_erklaeren(self) -> None:
        """Auch nachträglich gibt es keine Erklärung ohne Beleg."""
        fassung: TranskriptionsKonfiguration = transkriptions_fassung()

        response: HttpResponse = self.client.post(
            reverse(ERKLAEREN, args=[fassung.pk]), {"zero_retention_beleg": "  "}
        )

        self.assertFormError(
            response.context["erklaerungsformular"],
            "zero_retention_beleg",
            "Ohne Beleg der Zusage ist die Erklärung nicht nachprüfbar.",
        )
        fassung.refresh_from_db()
        self.assertFalse(fassung.zero_retention_erklaert)

    def test_weist_die_nachtraegliche_erklaerung_bei_fake_ab(self) -> None:
        """Die Regel gilt auch, wenn jemand die Geste ohne Formular aufruft."""
        fake: TranskriptionsKonfiguration = TranskriptionsKonfiguration.objects.aktive()

        response: HttpResponse = self.client.post(
            reverse(ERKLAEREN, args=[fake.pk]),
            {"zero_retention_beleg": "AVV"},
            follow=True,
        )

        self.assertContains(response, "keine Zero-Retention-Erklärung zulässig")
        fake.refresh_from_db()
        self.assertFalse(fake.zero_retention_erklaert)

    def test_aendert_eine_abgegebene_erklaerung_nicht(self) -> None:
        """Beleg und Zeitpunkt der ersten Erklärung bleiben stehen."""
        fassung: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())
        beleg: str = fassung.zero_retention_beleg

        response: HttpResponse = self.client.post(
            reverse(ERKLAEREN, args=[fassung.pk]),
            {"zero_retention_beleg": "Neuer Beleg"},
            follow=True,
        )

        self.assertContains(response, "lässt sich nicht ändern")
        fassung.refresh_from_db()
        self.assertEqual(fassung.zero_retention_beleg, beleg)

    def test_bietet_die_erklaerung_nur_an_einer_nicht_erklaerten_fassung_an(
        self,
    ) -> None:
        """Erklärte und `fake`-Fassungen zeigen kein Erklärungsformular."""
        fake: TranskriptionsKonfiguration = TranskriptionsKonfiguration.objects.aktive()
        offen: TranskriptionsKonfiguration = transkriptions_fassung()
        erklaert: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())

        for fassung, angeboten in ((offen, True), (erklaert, False), (fake, False)):
            with self.subTest(fassung=fassung.pk):
                response: HttpResponse = self.client.get(_detail_url(fassung))

                if angeboten:
                    self.assertContains(response, reverse(ERKLAEREN, args=[fassung.pk]))
                else:
                    self.assertNotContains(
                        response, reverse(ERKLAEREN, args=[fassung.pk])
                    )

    def test_zeigt_beleg_und_erklaerendes_konto_im_detail(self) -> None:
        """Wer die Seite liest, sieht, worauf sich die Zusage stützt."""
        fassung: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())

        response: HttpResponse = self.client.get(_detail_url(fassung))

        self.assertContains(response, fassung.zero_retention_beleg)
        self.assertContains(response, str(fassung.zero_retention_erklaert_von))

    def test_zeigt_den_erklaerungsstand_je_fassung(self) -> None:
        """Die Liste nennt je Fassung, ob die Erklärung vorliegt, fehlt oder entfällt."""
        fake: TranskriptionsKonfiguration = TranskriptionsKonfiguration.objects.aktive()
        offen: TranskriptionsKonfiguration = transkriptions_fassung()
        erklaert: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())

        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertEqual(
            [
                (zeile.pk, zeile.erklaerungsstand)
                for zeile in response.context["fassungen"]
            ],
            [
                (erklaert.pk, "erklärt"),
                (offen.pk, "fehlt"),
                (fake.pk, "nicht nötig"),
            ],
        )


class TranskriptionsWiderrufTests(TestCase):
    """Eine abgegebene Erklärung lässt sich mit Grund widerrufen, einmal."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.linus: Konto = konto_mit_rollen("linus", is_superuser=True)
        self.client.force_login(self.linus)

    def _widerrufen(
        self, fassung: TranskriptionsKonfiguration, grund: str = "Zusage zurückgezogen"
    ) -> HttpResponse:
        # Widerruft über die Seite und folgt der Umleitung.
        return self.client.post(
            reverse(WIDERRUFEN, args=[fassung.pk]),
            {"zero_retention_widerrufsgrund": grund},
            follow=True,
        )

    def test_widerruft_die_erklaerung_mit_grund(self) -> None:
        """Grund, Zeitpunkt und Konto stehen danach an der Fassung."""
        fassung: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())

        response: HttpResponse = self._widerrufen(fassung)

        self.assertRedirects(response, _detail_url(fassung))
        self.assertContains(response, "ist die Zero-Retention-Erklärung widerrufen")
        fassung.refresh_from_db()
        self.assertFalse(fassung.zero_retention_erklaert)
        self.assertEqual(fassung.zero_retention_widerrufsgrund, "Zusage zurückgezogen")
        self.assertEqual(fassung.zero_retention_widerrufen_von, self.linus)
        self.assertIsNotNone(fassung.zero_retention_widerrufen_am)

    def test_meldet_den_fehlenden_grund_am_feld(self) -> None:
        """Ohne Grund kein Widerruf."""
        fassung: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())

        response: HttpResponse = self.client.post(
            reverse(WIDERRUFEN, args=[fassung.pk]),
            {"zero_retention_widerrufsgrund": "  "},
        )

        self.assertFormError(
            response.context["widerrufsformular"],
            "zero_retention_widerrufsgrund",
            "Ohne Grund ist der Widerruf nicht nachvollziehbar.",
        )
        fassung.refresh_from_db()
        self.assertTrue(fassung.zero_retention_erklaert)

    def test_weist_den_widerruf_ohne_abgegebene_erklaerung_ab(self) -> None:
        """Eine nie abgegebene Erklärung lässt sich nicht widerrufen."""
        fassung: TranskriptionsKonfiguration = transkriptions_fassung()

        response: HttpResponse = self._widerrufen(fassung)

        self.assertContains(response, "gibt es nichts zu widerrufen")
        fassung.refresh_from_db()
        self.assertIsNone(fassung.zero_retention_widerrufen_am)

    def test_zeigt_den_widerruf_im_detail_und_in_der_liste(self) -> None:
        """Der Widerruf bleibt mit Grund sichtbar; erklären lässt sich nicht mehr."""
        fassung: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())
        self._widerrufen(fassung, "Kein ZDR mehr")

        response: HttpResponse = self.client.get(_detail_url(fassung))

        self.assertContains(response, "Kein ZDR mehr")
        self.assertContains(response, "widerrufen am")
        self.assertNotContains(response, reverse(ERKLAEREN, args=[fassung.pk]))
        self.assertNotContains(response, reverse(WIDERRUFEN, args=[fassung.pk]))

    def test_weist_die_aktivierung_einer_widerrufenen_fassung_ab(self) -> None:
        """Eine weggefallene Zusage kommt nicht versehentlich wieder in Gebrauch."""
        fassung: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())
        self._widerrufen(fassung)

        response: HttpResponse = self.client.post(
            reverse(AKTIVIEREN, args=[fassung.pk]), follow=True
        )

        self.assertContains(response, "lässt sich nicht mehr aktivieren")
        self.assertNotEqual(TranskriptionsKonfiguration.objects.aktive(), fassung)
        self.assertNotContains(response, reverse(AKTIVIEREN, args=[fassung.pk]))

    def test_warnt_bei_widerrufener_aktiver_fassung(self) -> None:
        """Der Widerruf schließt das Tor; die Seite sagt es deutlich."""
        fassung: TranskriptionsKonfiguration = erklaerte(transkriptions_fassung())
        TranskriptionsKonfiguration.objects.aktivieren(fassung)
        self._widerrufen(fassung)

        response: HttpResponse = self.client.get(reverse(SEITE))

        self.assertContains(response, "Die Spracheingabe ist aus")

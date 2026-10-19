"""HTTP-Vertrag des Transkriptions-Endpunkts der Trainingssitzung."""

from collections.abc import Callable

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    erklaerte_aktive_transkription,
    finale_vignette,
    konto_mit_rollen,
    transkriptions_fassung,
)
from konten.models import Konto
from simulation.models import TranskriptionsKonfiguration, Verwendung
from simulation.transkription import FakeTranskription, Transkription
from sitzungen.models import Gespraechsschritt, Sitzung
from sitzungen.views import transkriptions_endpunkt
from sitzungen.tests.aufnahme import audioaufnahme
from training.models import Training
from training.views import laufende_training_sitzung
from vignetten.models import Vignette


class TranskriptionsEndpointTests(TestCase):
    """Eine eingewilligte Trainingssitzung kann Audio transkribieren lassen."""

    def setUp(self) -> None:
        """Öffnet das Tor: Eine erklärte Fassung ist aktiv."""
        self.fassung: TranskriptionsKonfiguration = erklaerte_aktive_transkription()

    def _sitzung_starten(self) -> Sitzung:
        # Startet die zur Transkription berechtigte Trainingssitzung über HTTP.
        ausbilderin: Konto = konto_mit_rollen("ada")
        teilnehmerin: Konto = konto_mit_rollen("grace")
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        vignette: Vignette = finale_vignette(ausbilderin)
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        training.vignette_aufnehmen(vignette)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.client.post(reverse("training:wahl", args=[training.pk, vignette.pk]))
        self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "ja"},
        )
        return Sitzung.objects.get()

    def _anfragen(self, sitzung: Sitzung, anbieter: FakeTranskription) -> HttpResponse:
        # Ruft den Endpunkt mit einer Fabrik auf, die diesen einen Anbieter gibt.
        return self._anfragen_mit_fabrik(sitzung, lambda _: anbieter)

    def _anfragen_mit_fabrik(
        self,
        sitzung: Sitzung,
        fabrik: Callable[[TranskriptionsKonfiguration], Transkription],
    ) -> HttpResponse:
        # Ruft den Endpunkt mit einer Fabrik auf, die den Anbieter je Fassung bildet.
        request: HttpRequest = RequestFactory().post(
            reverse("training:transkription", args=[sitzung.pk]),
            {"audio": audioaufnahme()},
        )
        request.user = get_user_model().objects.get(username="grace")
        request.session = self.client.session
        try:
            return transkriptions_endpunkt(fabrik, laufende_training_sitzung)(
                request, pk=sitzung.pk
            )
        finally:
            request.close()

    def _fassung_der_anfrage(self, sitzung: Sitzung) -> TranskriptionsKonfiguration:
        # Die Fassung, aus der der Endpunkt den Adapter bilden lässt.
        gebildet_aus: list[TranskriptionsKonfiguration] = []

        def fabrik(konfiguration: TranskriptionsKonfiguration) -> FakeTranskription:
            gebildet_aus.append(konfiguration)
            return FakeTranskription(["Text"])

        self.assertEqual(self._anfragen_mit_fabrik(sitzung, fabrik).status_code, 200)
        return gebildet_aus[0]

    def test_transkribiert_nach_einem_wechsel_mit_der_gepinnten_fassung(self) -> None:
        """Die Aufnahmen einer Sitzung gehen immer an denselben Anbieter."""
        sitzung: Sitzung = self._sitzung_starten()
        gepinnt: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.aktive()
        )

        erklaerte_aktive_transkription()

        self.assertEqual(self._fassung_der_anfrage(sitzung), gepinnt)

    def test_eine_danach_gestartete_sitzung_nimmt_die_neue_fassung(self) -> None:
        """Ein Wechsel wirkt ab der nächsten Sitzung."""
        neue: TranskriptionsKonfiguration = erklaerte_aktive_transkription()

        sitzung: Sitzung = self._sitzung_starten()

        self.assertEqual(self._fassung_der_anfrage(sitzung), neue)

    def test_eine_sitzung_von_vor_dem_pin_folgt_der_aktiven_fassung(self) -> None:
        """Ohne gepinnte Fassung gilt, was gerade aktiv ist."""
        sitzung: Sitzung = self._sitzung_starten()
        Sitzung.objects.filter(pk=sitzung.pk).update(transkriptions_konfiguration=None)
        sitzung.refresh_from_db()

        neue: TranskriptionsKonfiguration = erklaerte_aktive_transkription()

        self.assertEqual(self._fassung_der_anfrage(sitzung), neue)

    def test_ein_widerruf_schliesst_das_tor_mitten_in_der_sitzung(self) -> None:
        """Maßgeblich ist der Erklärungsstand bei der Anfrage, nicht beim Start."""
        sitzung: Sitzung = self._sitzung_starten()
        self.fassung.zero_retention_widerrufen(
            "Zusage zurückgezogen", konto_mit_rollen("linus", is_superuser=True)
        )
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(sitzung, anbieter)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "zero_retention_fehlt"})
        self.assertEqual(anbieter.skript, ["Text"])

    def test_ein_wechsel_auf_eine_erklaerte_fassung_oeffnet_die_sitzung_nicht(
        self,
    ) -> None:
        """Die gepinnte Fassung entscheidet, nicht die inzwischen aktive."""
        TranskriptionsKonfiguration.objects.aktivieren(
            TranskriptionsKonfiguration.objects.create()
        )
        sitzung: Sitzung = self._sitzung_starten()
        erklaerte_aktive_transkription()
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(sitzung, anbieter)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(anbieter.skript, ["Text"])

    def test_liefert_das_transkript_einer_aufnahme(self) -> None:
        """Audio wird nur in der Anfrage zum Text für das Frontend überführt."""
        sitzung: Sitzung = self._sitzung_starten()

        response: HttpResponse = self._anfragen(
            sitzung, FakeTranskription(["Wie hast du gerechnet?"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"text": "Wie hast du gerechnet?"})
        self.assertFalse(Gespraechsschritt.objects.exists())

    def test_ohne_einwilligung_verweigert_externe_transkription(self) -> None:
        """Ohne Einwilligung wird der Anbieter nicht einmal für Audio aufgerufen."""
        sitzung: Sitzung = self._sitzung_starten()
        sitzung.teilnahme.audioverarbeitung_eingewilligt = False
        sitzung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(sitzung, anbieter)

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {"status": "einwilligung_verweigert"})
        self.assertEqual(anbieter.skript, ["Text"])

    def test_ohne_laufende_sitzung_bleibt_der_endpunkt_verschlossen(self) -> None:
        """Ein Trainingskonto allein berechtigt nicht zur Transkription."""
        sitzung: Sitzung = self._sitzung_starten()
        self.client.post(reverse("training:abbrechen", args=[sitzung.pk]))
        anbieter = FakeTranskription(["Text"])

        with self.assertRaises(PermissionDenied):
            self._anfragen(sitzung, anbieter)

        self.assertEqual(anbieter.skript, ["Text"])

    def test_weist_anonyme_anfrage_ab(self) -> None:
        """Ohne Anmeldung antwortet der Endpunkt mit 403, nicht mit einem Fehler."""
        sitzung: Sitzung = self._sitzung_starten()
        self.client.logout()

        response: HttpResponse = self.client.post(
            reverse("training:transkription", args=[sitzung.pk]),
            {"audio": audioaufnahme()},
        )

        self.assertEqual(response.status_code, 403)


class SpracheingabeTorTests(TestCase):
    """Training fragt und zeigt die Spracheingabe nur bei offenem Tor."""

    def setUp(self) -> None:
        """Eine Teilnehmer:in ist einem Training mit einer Vignette beigetreten."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        vignette: Vignette = finale_vignette(ausbilderin)
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        training.vignette_aufnehmen(vignette)
        training.veroeffentlichen()
        self.client.force_login(konto_mit_rollen("grace"))
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.wahl_url: str = reverse("training:wahl", args=[training.pk, vignette.pk])
        self.einwilligung_url: str = reverse(
            "training:einwilligung", args=[training.pk, vignette.pk]
        )

    def test_startet_bei_fake_fassung_ohne_einwilligungsseite(self) -> None:
        """Eine frische Instanz transkribiert nicht und fragt deshalb nicht."""
        start: HttpResponse = self.client.post(self.wahl_url)

        self.assertContains(start, "Die Ausgangslage")
        self.assertNotContains(start, "data-spracheingabe")

    def test_startet_bei_unerklaerter_fassung_ohne_einwilligungsseite(self) -> None:
        """Ein echter Anbieter ohne Erklärung hält das Tor ebenso zu."""
        TranskriptionsKonfiguration.objects.aktivieren(transkriptions_fassung())

        start: HttpResponse = self.client.post(self.wahl_url)

        self.assertContains(start, "Die Ausgangslage")
        self.assertNotContains(start, "data-spracheingabe")

    def test_fragt_nach_dem_oeffnen_des_tors_beim_naechsten_start(self) -> None:
        """Ohne Frage bleibt die Entscheidung offen und wird später nachgeholt."""
        self.client.post(self.wahl_url)
        self.client.post(reverse("training:abbrechen", args=[Sitzung.objects.get().pk]))
        erklaerte_aktive_transkription()

        frage: HttpResponse = self.client.post(self.wahl_url)

        self.assertContains(frage, "Audio zur Transkription")

    def test_fragt_bei_erklaerter_fassung_vor_dem_start(self) -> None:
        """Mit offenem Tor gilt der bisherige Ablauf."""
        erklaerte_aktive_transkription()

        frage: HttpResponse = self.client.post(self.wahl_url)

        self.assertContains(frage, "Audio zur Transkription")

    def test_zeigt_nach_ja_das_mikrofon(self) -> None:
        """Die eingewilligte Sitzung bietet bei offenem Tor die Spracheingabe an."""
        erklaerte_aktive_transkription()
        self.client.post(self.wahl_url)

        start: HttpResponse = self.client.post(
            self.einwilligung_url, {"audioverarbeitung_eingewilligt": "ja"}
        )

        self.assertContains(start, "data-spracheingabe")

    def _eingewilligt_starten_und_widerrufen(self) -> Sitzung:
        # Startet mit offenem Tor und Einwilligung, dann fällt die Erklärung.
        fassung: TranskriptionsKonfiguration = erklaerte_aktive_transkription()
        self.client.post(self.wahl_url)
        self.client.post(
            self.einwilligung_url, {"audioverarbeitung_eingewilligt": "ja"}
        )
        fassung.zero_retention_widerrufen(
            "Zusage zurückgezogen", konto_mit_rollen("linus", is_superuser=True)
        )
        return Sitzung.objects.get()

    def test_ein_widerruf_nimmt_der_naechsten_seite_das_mikrofon(self) -> None:
        """Die laufende Sitzung zeigt bei geschlossenem Tor nur die Tastatur."""
        sitzung: Sitzung = self._eingewilligt_starten_und_widerrufen()

        gespraech: HttpResponse = self.client.get(
            reverse("training:gespraech", args=[sitzung.pk])
        )

        self.assertContains(gespraech, "Ihre nächste Frage")
        self.assertNotContains(gespraech, "data-spracheingabe")

    def test_ein_widerruf_nimmt_dem_debrief_das_mikrofon(self) -> None:
        """Auch der Debrief nimmt die Diagnose dann nur per Tastatur auf."""
        sitzung: Sitzung = self._eingewilligt_starten_und_widerrufen()

        debrief: HttpResponse = self.client.post(
            reverse("training:gespraech_beenden", args=[sitzung.pk])
        )

        self.assertContains(debrief, "Ihre Diagnose")
        self.assertNotContains(debrief, "data-spracheingabe")

"""HTTP-Vertrag des Transkriptions-Endpunkts der Trainingssitzung."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from konten.models import Konto
from simulation.models import Verwendung
from simulation.transkription import FakeTranskription
from sitzungen.models import Gespraechsschritt, Sitzung
from sitzungen.views import transkriptions_endpunkt
from training.models import Training
from training.views import training_sitzung
from vignetten.models import Vignette


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class TranskriptionsEndpointTests(TestCase):
    """Eine eingewilligte Trainingssitzung kann Audio transkribieren lassen."""

    def _aufnahme(self) -> SimpleUploadedFile:
        # Erzeugt für jede Anfrage eine frische Datei, weil Django sie einliest.
        return SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")

    def _sitzung_starten(self) -> Sitzung:
        # Startet die zur Transkription berechtigte Trainingssitzung über HTTP.
        ausbilderin: Konto = konto_mit_rollen("ada")
        teilnehmerin: Konto = konto_mit_rollen("grace")
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        vignette: Vignette = finale_vignette(ausbilderin)
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.client.post(reverse("training:wahl", args=[training.pk, vignette.pk]))
        self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "ja"},
        )
        return Sitzung.objects.get()

    def _anfragen(self, anbieter: FakeTranskription) -> HttpResponse:
        request: HttpRequest = RequestFactory().post(
            "/training/sitzung/transkription/", {"audio": self._aufnahme()}
        )
        request.user = get_user_model().objects.get(username="grace")
        request.session = self.client.session
        try:
            return transkriptions_endpunkt(lambda: anbieter, training_sitzung)(request)
        finally:
            request.close()

    def test_liefert_das_transkript_einer_aufnahme(self) -> None:
        """Audio wird nur in der Anfrage zum Text für das Frontend überführt."""
        self._sitzung_starten()

        response: HttpResponse = self._anfragen(
            FakeTranskription(["Wie hast du gerechnet?"])
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

        response: HttpResponse = self._anfragen(anbieter)

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {"status": "einwilligung_verweigert"})
        self.assertEqual(anbieter.skript, ["Text"])

    def test_ohne_laufende_sitzung_bleibt_der_endpunkt_verschlossen(self) -> None:
        """Ein Trainingskonto allein berechtigt nicht zur Transkription."""
        self._sitzung_starten()
        self.client.post(reverse("training:abbrechen"))
        anbieter = FakeTranskription(["Text"])

        with self.assertRaises(PermissionDenied):
            self._anfragen(anbieter)

        self.assertEqual(anbieter.skript, ["Text"])

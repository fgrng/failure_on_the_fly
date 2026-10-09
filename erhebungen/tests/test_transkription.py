"""HTTP-Vertrag des Transkriptions-Endpunkts der Erhebungsteilnahme."""

from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from config.tests.aufbau import aktive_modell_konfiguration, finale_vignette
from erhebungen.models import Erhebung, Erhebungsbindung, Erhebungsvignette, Stichprobe
from erhebungen.views import sitzung_fuer_transkription
from konten.models import Konto
from simulation.models import Verwendung
from simulation.transkription import FakeTranskription
from sitzungen.models import Sitzung
from sitzungen.views import transkriptions_endpunkt


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class ErhebungsTranskriptionTests(TestCase):
    """Eine Erhebungsteilnahme autorisiert Audio ohne ein Nutzerkonto."""

    def setUp(self) -> None:
        """Startet eine laufende, pseudonyme Erhebungssitzung über den Teilnahme-Link."""
        forscherin: Konto = Konto.objects.create_user(username="ada")
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        erhebung: Erhebung = Erhebung.objects.anlegen(forscherin, name="Audioerhebung")
        Erhebungsvignette.objects.create(
            erhebung=erhebung, vignette=finale_vignette(forscherin), position=1
        )
        erhebung.finalisieren()
        self.stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(minutes=1),
            ende=timezone.now() + timedelta(minutes=1),
        )
        link = self.stichprobe.teilnahme_link
        self.client.get(reverse("erhebungen:teilnehmen", args=[link]))
        self.client.post(
            reverse("erhebungen:einwilligung", args=[link]),
            {
                "sprachmodell_eingewilligt": "ja",
                "audioverarbeitung_eingewilligt": "ja",
                "speicherung_eingewilligt": "ja",
            },
        )
        self.client.post(reverse("erhebungen:spielen", args=[link]))
        self.bindung: Erhebungsbindung = Erhebungsbindung.objects.get()
        self.sitzung: Sitzung = Sitzung.objects.get()

    def _aufnahme(self) -> SimpleUploadedFile:
        # Erzeugt für jede Anfrage eine frische Datei, weil Django sie einliest.
        return SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")

    def _anfragen(self, anbieter: FakeTranskription, sitzung: Sitzung) -> HttpResponse:
        # Ruft den Endpunkt pseudonym auf, so wie es die Teilnahme tut.
        request: HttpRequest = RequestFactory().post(
            "/erhebungen/teilnahme/transkription/",
            {"audio": self._aufnahme(), "sitzung_pk": sitzung.pk},
        )
        request.user = AnonymousUser()
        request.session = self.client.session
        try:
            return transkriptions_endpunkt(
                lambda: anbieter, sitzung_fuer_transkription
            )(request)
        finally:
            request.close()

    def test_eingewilligte_teilnahme_transkribiert_ohne_konto(self) -> None:
        """Das Browser-Token allein berechtigt die pseudonyme Teilnehmer:in."""
        response: HttpResponse = self._anfragen(
            FakeTranskription(["Wie rechnest du?"]), self.sitzung
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"text": "Wie rechnest du?"})

    def test_ohne_einwilligung_verweigert_externe_transkription(self) -> None:
        """Ein widerrufenes Einverständnis schließt den Endpunkt sofort."""
        self.bindung.teilnahme.audioverarbeitung_eingewilligt = False
        self.bindung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(anbieter, self.sitzung)

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {"status": "einwilligung_verweigert"})
        self.assertEqual(anbieter.skript, ["Text"])

    def test_fremde_sitzung_bleibt_dem_token_verschlossen(self) -> None:
        """Ein Token spricht ausschließlich für die eigene Sitzung."""
        fremde_bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(
            self.stichprobe
        )
        fremde_sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=fremde_bindung.teilnahme,
            vignette=self.sitzung.vignette,
            simulationskern=self.sitzung.simulationskern,
            modell_konfiguration=self.sitzung.modell_konfiguration,
        )
        anbieter = FakeTranskription(["Text"])

        with self.assertRaises(PermissionDenied):
            self._anfragen(anbieter, fremde_sitzung)

        self.assertEqual(anbieter.skript, ["Text"])

    def test_nach_fensterende_bleibt_der_endpunkt_verschlossen(self) -> None:
        """Nach dem Ende der Stichprobe autorisiert das Token keine Aufnahme mehr."""
        self.stichprobe.ende = timezone.now() - timedelta(seconds=1)
        self.stichprobe.save(update_fields=["ende"])
        anbieter = FakeTranskription(["Text"])

        with self.assertRaises(PermissionDenied):
            self._anfragen(anbieter, self.sitzung)

        self.assertEqual(anbieter.skript, ["Text"])

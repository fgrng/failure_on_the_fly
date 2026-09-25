"""HTTP-Vertrag des Transkriptions-Endpunkts der Erhebungsteilnahme."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from erhebungen.models import Erhebung, Erhebungsbindung, Stichprobe
from erhebungen.views import sitzung_fuer_transkription
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from simulation.transkription import FakeTranskription
from sitzungen.models import Sitzung
from sitzungen.views import transkriptions_endpunkt
from vignetten.models import Vignette, Vignettenhistorie


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class ErhebungsTranskriptionTests(TestCase):
    """Eine Erhebungsteilnahme autorisiert Audio ohne ein Nutzerkonto."""

    def setUp(self) -> None:
        """Legt eine laufende, pseudonyme Erhebungssitzung samt Token an."""
        forscherin: Konto = get_user_model().objects.create_user(username="ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test", sprachmodell="fake"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(name="Brüche")
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Addiere zwei Brüche.",
            arbeitsheft_text="1/2 + 1/3 = 2/5",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Weber",
            lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
            gepinnter_kern=kern,
        )
        erhebung: Erhebung = Erhebung.objects.anlegen(forscherin, name="Audioerhebung")
        erhebung.finalisieren()
        self.stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(minutes=1),
            ende=timezone.now() + timedelta(minutes=1),
        )
        self.bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(
            self.stichprobe
        )
        self.bindung.teilnahme.audioverarbeitung_eingewilligt = True
        self.bindung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])
        self.sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=self.bindung.teilnahme,
            vignette=vignette,
            simulationskern=kern,
            modell_konfiguration=konfiguration,
        )
        session: SessionBase = self.client.session
        session["erhebung_teilnahme_tokens"] = {
            str(self.stichprobe.teilnahme_link): self.bindung.token
        }
        session.save()

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

    @override_settings(TRANSKRIPTION_ZERO_RETENTION=False)
    def test_ohne_zero_retention_verweigert_externe_transkription(self) -> None:
        """Ohne vertragliche Zusicherung wird der Anbieter nicht aufgerufen."""
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(anbieter, self.sitzung)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "zero_retention_fehlt"})
        self.assertEqual(anbieter.skript, ["Text"])

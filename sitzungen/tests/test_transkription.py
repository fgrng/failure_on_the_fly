"""HTTP-Vertrag des Transkriptions-Endpunkts."""

from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from erhebungen.models import Erhebung, Erhebungsbindung, Stichprobe
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.transkription import (
    AnbieterNichtErreichbar,
    FakeTranskription,
    LeeresTranskript,
    TranskriptionsAnbieterfehler,
)
from sitzungen.models import Gespraechsschritt, Sitzung, Teilnahme
from sitzungen.views import transkriptions_endpunkt
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette, Vignettenhistorie


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class TranskriptionsEndpointTests(TestCase):
    """Eine eingewilligte Trainingssitzung kann Audio transkribieren lassen."""

    def _aufnahme(self) -> SimpleUploadedFile:
        # Erzeugt für jede Anfrage eine frische Datei, weil Django sie einliest.
        return SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")

    def _sitzung_starten(self) -> Sitzung:
        # Richtet die zur Transkription berechtigte Trainingssitzung ein.
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        teilnehmerin: Konto = get_user_model().objects.create_user(username="grace")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake"
        )
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(name="Brüche")
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="1/2 + 1/3 = 2/5",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Weber",
            lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
            gepinnter_kern=kern,
        )
        teilnahme: Teilnahme = Teilnahme.objects.create(
            audioverarbeitung_eingewilligt=True
        )
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        Trainingsbindung.objects.create(
            training=training, teilnahme=teilnahme, konto=teilnehmerin
        )
        sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=teilnahme,
            vignette=vignette,
            simulationskern=kern,
            modell_konfiguration=konfiguration,
        )
        self.client.force_login(teilnehmerin)
        session: SessionBase = self.client.session
        session["training_sitzung_pk"] = sitzung.pk
        session.save()
        return sitzung

    def _anfragen(self, anbieter: FakeTranskription) -> HttpResponse:
        request: HttpRequest = RequestFactory().post(
            "/sitzungen/transkription/", {"audio": self._aufnahme()}
        )
        request.user = get_user_model().objects.get(username="grace")
        request.session = self.client.session
        try:
            return transkriptions_endpunkt(anbieter)(request)
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

    def test_reicht_anbieterfehler_als_unterscheidbare_zustaende_durch(self) -> None:
        """Das Frontend kann jede fehlgeschlagene Aufnahme einzeln behandeln."""
        self._sitzung_starten()
        faelle: list[tuple[Exception, int, str]] = [
            (LeeresTranskript(), 422, "leeres_transkript"),
            (TranskriptionsAnbieterfehler(), 502, "anbieterfehler"),
            (AnbieterNichtErreichbar(), 503, "anbieter_nicht_erreichbar"),
        ]

        for fehler, status_code, status in faelle:
            with self.subTest(status=status):
                response: HttpResponse = self._anfragen(FakeTranskription([fehler]))

                self.assertEqual(response.status_code, status_code)
                self.assertJSONEqual(response.content, {"status": status})
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

    def test_pseudonyme_erhebungssitzung_darf_eingewilligt_transkribieren(self) -> None:
        """Eine Erhebungsteilnahme autorisiert Audio ohne ein Nutzerkonto."""

        trainingssitzung: Sitzung = self._sitzung_starten()
        konfiguration: ModellKonfiguration = trainingssitzung.modell_konfiguration
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.create(
            name="Audioerhebung",
            eigentuemerin=get_user_model().objects.get(username="ada"),
        )
        erhebung.finalisieren()
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(minutes=1),
            ende=timezone.now() + timedelta(minutes=1),
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)
        bindung.teilnahme.audioverarbeitung_eingewilligt = True
        bindung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])
        sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=bindung.teilnahme,
            vignette=trainingssitzung.vignette,
            simulationskern=trainingssitzung.simulationskern,
            modell_konfiguration=konfiguration,
        )
        self.client.logout()
        session: SessionBase = self.client.session
        session["erhebung_teilnahme_tokens"] = {
            str(stichprobe.teilnahme_link): bindung.token
        }
        session.save()
        request: HttpRequest = RequestFactory().post(
            "/sitzungen/transkription/",
            {"audio": self._aufnahme(), "sitzung_pk": sitzung.pk},
        )
        request.user = AnonymousUser()
        request.session = self.client.session
        try:
            response: HttpResponse = transkriptions_endpunkt(
                FakeTranskription(["Wie rechnest du?"])
            )(request)
        finally:
            request.close()

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"text": "Wie rechnest du?"})

        angemeldete_anfrage: HttpRequest = RequestFactory().post(
            "/sitzungen/transkription/",
            {"audio": self._aufnahme(), "sitzung_pk": sitzung.pk},
        )
        angemeldete_anfrage.user = get_user_model().objects.get(username="grace")
        angemeldete_anfrage.session = self.client.session
        try:
            angemeldete_antwort: HttpResponse = transkriptions_endpunkt(
                FakeTranskription(["Noch eine Frage"])
            )(angemeldete_anfrage)
        finally:
            angemeldete_anfrage.close()

        self.assertEqual(angemeldete_antwort.status_code, 200)
        self.assertJSONEqual(angemeldete_antwort.content, {"text": "Noch eine Frage"})

        bindung.teilnahme.audioverarbeitung_eingewilligt = False
        bindung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])
        abgelehnte_anfrage: HttpRequest = RequestFactory().post(
            "/sitzungen/transkription/",
            {"audio": self._aufnahme(), "sitzung_pk": sitzung.pk},
        )
        abgelehnte_anfrage.user = AnonymousUser()
        abgelehnte_anfrage.session = self.client.session
        try:
            abgelehnte_antwort: HttpResponse = transkriptions_endpunkt(
                FakeTranskription(["Text"])
            )(abgelehnte_anfrage)
        finally:
            abgelehnte_anfrage.close()

        self.assertEqual(abgelehnte_antwort.status_code, 403)
        self.assertJSONEqual(
            abgelehnte_antwort.content, {"status": "einwilligung_verweigert"}
        )

        fremdebindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)
        fremde_sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=fremdebindung.teilnahme,
            vignette=trainingssitzung.vignette,
            simulationskern=trainingssitzung.simulationskern,
            modell_konfiguration=konfiguration,
        )
        fremde_anfrage: HttpRequest = RequestFactory().post(
            "/sitzungen/transkription/",
            {"audio": self._aufnahme(), "sitzung_pk": fremde_sitzung.pk},
        )
        fremde_anfrage.user = AnonymousUser()
        fremde_anfrage.session = self.client.session
        try:
            with self.assertRaises(PermissionDenied):
                transkriptions_endpunkt(FakeTranskription(["Text"]))(fremde_anfrage)
        finally:
            fremde_anfrage.close()

    @override_settings(TRANSKRIPTION_ZERO_RETENTION=False)
    def test_ohne_zero_retention_verweigert_externe_transkription(self) -> None:
        """Ohne vertragliche Zusicherung wird der Anbieter nicht aufgerufen."""
        self._sitzung_starten()
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(anbieter)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "zero_retention_fehlt"})
        self.assertEqual(anbieter.skript, ["Text"])

    def test_persistiert_keine_aufnahme(self) -> None:
        """Nach der Transkription liegt keine Audio-Datei im Medienverzeichnis."""
        self._sitzung_starten()
        media_root: str
        upload_temp_dir: str
        with TemporaryDirectory() as media_root, TemporaryDirectory() as upload_temp_dir:
            with self.settings(
                MEDIA_ROOT=media_root,
                FILE_UPLOAD_MAX_MEMORY_SIZE=0,
                FILE_UPLOAD_TEMP_DIR=upload_temp_dir,
            ):
                self._anfragen(FakeTranskription(["Text"]))

            self.assertEqual(list(Path(upload_temp_dir).iterdir()), [])
            self.assertEqual(list(Path(media_root).iterdir()), [])

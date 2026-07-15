"""HTTP-Vertrag des Transkriptions-Endpunkts."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import httpx
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.base import SessionBase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from openai import APIConnectionError
from sitzungen.models import Gespraechsschritt, Sitzung, Teilnahme
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

    @patch("simulation.transkription.OpenAI")
    def test_liefert_das_transkript_einer_aufnahme(self, client: MagicMock) -> None:
        """Audio wird nur in der Anfrage zum Text für das Frontend überführt."""
        self._sitzung_starten()
        client.return_value.audio.transcriptions.create.return_value.text = (
            "Wie hast du gerechnet?"
        )

        response: HttpResponse = self.client.post(
            reverse("sitzungen:transkription"),
            {"audio": self._aufnahme()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"text": "Wie hast du gerechnet?"})
        self.assertFalse(Gespraechsschritt.objects.exists())

    @patch("simulation.transkription.OpenAI")
    def test_reicht_anbieterfehler_als_unterscheidbare_zustaende_durch(
        self, client: MagicMock
    ) -> None:
        """Das Frontend kann jede fehlgeschlagene Aufnahme einzeln behandeln."""
        self._sitzung_starten()
        faelle: list[tuple[str | Exception, int, str]] = [
            ("   ", 422, "leeres_transkript"),
            (RuntimeError(), 502, "anbieterfehler"),
            (
                APIConnectionError(
                    request=httpx.Request(
                        "POST", "https://api.openai.com/v1/audio/transcriptions"
                    )
                ),
                503,
                "anbieter_nicht_erreichbar",
            ),
        ]

        for fehler, status_code, status in faelle:
            with self.subTest(status=status):
                anfrage: MagicMock = client.return_value.audio.transcriptions.create
                if isinstance(fehler, Exception):
                    anfrage.side_effect = fehler
                else:
                    anfrage.side_effect = None
                    anfrage.return_value.text = fehler

                response: HttpResponse = self.client.post(
                    reverse("sitzungen:transkription"),
                    {"audio": self._aufnahme()},
                )

                self.assertEqual(response.status_code, status_code)
                self.assertJSONEqual(response.content, {"status": status})
                self.assertFalse(Gespraechsschritt.objects.exists())

    @patch("simulation.transkription.OpenAI")
    def test_ohne_einwilligung_verweigert_externe_transkription(
        self, client: MagicMock
    ) -> None:
        """Ohne Einwilligung wird der Anbieter nicht einmal für Audio aufgerufen."""
        sitzung: Sitzung = self._sitzung_starten()
        sitzung.teilnahme.audioverarbeitung_eingewilligt = False
        sitzung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])

        response: HttpResponse = self.client.post(
            reverse("sitzungen:transkription"),
            {"audio": self._aufnahme()},
        )

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {"status": "einwilligung_verweigert"})
        client.assert_not_called()

    @override_settings(TRANSKRIPTION_ZERO_RETENTION=False)
    @patch("simulation.transkription.OpenAI")
    def test_ohne_zero_retention_verweigert_externe_transkription(
        self, client: MagicMock
    ) -> None:
        """Ohne vertragliche Zusicherung wird der Anbieter nicht aufgerufen."""
        self._sitzung_starten()

        response: HttpResponse = self.client.post(
            reverse("sitzungen:transkription"),
            {"audio": self._aufnahme()},
        )

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "zero_retention_fehlt"})
        client.assert_not_called()

    @patch("simulation.transkription.OpenAI")
    def test_persistiert_keine_aufnahme(self, client: MagicMock) -> None:
        """Nach der Transkription liegt keine Audio-Datei im Medienverzeichnis."""
        self._sitzung_starten()
        client.return_value.audio.transcriptions.create.return_value.text = "Text"
        media_root: str
        upload_temp_dir: str
        with TemporaryDirectory() as media_root, TemporaryDirectory() as upload_temp_dir:
            with self.settings(
                MEDIA_ROOT=media_root,
                FILE_UPLOAD_MAX_MEMORY_SIZE=0,
                FILE_UPLOAD_TEMP_DIR=upload_temp_dir,
            ):
                self.client.post(
                    reverse("sitzungen:transkription"), {"audio": self._aufnahme()}
                )

            self.assertEqual(list(Path(upload_temp_dir).iterdir()), [])
            self.assertEqual(list(Path(media_root).iterdir()), [])

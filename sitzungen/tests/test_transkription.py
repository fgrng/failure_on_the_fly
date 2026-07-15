"""HTTP-Vertrag des Transkriptions-Endpunkts."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.transkription import (
    AnbieterNichtErreichbar,
    FakeTranskription,
    LeeresTranskript,
    TranskriptionsAnbieterfehler,
)
from sitzungen.models import Gespraechsschritt, Sitzung, Teilnahme
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette, Vignettenhistorie


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class TranskriptionsEndpointTests(TestCase):
    """Eine eingewilligte Trainingssitzung kann Audio transkribieren lassen."""

    def _sitzung_starten(self) -> None:
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
        session = self.client.session
        session["training_sitzung_pk"] = sitzung.pk
        session.save()

    @patch("sitzungen.views.OpenAITranskription")
    def test_liefert_das_transkript_einer_aufnahme(self, adapter: MagicMock) -> None:
        """Audio wird nur in der Anfrage zum Text für das Frontend überführt."""
        self._sitzung_starten()
        adapter.return_value = FakeTranskription(["Wie hast du gerechnet?"])

        response: HttpResponse = self.client.post(
            reverse("sitzungen:transkription"),
            {"audio": SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"text": "Wie hast du gerechnet?"})
        self.assertFalse(Gespraechsschritt.objects.exists())

    @patch("sitzungen.views.OpenAITranskription")
    def test_reicht_anbieterfehler_als_unterscheidbare_zustaende_durch(
        self, adapter: MagicMock
    ) -> None:
        """Das Frontend kann jede fehlgeschlagene Aufnahme einzeln behandeln."""
        self._sitzung_starten()
        faelle: list[tuple[Exception, int, str]] = [
            (LeeresTranskript(), 422, "leeres_transkript"),
            (TranskriptionsAnbieterfehler(), 502, "anbieterfehler"),
            (AnbieterNichtErreichbar(), 503, "anbieter_nicht_erreichbar"),
        ]

        for fehler, status_code, status in faelle:
            with self.subTest(status=status):
                adapter.return_value = FakeTranskription([fehler])

                response: HttpResponse = self.client.post(
                    reverse("sitzungen:transkription"),
                    {
                        "audio": SimpleUploadedFile(
                            "aufnahme.webm", b"audio", "audio/webm"
                        )
                    },
                )

                self.assertEqual(response.status_code, status_code)
                self.assertJSONEqual(response.content, {"status": status})

    @patch("sitzungen.views.OpenAITranskription")
    def test_ohne_einwilligung_bleibt_die_aufnahme_beim_server(
        self, adapter: MagicMock
    ) -> None:
        """Ohne Einwilligung wird der Anbieter nicht einmal für Audio aufgerufen."""
        self._sitzung_starten()
        fake: FakeTranskription = FakeTranskription(["Wie hast du gerechnet?"])
        adapter.return_value = fake
        Teilnahme.objects.update(audioverarbeitung_eingewilligt=False)

        verweigert: HttpResponse = self.client.post(
            reverse("sitzungen:transkription"),
            {"audio": SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")},
        )

        self.assertEqual(verweigert.status_code, 403)
        self.assertJSONEqual(verweigert.content, {"status": "einwilligung_verweigert"})
        self.assertEqual(fake.skript, ["Wie hast du gerechnet?"])

    @override_settings(TRANSKRIPTION_ZERO_RETENTION=False)
    @patch("sitzungen.views.OpenAITranskription")
    def test_ohne_zero_retention_bleibt_die_aufnahme_beim_server(
        self, adapter: MagicMock
    ) -> None:
        """Ohne vertragliche Zusicherung wird der Anbieter nicht aufgerufen."""
        self._sitzung_starten()

        response: HttpResponse = self.client.post(
            reverse("sitzungen:transkription"),
            {"audio": SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")},
        )

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "zero_retention_fehlt"})
        adapter.assert_not_called()

    @patch("sitzungen.views.OpenAITranskription")
    def test_persistiert_keine_aufnahme(self, adapter: MagicMock) -> None:
        """Nach der Transkription liegt keine Audio-Datei im Medienverzeichnis."""
        self._sitzung_starten()
        adapter.return_value = FakeTranskription(["Wie hast du gerechnet?"])
        with TemporaryDirectory() as media_root:
            with TemporaryDirectory() as upload_temp_dir:
                with self.settings(
                    MEDIA_ROOT=media_root,
                    FILE_UPLOAD_MAX_MEMORY_SIZE=0,
                    FILE_UPLOAD_TEMP_DIR=upload_temp_dir,
                ):
                    self.client.post(
                        reverse("sitzungen:transkription"),
                        {
                            "audio": SimpleUploadedFile(
                                "aufnahme.webm", b"audio", "audio/webm"
                            )
                        },
                    )

                self.assertEqual(list(Path(upload_temp_dir).iterdir()), [])

            self.assertEqual(list(Path(media_root).iterdir()), [])

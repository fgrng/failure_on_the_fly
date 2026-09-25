"""HTTP-Vertrag des Transkriptions-Endpunkts im schreibfreien Probelauf."""

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from simulation.transkription import (
    AnbieterNichtErreichbar,
    FakeTranskription,
    LeeresTranskript,
    Transkription,
    TranskriptionsAnbieterfehler,
)
from sitzungen.models import Sitzung, Teilnahme
from sitzungen.views import (
    probelauf_sitzung_fuer_transkription,
    transkriptions_endpunkt,
)
from vignetten.models import Vignette


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class ProbelaufTranskriptionTests(TestCase):
    """Der schreibfreie Probelauf transkribiert ohne Teilnahme und Einwilligung."""

    def setUp(self) -> None:
        """Meldet die Autor:in an und legt ihren spielbaren Entwurf an."""
        self.autorin: Konto = get_user_model().objects.create_user(username="ada")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(
                bezeichnung="Test", sprachmodell="fake", parameter={"skript": []}
            ),
            Verwendung.SCHUELERIN,
        )
        self.entwurf: Vignette = Vignette.objects.anlegen(self.autorin)
        # Die Rahmenhandlung braucht beide Akteure für ihre Grammatikformen.
        self.entwurf.schuelerin_name = "Mia"
        self.entwurf.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.lehrperson_name = "Weber"
        self.entwurf.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.save()
        self.client.force_login(self.autorin)

    def _aufnahme(self) -> SimpleUploadedFile:
        # Erzeugt für jede Anfrage eine frische Datei, weil Django sie einliest.
        return SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")

    def _aufnahme_mit_groesse(self, groesse: int) -> SimpleUploadedFile:
        # Der Inhalt ist beliebig; den Endpunkt interessiert allein die Größe.
        return SimpleUploadedFile("aufnahme.webm", b"\0" * groesse, "audio/webm")

    def _probelauf_starten(self) -> None:
        # Legt den Probelaufzustand über die echte HTTP-Naht in der Session ab.
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

    def _anfragen(
        self, anbieter: FakeTranskription, aufnahme: SimpleUploadedFile | None = None
    ) -> HttpResponse:
        # Ruft den Endpunkt mit einer Fabrik auf, die diesen einen Anbieter gibt.
        return self._anfragen_mit_fabrik(lambda: anbieter, aufnahme)

    def _anfragen_mit_fabrik(
        self,
        fabrik: Callable[[], Transkription],
        aufnahme: SimpleUploadedFile | None = None,
    ) -> HttpResponse:
        # Ruft den Endpunkt ohne sitzung_pk auf, so wie es der Probelauf tut.
        request: HttpRequest = RequestFactory().post(
            "/sitzungen/transkription/", {"audio": aufnahme or self._aufnahme()}
        )
        request.user = self.autorin
        request.session = self.client.session
        try:
            return transkriptions_endpunkt(
                fabrik, probelauf_sitzung_fuer_transkription
            )(request)
        finally:
            request.close()

    def test_bildet_den_anbieter_je_anfrage_neu(self) -> None:
        """Eine geänderte Konfiguration greift sofort, nicht erst beim Neustart."""
        self._probelauf_starten()
        gebildete: list[FakeTranskription] = []

        def fabrik() -> FakeTranskription:
            anbieter: FakeTranskription = FakeTranskription(["Wie hast du gerechnet?"])
            gebildete.append(anbieter)
            return anbieter

        for _ in range(2):
            self.assertEqual(self._anfragen_mit_fabrik(fabrik).status_code, 200)

        self.assertEqual(len(gebildete), 2)

    def test_laufender_probelauf_transkribiert_ohne_teilnahme(self) -> None:
        """Die Autor:in spricht über eigenes Material, ohne einzuwilligen."""
        self._probelauf_starten()

        response: HttpResponse = self._anfragen(
            FakeTranskription(["Wie hast du gerechnet?"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"text": "Wie hast du gerechnet?"})
        self.assertFalse(Teilnahme.objects.exists())
        self.assertFalse(Sitzung.objects.exists())

    def test_ohne_laufenden_probelauf_bleibt_der_endpunkt_verschlossen(self) -> None:
        """Eine Anmeldung allein berechtigt nicht zur Transkription."""
        anbieter = FakeTranskription(["Text"])

        with self.assertRaises(PermissionDenied):
            self._anfragen(anbieter)

        self.assertEqual(anbieter.skript, ["Text"])

    def test_reicht_anbieterfehler_als_unterscheidbare_zustaende_durch(self) -> None:
        """Das Frontend kann jede fehlgeschlagene Aufnahme einzeln behandeln."""
        self._probelauf_starten()
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

    @override_settings(TRANSKRIPTION_ZERO_RETENTION=False)
    def test_zero_retention_bleibt_auch_im_probelauf_das_tor(self) -> None:
        """Die vertragliche Zusicherung wird von keinem Weg umgangen."""
        self._probelauf_starten()
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(anbieter)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "zero_retention_fehlt"})
        self.assertEqual(anbieter.skript, ["Text"])

    def test_lehnt_aufnahme_ueber_der_grenze_mit_eigenem_status_ab(self) -> None:
        """Eine Aufnahme jenseits der Grenze erreicht den Anbieter nicht."""
        self._probelauf_starten()
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(
            anbieter,
            self._aufnahme_mit_groesse(settings.TRANSKRIPTION_MAX_AUFNAHME_BYTES + 1),
        )

        self.assertEqual(response.status_code, 413)
        self.assertJSONEqual(response.content, {"status": "aufnahme_zu_gross"})
        self.assertEqual(anbieter.skript, ["Text"])

    def test_nimmt_aufnahme_genau_auf_der_grenze_an(self) -> None:
        """Die Grenze schließt die letzte erlaubte Größe ein."""
        self._probelauf_starten()

        response: HttpResponse = self._anfragen(
            FakeTranskription(["Wie hast du gerechnet?"]),
            self._aufnahme_mit_groesse(settings.TRANSKRIPTION_MAX_AUFNAHME_BYTES),
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"text": "Wie hast du gerechnet?"})

    def test_persistiert_keine_aufnahme(self) -> None:
        """Nach der Transkription liegt keine Audio-Datei im Medienverzeichnis."""
        self._probelauf_starten()
        media_root: str
        upload_temp_dir: str
        with (
            TemporaryDirectory() as media_root,
            TemporaryDirectory() as upload_temp_dir,
        ):
            with self.settings(
                MEDIA_ROOT=media_root,
                FILE_UPLOAD_MAX_MEMORY_SIZE=0,
                FILE_UPLOAD_TEMP_DIR=upload_temp_dir,
            ):
                self._anfragen(FakeTranskription(["Text"]))

            self.assertEqual(list(Path(upload_temp_dir).iterdir()), [])
            self.assertEqual(list(Path(media_root).iterdir()), [])

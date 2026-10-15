"""HTTP-Vertrag des Transkriptions-Endpunkts im schreibfreien Probelauf."""

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    erklaerte,
    erklaerte_aktive_transkription,
    konto_mit_rollen,
    vignetten_entwurf,
)
from konten.models import Konto
from konten.navigation import AUTORIN_GRUPPE
from simulation.models import Anbieter, TranskriptionsKonfiguration, Verwendung
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
from sitzungen.tests.aufnahme import audioaufnahme
from vignetten.models import Vignette


class ProbelaufTranskriptionTests(TestCase):
    """Der schreibfreie Probelauf transkribiert ohne Teilnahme und Einwilligung."""

    def setUp(self) -> None:
        """Meldet die Autor:in an und legt ihren spielbaren Entwurf an."""
        self.fassung: TranskriptionsKonfiguration = erklaerte_aktive_transkription()
        self.autorin: Konto = konto_mit_rollen("ada", AUTORIN_GRUPPE)
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        self.entwurf: Vignette = vignetten_entwurf(self.autorin)
        # Die Rahmenhandlung braucht beide Akteure für ihre Grammatikformen.
        self.entwurf.schuelerin_name = "Mia"
        self.entwurf.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.lehrperson_name = "Weber"
        self.entwurf.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.save()
        self.client.force_login(self.autorin)

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
        return self._anfragen_mit_fabrik(lambda _: anbieter, aufnahme)

    def _anfragen_mit_fabrik(
        self,
        fabrik: Callable[[TranskriptionsKonfiguration], Transkription],
        aufnahme: SimpleUploadedFile | None = None,
    ) -> HttpResponse:
        # Ruft den Endpunkt ohne sitzung_pk auf, so wie es der Probelauf tut.
        request: HttpRequest = RequestFactory().post(
            "/sitzungen/transkription/", {"audio": aufnahme or audioaufnahme()}
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

        def fabrik(_: TranskriptionsKonfiguration) -> FakeTranskription:
            anbieter: FakeTranskription = FakeTranskription(["Wie hast du gerechnet?"])
            gebildete.append(anbieter)
            return anbieter

        for _ in range(2):
            self.assertEqual(self._anfragen_mit_fabrik(fabrik).status_code, 200)

        self.assertEqual(len(gebildete), 2)

    def test_folgt_bei_jeder_anfrage_der_aktiven_fassung(self) -> None:
        """Der Probelauf hat keine Sitzung, die eine Fassung pinnen könnte."""
        self._probelauf_starten()
        gebildet_aus: list[TranskriptionsKonfiguration] = []

        def fabrik(konfiguration: TranskriptionsKonfiguration) -> FakeTranskription:
            gebildet_aus.append(konfiguration)
            return FakeTranskription(["Text"])

        erste: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.aktive()
        )
        self._anfragen_mit_fabrik(fabrik)
        zweite: TranskriptionsKonfiguration = (
            TranskriptionsKonfiguration.objects.aktivieren(
                erklaerte(
                    TranskriptionsKonfiguration.objects.create(
                        anbieter=Anbieter.OPENROUTER,
                        anbieter_token="sk-or-geheim",
                        transkriptionsmodell="whisper-large-v3",
                    )
                )
            )
        )
        self._anfragen_mit_fabrik(fabrik)

        self.assertEqual(gebildet_aus, [erste, zweite])

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

    def _ist_zu(self) -> None:
        # Das Tor ist zu: 503, und der Anbieter wird nicht gebildet.
        gebildet: list[TranskriptionsKonfiguration] = []

        def fabrik(konfiguration: TranskriptionsKonfiguration) -> FakeTranskription:
            gebildet.append(konfiguration)
            return FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen_mit_fabrik(fabrik)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "zero_retention_fehlt"})
        self.assertEqual(gebildet, [])

    def test_ohne_erklaerung_der_aktiven_fassung_bleibt_das_tor_zu(self) -> None:
        """Die Erklärung an der Fassung ist das Tor, auch im Probelauf (ADR-0026)."""
        TranskriptionsKonfiguration.objects.aktivieren(
            TranskriptionsKonfiguration.objects.create(
                anbieter=Anbieter.OPENROUTER,
                anbieter_token="sk-or-geheim",
                transkriptionsmodell="whisper-large-v3",
            )
        )
        self._probelauf_starten()

        self._ist_zu()

    def test_nach_dem_widerruf_bleibt_das_tor_zu(self) -> None:
        """Ein Widerruf wirkt ab der nächsten Aufnahme."""
        self._probelauf_starten()
        self.fassung.zero_retention_widerrufen(
            "Zusage zurückgezogen", konto_mit_rollen("linus", is_superuser=True)
        )

        self._ist_zu()

    def test_mit_fake_als_aktiver_fassung_ist_die_transkription_aus(self) -> None:
        """`fake` heißt »keine Transkription«, nicht »Platzhaltertext«."""
        TranskriptionsKonfiguration.objects.aktivieren(
            TranskriptionsKonfiguration.objects.create()
        )
        self._probelauf_starten()

        self._ist_zu()

    @override_settings(TRANSKRIPTION_MAX_AUFNAHME_BYTES=8)
    def test_lehnt_aufnahme_ueber_der_grenze_mit_eigenem_status_ab(self) -> None:
        """Eine Aufnahme jenseits der Grenze erreicht den Anbieter nicht."""
        self._probelauf_starten()
        anbieter = FakeTranskription(["Text"])

        response: HttpResponse = self._anfragen(
            anbieter,
            self._aufnahme_mit_groesse(9),
        )

        self.assertEqual(response.status_code, 413)
        self.assertJSONEqual(response.content, {"status": "aufnahme_zu_gross"})
        self.assertEqual(anbieter.skript, ["Text"])

    @override_settings(TRANSKRIPTION_MAX_AUFNAHME_BYTES=8)
    def test_nimmt_aufnahme_genau_auf_der_grenze_an(self) -> None:
        """Die Grenze schließt die letzte erlaubte Größe ein."""
        self._probelauf_starten()

        response: HttpResponse = self._anfragen(
            FakeTranskription(["Wie hast du gerechnet?"]),
            self._aufnahme_mit_groesse(8),
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

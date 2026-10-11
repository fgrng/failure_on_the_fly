"""HTTP-Tests für den Austritt aus dem Training (ADR-0049)."""

from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE, AUTORIN_GRUPPE
from simulation.models import Verwendung
from sitzungen.models import Gespraechsschritt, Sitzung
from sitzungen.tests.aufnahme import audioaufnahme
from training.models import Training
from training.tests.aufbau import ansehen_url, gespielte_sitzung
from training.tests.seite import tabellenzeilen
from vignetten.models import Vignette

HINWEIS_AUSGETRETEN: str = "Sie sind nicht mehr Teilnehmer:in dieses Trainings"


class AustrittTests(TestCase):
    """Eine Trainingsteilnehmerin tritt aus und behält ihre Selbsteinsicht."""

    def setUp(self) -> None:
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        self.ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.teilnehmerin: Konto = konto_mit_rollen("grace")
        self.vignette: Vignette = finale_vignette(
            konto_mit_rollen("barbara", AUTORIN_GRUPPE), name="Brüche vergleichen"
        )
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.vignetten.add(self.vignette)
        self.training.veroeffentlichen()
        self.client.force_login(self.teilnehmerin)
        self.client.get(
            reverse("training:beitreten", args=[self.training.trainings_link])
        )

    def _detail(self) -> HttpResponse:
        return self.client.get(reverse("training:detail", args=[self.training.pk]))

    def _austreten(self) -> HttpResponse:
        return self.client.post(
            reverse("training:austreten", args=[self.training.pk]), follow=True
        )

    def test_trainingsseite_bietet_den_austritt_mit_erklaerung_an(self) -> None:
        """Vor dem Austritt erklärt die Seite seine Folgen."""
        detail: HttpResponse = self._detail()

        self.assertContains(detail, "Aus dem Training austreten")
        self.assertContains(
            detail, reverse("training:austreten", args=[self.training.pk])
        )
        for folge in (
            "sieht der Kreis dieses Trainings Ihre Sitzungen nicht mehr",
            "für dieses Training ruhen",
            "Nichts wird gelöscht",
            "können Sie wieder beitreten",
        ):
            self.assertContains(detail, folge)

    def test_austritt_leitet_mit_meldung_auf_die_trainingsseite(self) -> None:
        """Nach dem Austritt zeigt die Trainingsseite den neuen Stand."""
        antwort: HttpResponse = self._austreten()

        self.assertRedirects(
            antwort, reverse("training:detail", args=[self.training.pk])
        )
        self.assertContains(antwort, "Sie sind aus dem Training")
        self.assertContains(antwort, HINWEIS_AUSGETRETEN)

    def test_austritt_nur_per_post(self) -> None:
        """Ein aufgerufener Link lässt niemanden austreten."""
        antwort: HttpResponse = self.client.get(
            reverse("training:austreten", args=[self.training.pk])
        )

        self.assertEqual(antwort.status_code, 405)
        self.assertNotContains(self._detail(), HINWEIS_AUSGETRETEN)

    def test_zweiter_austritt_aendert_nichts_und_scheitert_nicht(self) -> None:
        """Ein doppeltes Absenden bleibt harmlos."""
        self._austreten()

        antwort: HttpResponse = self._austreten()

        self.assertRedirects(
            antwort, reverse("training:detail", args=[self.training.pk])
        )
        self.assertContains(antwort, HINWEIS_AUSGETRETEN)

    def test_austritt_ohne_bindung_ist_unbekannt(self) -> None:
        """Wer dem Training nie beigetreten ist, erfährt nichts über es."""
        self.client.force_login(konto_mit_rollen("linus"))

        antwort: HttpResponse = self.client.post(
            reverse("training:austreten", args=[self.training.pk])
        )

        self.assertEqual(antwort.status_code, 404)

    def test_katalog_zeigt_das_training_nicht_mehr(self) -> None:
        """Der Katalog zeigt nur, woran die Person teilnimmt."""
        self._austreten()

        katalog: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertEqual(tabellenzeilen(katalog), [])

    def test_historie_kennzeichnet_das_training_als_ausgetreten(self) -> None:
        """Frühere Sitzungen bleiben über die Historie auffindbar."""
        self._austreten()

        historie: HttpResponse = self.client.get(reverse("training:historie"))

        self.assertEqual(
            [
                (zeile["name"], zeile["ausgetreten"])
                for zeile in tabellenzeilen(historie)
            ],
            [("Bruchrechnung", True)],
        )

    def test_historie_kennzeichnet_aktive_trainings_nicht(self) -> None:
        """Ohne Austritt steht kein Kennzeichen."""
        historie: HttpResponse = self.client.get(reverse("training:historie"))

        self.assertEqual(
            [zeile["ausgetreten"] for zeile in tabellenzeilen(historie)], [False]
        )

    def test_trainingsseite_zeigt_eigene_sitzungen_in_jedem_status(self) -> None:
        """Die Ausgetretene liest ihre Arbeit weiter."""
        sitzungen: list[Sitzung] = [
            gespielte_sitzung(self.training, self.teilnehmerin, self.vignette, status)
            for status in Sitzung.Status
        ]
        self._austreten()

        detail: HttpResponse = self._detail()

        for sitzung in sitzungen:
            with self.subTest(status=sitzung.status):
                self.assertContains(detail, ansehen_url(sitzung))

    def test_trainingsseite_bietet_weder_wahl_noch_start_noch_austritt(self) -> None:
        """Die Seite ist für die Ausgetretene nur lesend."""
        self._austreten()

        detail: HttpResponse = self._detail()

        self.assertContains(detail, HINWEIS_AUSGETRETEN)
        self.assertNotContains(
            detail, reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )
        self.assertNotContains(detail, "Neu starten")
        self.assertNotContains(detail, "Aus dem Training austreten")

    def test_wahl_einwilligung_und_start_werden_abgewiesen(self) -> None:
        """Nach dem Austritt entsteht keine Sitzung, und die Bindung bleibt ruhend."""
        self._austreten()
        wahl_url: str = reverse(
            "training:wahl", args=[self.training.pk, self.vignette.pk]
        )

        antworten: list[HttpResponse] = [
            self.client.get(wahl_url),
            self.client.post(wahl_url),
            self.client.post(
                reverse(
                    "training:einwilligung", args=[self.training.pk, self.vignette.pk]
                ),
                {"audioverarbeitung_eingewilligt": "ja"},
            ),
        ]

        self.assertEqual([a.status_code for a in antworten], [404, 404, 404])
        self.assertFalse(Sitzung.objects.exists())
        self.assertContains(self._detail(), HINWEIS_AUSGETRETEN)

    def test_eigene_sitzung_bleibt_lesbar_ohne_denkspur(self) -> None:
        """Auch eine laufende Sitzung öffnet sich lesend, ohne Denkspur."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette, Sitzung.Status.LAUFEND
        )
        self._austreten()

        antwort: HttpResponse = self.client.get(ansehen_url(sitzung))

        self.assertContains(antwort, "Ich habe oben und unten zusammengezählt.")
        self.assertNotContains(antwort, "Geheime Denkspur der Schülerin.")

    def test_kreis_und_administration_erreichen_das_training_unveraendert(
        self,
    ) -> None:
        """Ein Austritt von Teilnehmenden ändert nichts am Zugang des Kreises."""
        self._austreten()
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)

        for konto in (self.ausbilderin, administratorin):
            with self.subTest(konto=konto.username):
                self.client.force_login(konto)
                detail: HttpResponse = self._detail()
                self.assertContains(detail, "Neu starten")
                self.assertNotContains(detail, HINWEIS_AUSGETRETEN)
                self.assertEqual(
                    self.client.get(
                        reverse("training:kuratieren", args=[self.training.pk])
                    ).status_code,
                    200,
                )

    def test_ausgetretene_eigentuemerin_startet_keine_sitzung(self) -> None:
        """Der Kreiszugang führt nicht an einer ausgetretenen Bindung vorbei."""
        gespielte_sitzung(self.training, self.ausbilderin, self.vignette)
        self.client.force_login(self.ausbilderin)
        self._austreten()
        sitzungen_vorher: int = Sitzung.objects.count()

        start: HttpResponse = self.client.post(
            reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )

        self.assertEqual(start.status_code, 404)
        self.assertEqual(Sitzung.objects.count(), sitzungen_vorher)


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class LaufendeSitzungNachAustrittTests(TestCase):
    """Eine beim Austritt laufende Sitzung bleibt liegen."""

    def setUp(self) -> None:
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        vignette: Vignette = finale_vignette(ausbilderin)
        self.training: Training = Training.objects.anlegen(
            ausbilderin, name="Bruchrechnung"
        )
        self.training.vignetten.add(vignette)
        self.training.veroeffentlichen()
        self.client.force_login(konto_mit_rollen("grace"))
        self.client.get(
            reverse("training:beitreten", args=[self.training.trainings_link])
        )
        self.client.post(reverse("training:wahl", args=[self.training.pk, vignette.pk]))
        self.client.post(
            reverse("training:einwilligung", args=[self.training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "ja"},
        )
        self.client.post(reverse("training:austreten", args=[self.training.pk]))

    def test_gespraechsablaeufe_setzen_die_sitzung_nicht_fort(self) -> None:
        """Auch ein noch offener Tab führt kein Gespräch weiter."""
        anfragen: dict[str, tuple[str, dict[str, object]]] = {
            "gespraech": ("training:gespraech", {"eingabe": "Wie rechnest du?"}),
            "beenden": ("training:gespraech_beenden", {}),
            "debrief": ("training:debrief", {"diagnose": "Zähler addiert."}),
            "abbrechen": ("training:abbrechen", {}),
            "transkription": ("training:transkription", {"audio": audioaufnahme()}),
        }

        for ablauf, (name, daten) in anfragen.items():
            with self.subTest(ablauf=ablauf):
                antwort: HttpResponse = self.client.post(reverse(name), daten)
                self.assertEqual(antwort.status_code, 404)
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)
        self.assertFalse(Gespraechsschritt.objects.exists())

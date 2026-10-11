"""HTTP-Tests: Ein zweiter Start im Training wird abgewiesen."""

from unittest import mock

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from konten.models import Konto
from simulation.models import ModellKonfiguration, Verwendung
from sitzungen.models import Gespraechsschritt, Sitzung
from training.models import Training
from vignetten.models import Vignette


class ZweiterStartTests(TestCase):
    """Je Teilnahme läuft höchstens eine Trainingssitzung."""

    def setUp(self) -> None:
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={
                "skript": [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere."}]
            },
        )
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        ausbilderin: Konto = konto_mit_rollen("ada")
        self.erste: Vignette = finale_vignette(ausbilderin, name="Brüche addieren")
        self.zweite: Vignette = finale_vignette(ausbilderin, name="Brüche kürzen")
        self.training: Training = self._training(ausbilderin, "Bruchrechnung")
        self.client.force_login(konto_mit_rollen("grace"))
        self._beitreten(self.training)

    def _training(self, ausbilderin: Konto, name: str) -> Training:
        training: Training = Training.objects.anlegen(ausbilderin, name=name)
        training.vignetten.add(self.erste, self.zweite)
        training.veroeffentlichen()
        return training

    def _beitreten(self, training: Training) -> None:
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.client.post(
            reverse("training:einwilligung", args=[training.pk, self.erste.pk]),
            {"audioverarbeitung_eingewilligt": "nein"},
        )

    def _starten(self, vignette: Vignette) -> HttpResponse:
        return self.client.post(
            reverse("training:wahl", args=[self.training.pk, vignette.pk])
        )

    def test_zweiter_start_zeigt_die_laufende_sitzung_statt_einer_neuen(self) -> None:
        """Die Abweisung nennt Vignette und Beginn und bietet beide Wege an."""
        laufende: Sitzung = Sitzung.objects.get()

        response: HttpResponse = self._starten(self.zweite)

        self.assertContains(response, "Es läuft noch eine Sitzung", status_code=409)
        self.assertContains(response, "Brüche addieren", status_code=409)
        self.assertContains(
            response, laufende.erstellt_am.strftime("%d.%m.%Y"), status_code=409
        )
        self.assertContains(
            response,
            f'href="{reverse("training:gespraech", args=[laufende.pk])}"',
            status_code=409,
        )
        self.assertContains(
            response,
            reverse("training:neu_starten", args=[self.training.pk, self.zweite.pk]),
            status_code=409,
        )
        self.assertEqual(Sitzung.objects.get(), laufende)

    def test_auch_dieselbe_vignette_wird_abgewiesen(self) -> None:
        """Wer dieselbe Vignette erneut wählt, beginnt nicht versehentlich neu."""

        response: HttpResponse = self._starten(self.erste)

        self.assertContains(response, "Es läuft noch eine Sitzung", status_code=409)
        self.assertEqual(Sitzung.objects.count(), 1)

    def test_fortsetzen_fuehrt_mit_bisherigem_verlauf_weiter(self) -> None:
        """Der Fortsetzen-Link der Abweisung trägt das bisherige Gespräch."""
        laufende: Sitzung = Sitzung.objects.get()
        gespraech_url: str = reverse("training:gespraech", args=[laufende.pk])
        self.client.post(gespraech_url, {"eingabe": "Wie rechnest du?"})
        self._starten(self.zweite)

        fortgesetzt: HttpResponse = self.client.get(gespraech_url)

        self.assertContains(fortgesetzt, "Wie rechnest du?")
        self.assertContains(fortgesetzt, "Ich addiere.")
        self.assertEqual(Gespraechsschritt.objects.get().sitzung, laufende)

    def test_abbrechen_und_neu_starten_bricht_ab_und_startet_die_wahl(self) -> None:
        """Die laufende Sitzung wird abgebrochen, die gewählte beginnt."""
        alte: Sitzung = Sitzung.objects.get()

        response: HttpResponse = self.client.post(
            reverse("training:neu_starten", args=[self.training.pk, self.zweite.pk]),
            {"laufende_sitzung": alte.pk},
        )

        alte.refresh_from_db()
        self.assertEqual(alte.status, Sitzung.Status.ABGEBROCHEN)
        neue: Sitzung = Sitzung.objects.get(status=Sitzung.Status.LAUFEND)
        self.assertEqual(neue.vignette, self.zweite)
        self.assertContains(
            response, f'action="{reverse("training:gespraech", args=[neue.pk])}"'
        )
        self.assertContains(response, "Ihre nächste Frage")

    def test_neu_starten_bricht_keine_ungesehene_sitzung_ab(self) -> None:
        """Läuft inzwischen eine andere Sitzung, wird sie nur erneut genannt."""
        laufende: Sitzung = Sitzung.objects.get()

        response: HttpResponse = self.client.post(
            reverse("training:neu_starten", args=[self.training.pk, self.zweite.pk]),
            {"laufende_sitzung": laufende.pk + 1},
        )

        self.assertContains(response, "Es läuft noch eine Sitzung", status_code=409)
        laufende.refresh_from_db()
        self.assertEqual(laufende.status, Sitzung.Status.LAUFEND)
        self.assertEqual(Sitzung.objects.count(), 1)

    def test_neu_starten_ohne_laufende_sitzung_startet_einfach(self) -> None:
        """Ist die Sitzung inzwischen beendet, beginnt die Wahl ohne Abbruch."""
        alte: Sitzung = Sitzung.objects.get()
        self.client.post(reverse("training:abbrechen", args=[alte.pk]))

        self.client.post(
            reverse("training:neu_starten", args=[self.training.pk, self.zweite.pk]),
            {"laufende_sitzung": alte.pk},
        )

        self.assertEqual(
            Sitzung.objects.get(status=Sitzung.Status.LAUFEND).vignette, self.zweite
        )

    def test_laufende_sitzungen_in_zwei_trainings_sind_erlaubt(self) -> None:
        """Jedes Training ist eine eigene Teilnahme."""
        anderes: Training = self._training(Konto.objects.get(username="ada"), "Zwei")
        self._beitreten(anderes)

        self.assertEqual(
            Sitzung.objects.filter(status=Sitzung.Status.LAUFEND).count(), 2
        )

    def test_constraint_verletzung_beim_start_ergibt_die_abweisung(self) -> None:
        """Verliert ein Start das Rennen, sieht er die Abweisung statt eines 500."""

        with mock.patch(
            "sitzungen.models.SitzungQuerySet.laufende_von",
            side_effect=[None, Sitzung.objects.get()],
        ):
            response: HttpResponse = self._starten(self.zweite)

        self.assertContains(response, "Es läuft noch eine Sitzung", status_code=409)
        self.assertEqual(Sitzung.objects.count(), 1)

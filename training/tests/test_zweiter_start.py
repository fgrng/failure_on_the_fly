"""HTTP-Tests: Ein zweiter Start im Training wird abgewiesen."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from django.db import IntegrityError, connection
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from konten.models import Konto
from simulation.models import ModellKonfiguration, Verwendung
from sitzungen.models import Gespraechsschritt, Sitzung, Teilnahme
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
        # Veröffentlicht ein Training mit beiden Vignetten.
        training: Training = Training.objects.anlegen(ausbilderin, name=name)
        training.vignetten.add(self.erste, self.zweite)
        training.veroeffentlichen()
        return training

    def _beitreten(self, training: Training) -> None:
        # Tritt bei und startet nach abgelehnter Audioverarbeitung die erste Vignette.
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.client.post(
            reverse("training:einwilligung", args=[training.pk, self.erste.pk]),
            {"audioverarbeitung_eingewilligt": "nein"},
        )

    def _starten(self, vignette: Vignette) -> HttpResponse:
        # Wählt die Vignette im Training zum Start.
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

    @contextmanager
    def _gleichzeitiger_start(
        self, beim_anlegen: Callable[[], None] = lambda: None
    ) -> Iterator[None]:
        # Verbirgt laufende Sitzungen vor dem Startversuch, wie es ein
        # gleichzeitiger, noch nicht sichtbarer Start täte.
        im_start: list[bool] = [False]

        def verbergen(
            execute: Any, sql: str, params: Any, many: bool, context: dict[str, Any]
        ) -> Any:
            if sql.startswith("SAVEPOINT"):
                im_start[0] = True
            elif "SAVEPOINT" in sql:
                im_start[0] = False
            elif im_start[0] and 'FROM "sitzungen_sitzung"' in sql:
                params = [
                    "unsichtbar" if wert == Sitzung.Status.LAUFEND else wert
                    for wert in params
                ]
            elif im_start[0] and sql.startswith('INSERT INTO "sitzungen_sitzung"'):
                beim_anlegen()
            return execute(sql, params, many, context)

        with connection.execute_wrapper(verbergen):
            yield

    def test_constraint_verletzung_beim_start_ergibt_die_abweisung(self) -> None:
        """Verliert ein Start das Rennen, sieht er die Abweisung statt eines 500."""

        with self._gleichzeitiger_start():
            response: HttpResponse = self._starten(self.zweite)

        self.assertContains(response, "Es läuft noch eine Sitzung", status_code=409)
        self.assertEqual(Sitzung.objects.count(), 1)

    def test_fremde_integritaetsverletzung_wird_nicht_zur_abweisung(self) -> None:
        """Nur der Constraint der laufenden Sitzung führt zur Abweisung."""

        def fremd_scheitern() -> None:
            raise IntegrityError("NOT NULL constraint failed: sitzungen_sitzung.x")

        with (
            self._gleichzeitiger_start(beim_anlegen=fremd_scheitern),
            self.assertRaises(IntegrityError),
        ):
            self._starten(self.zweite)

    def test_neu_starten_nimmt_nur_post_an(self) -> None:
        """Ein Aufruf per GET bricht nichts ab."""

        response: HttpResponse = self.client.get(
            reverse("training:neu_starten", args=[self.training.pk, self.zweite.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)

    def test_neu_starten_ohne_gueltige_laufende_sitzung_ist_fehlerhaft(self) -> None:
        """Ohne die genannte Sitzung als Zahl wird nichts abgebrochen."""
        url: str = reverse(
            "training:neu_starten", args=[self.training.pk, self.zweite.pk]
        )

        for daten in ({}, {"laufende_sitzung": "eins"}):
            with self.subTest(daten=daten):
                response: HttpResponse = self.client.post(url, daten)

                self.assertEqual(response.status_code, 400)
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)

    def test_einwilligung_vor_dem_neustart_behaelt_den_abbruchwunsch(self) -> None:
        """Nach der Einwilligung wird abgebrochen und die Wahl gestartet."""
        alte: Sitzung = Sitzung.objects.get()
        Teilnahme.objects.filter(pk=alte.teilnahme_id).update(
            audioverarbeitung_eingewilligt=None
        )

        abfrage: HttpResponse = self.client.post(
            reverse("training:neu_starten", args=[self.training.pk, self.zweite.pk]),
            {"laufende_sitzung": alte.pk},
        )
        self.assertContains(abfrage, "Audioverarbeitung")
        self.assertContains(
            abfrage, f'name="laufende_sitzung" value="{alte.pk}"', html=False
        )
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)

        self.client.post(
            reverse("training:einwilligung", args=[self.training.pk, self.zweite.pk]),
            {"audioverarbeitung_eingewilligt": "nein", "laufende_sitzung": alte.pk},
        )

        alte.refresh_from_db()
        self.assertEqual(alte.status, Sitzung.Status.ABGEBROCHEN)
        self.assertEqual(
            Sitzung.objects.get(status=Sitzung.Status.LAUFEND).vignette, self.zweite
        )

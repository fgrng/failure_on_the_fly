"""HTTP-Tests der Fremdeinsicht im Training (ADR-0049)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import time_machine
from django.http import HttpResponse
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE
from sitzungen.models import Sitzung
from training.models import Training
from training.tests.aufbau import (
    FremdeinsichtTestCase,
    ansehen_url,
    gespielte_sitzung,
)
from vignetten.models import Vignette


class SitzungAnsehenTests(FremdeinsichtTestCase):
    """Wer eine fremde Trainingssitzung lesend öffnen darf."""

    def _status_fuer(
        self, konto: Konto, status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN
    ) -> int:
        # Öffnet eine Sitzung der Teilnehmerin aus Sicht des Kontos.
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette, status
        )
        self.client.force_login(konto)
        return self.client.get(ansehen_url(sitzung)).status_code

    def test_kreismitglied_liest_eine_abgeschlossene_sitzung(self) -> None:
        """Die Eigentümerin sieht Transkript und Diagnose ihrer Gruppe."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(ansehen_url(sitzung))

        self.assertContains(response, "Ich habe oben und unten zusammengezählt.")

    def test_kreismitglied_liest_die_abgegebene_diagnose(self) -> None:
        """Die Diagnose der Teilnehmerin steht in der lesenden Ansicht."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(ansehen_url(sitzung))

        self.assertContains(response, "Zähler und Nenner addiert.")

    def test_neues_kreismitglied_liest_auch_aeltere_sitzungen(self) -> None:
        """Einsicht folgt der aktuellen Mitgliedschaft, auch rückwirkend."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        neues_mitglied: Konto = konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(neues_mitglied)
        self.client.force_login(neues_mitglied)

        response: HttpResponse = self.client.get(ansehen_url(sitzung))

        self.assertEqual(response.status_code, 200)

    def test_ausgetretenes_kreismitglied_bekommt_404(self) -> None:
        """Wer den Kreis verlässt, sieht sofort nichts mehr."""
        nachfolgerin: Konto = konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(nachfolgerin)
        self.training.austreten(self.ausbilderin.pk)

        self.assertEqual(self._status_fuer(self.ausbilderin), 404)

    def test_administration_liest_eine_abgeschlossene_sitzung(self) -> None:
        """Die Administration folgt allein aus der Sichtbarkeitsregel."""
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)

        self.assertEqual(self._status_fuer(administratorin), 200)

    def test_fremdes_konto_bekommt_404(self) -> None:
        """Eine Ausbilder:in außerhalb des Kreises sieht die Sitzung nicht."""
        fremde: Konto = konto_mit_rollen("margaret", AUSBILDERIN_GRUPPE)

        self.assertEqual(self._status_fuer(fremde), 404)

    def test_autorin_der_vignette_bekommt_404(self) -> None:
        """Autorschaft der Vignette begründet keine Einsicht."""
        self.assertEqual(self._status_fuer(self.autorin), 404)

    def test_nicht_abgeschlossene_sitzungen_bleiben_dem_kreis_verborgen(
        self,
    ) -> None:
        """Laufende, abgebrochene und gescheiterte Sitzungen liefern 404."""
        for status in (
            Sitzung.Status.LAUFEND,
            Sitzung.Status.ABGEBROCHEN,
            Sitzung.Status.GESCHEITERT,
        ):
            with self.subTest(status=status):
                self.assertEqual(self._status_fuer(self.ausbilderin, status), 404)

    def test_fremdeinsicht_verschweigt_die_denkspur(self) -> None:
        """Der Kreis sieht, was die Teilnehmerin sieht, also keine Denkspur."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(ansehen_url(sitzung))

        self.assertNotContains(response, "Geheime Denkspur der Schülerin.")

    def test_fremdeinsicht_ist_rein_lesend(self) -> None:
        """Ohne Abbrechen, Fortsetzen oder Löschen."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(ansehen_url(sitzung))

        for bedienelement in (
            reverse("training:abbrechen"),
            reverse("training:gespraech"),
            "Sitzung abbrechen",
            "Fortsetzen",
            "Löschen",
        ):
            self.assertNotContains(response, bedienelement)

    def test_sitzung_in_einem_fremden_training_bleibt_verborgen(self) -> None:
        """Dieselbe Person mit derselben Vignette anderswo gehört nicht dazu."""
        fremder_kreis: Konto = konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)
        fremdes_training: Training = Training.objects.anlegen(
            fremder_kreis, name="Anderes Seminar"
        )
        fremdes_training.vignetten.add(self.vignette)
        fremdes_training.veroeffentlichen()
        fremdes_training.beitreten(self.teilnehmerin)
        sitzung: Sitzung = gespielte_sitzung(
            fremdes_training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(ansehen_url(sitzung))

        self.assertEqual(response.status_code, 404)


class SelbsteinsichtTests(FremdeinsichtTestCase):
    """Die eigene Sitzung bleibt in jedem Status lesbar."""

    def test_eigene_sitzung_ist_in_jedem_status_lesbar(self) -> None:
        """Auch laufende, abgebrochene und gescheiterte eigene Sitzungen."""
        self.client.force_login(self.teilnehmerin)
        for status in Sitzung.Status:
            with self.subTest(status=status):
                sitzung: Sitzung = gespielte_sitzung(
                    self.training, self.teilnehmerin, self.vignette, status
                )

                response: HttpResponse = self.client.get(ansehen_url(sitzung))

                self.assertEqual(response.status_code, 200)

    def test_selbsteinsicht_verschweigt_die_denkspur(self) -> None:
        """Auch die eigene Sitzung zeigt in keinem Status eine Denkspur."""
        self.client.force_login(self.teilnehmerin)
        for status in Sitzung.Status:
            with self.subTest(status=status):
                sitzung: Sitzung = gespielte_sitzung(
                    self.training, self.teilnehmerin, self.vignette, status
                )

                response: HttpResponse = self.client.get(ansehen_url(sitzung))

                self.assertNotContains(response, "Geheime Denkspur der Schülerin.")


class FremdeinsichtTabelleTests(FremdeinsichtTestCase):
    """Die Tabelle der Fremdeinsicht auf der Kuratierseite."""

    def _kuratierseite(self) -> str:
        # Liest die Kuratierseite aus Sicht der Eigentümerin.
        self.client.force_login(self.ausbilderin)
        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[self.training.pk])
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_beigetretene_ohne_sitzung_erscheinen_als_zeile(self) -> None:
        """Wer nichts bearbeitet hat, steht trotzdem namentlich in der Tabelle."""
        self.assertIn("Grace Hopper", self._kuratierseite())

    def test_vignetten_des_trainings_sind_die_spalten(self) -> None:
        """Jede Vignette des Trainings hat ihren Spaltenkopf."""
        self.assertIn('title="Brüche addieren"', self._kuratierseite())

    def test_spalten_folgen_der_kuratierreihenfolge(self) -> None:
        """Eine später aufgenommene Vignette steht rechts, nicht alphabetisch."""
        self.training.vignetten.add(finale_vignette(self.autorin, name="Addition"))

        seite: str = self._kuratierseite()

        self.assertLess(
            seite.index('title="Brüche addieren"'), seite.index('title="Addition"')
        )

    def test_abgeschlossene_sitzung_ist_verlinkt(self) -> None:
        """Eine abgeschlossene Sitzung öffnet die lesende Sitzungsansicht."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )

        self.assertIn(ansehen_url(sitzung), self._kuratierseite())

    def test_nicht_abgeschlossene_sitzung_ist_nicht_verlinkt(self) -> None:
        """Laufende, abgebrochene und gescheiterte Sitzungen fehlen."""
        for status in (
            Sitzung.Status.LAUFEND,
            Sitzung.Status.ABGEBROCHEN,
            Sitzung.Status.GESCHEITERT,
        ):
            with self.subTest(status=status):
                sitzung: Sitzung = gespielte_sitzung(
                    self.training, self.teilnehmerin, self.vignette, status
                )

                self.assertNotIn(ansehen_url(sitzung), self._kuratierseite())

    def test_sitzungen_sind_je_vignette_nummeriert_und_datiert(self) -> None:
        """Mehrere Durchläufe stehen einzeln, mit Nummer und Datum."""
        berlin: ZoneInfo = ZoneInfo("Europe/Berlin")
        with time_machine.travel(datetime(2026, 7, 1, 10, 0, tzinfo=berlin)):
            gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        with time_machine.travel(datetime(2026, 7, 2, 0, 30, tzinfo=berlin)):
            gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)

        seite: str = self._kuratierseite()

        self.assertIn('aria-label="Sitzung vom 01.07.2026">1</a>', seite)
        self.assertIn('aria-label="Sitzung vom 02.07.2026">2</a>', seite)

    def test_nummerierung_beginnt_je_vignette_neu(self) -> None:
        """Die erste Sitzung zu einer weiteren Vignette trägt wieder die 1."""
        weitere: Vignette = finale_vignette(self.autorin, name="Addition")
        self.training.vignetten.add(weitere)
        gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        gespielte_sitzung(self.training, self.teilnehmerin, weitere)

        seite: str = self._kuratierseite()

        self.assertEqual(seite.count('">1</a>'), 2)

    def test_zeilen_sind_nach_namen_sortiert(self) -> None:
        """Die Gruppe steht alphabetisch, nicht in Beitrittsreihenfolge."""
        self.training.beitreten(
            Konto.objects.create_user(
                username="anna", first_name="anna", last_name="Zeller"
            )
        )

        seite: str = self._kuratierseite()

        self.assertLess(seite.index("anna Zeller"), seite.index("Grace Hopper"))

    def test_training_ohne_beigetretene_zeigt_eine_leerzeile(self) -> None:
        """Solange niemand beigetreten ist, sagt die Tabelle das."""
        leeres: Training = Training.objects.anlegen(self.ausbilderin, name="Neu")
        leeres.vignetten.add(self.vignette)
        leeres.veroeffentlichen()
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[leeres.pk])
        )

        self.assertContains(response, "Noch niemand ist beigetreten.")

    def test_leeres_training_zeigt_einen_hinweis_statt_der_tabelle(self) -> None:
        """Ohne Vignetten gibt es nichts zu tabellieren."""
        self.training.vignetten.clear()

        self.assertIn("Dieses Training enthält keine Vignetten.", self._kuratierseite())

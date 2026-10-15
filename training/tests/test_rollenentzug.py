"""HTTP-Tests: Im Kreis ohne Rolle Ausbilder:in öffnet der Kreis keine Tür (ADR-0037)."""

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE
from sitzungen.models import Sitzung
from training.tests.aufbau import FremdeinsichtTestCase, ansehen_url, gespielte_sitzung


class RollenentzugImKreisTests(FremdeinsichtTestCase):
    """Die ehemalige Ausbilderin bleibt im Kreis, verliert aber dessen Zugänge."""

    def setUp(self) -> None:
        super().setUp()
        self.ausbilderin.groups.remove(Group.objects.get(name=AUSBILDERIN_GRUPPE))
        self.client.force_login(self.ausbilderin)

    def _rolle_zurueckgeben(self) -> None:
        # Gibt der ehemaligen Ausbilderin ihre Rolle zurück; der Kreis blieb.
        self.ausbilderin.groups.add(Group.objects.get(name=AUSBILDERIN_GRUPPE))

    def _entfernen(self) -> HttpResponse:
        # Entfernt die Teilnehmerin aus dem Training.
        return self.client.post(
            reverse(
                "training:teilnehmerin_entfernen",
                args=[self.training.pk, self.teilnehmerin.pk],
            )
        )

    def _wahl_url(self) -> str:
        # Adresse der Wahl der Trainingsvignette.
        return reverse("training:wahl", args=[self.training.pk, self.vignette.pk])

    def test_teilnehmerin_entfernen_ist_verboten(self) -> None:
        """Ohne Rolle 403; die Bindung der Teilnehmerin bleibt aktiv."""
        self.assertEqual(self._entfernen().status_code, 403)
        self.assertTrue(self.training.bindung_fuer(self.teilnehmerin).ist_aktiv)

    def test_rueckgabe_der_rolle_erlaubt_das_entfernen_wieder(self) -> None:
        """Mit der Rolle zurück entfernt die Ausbilderin wieder."""
        self._rolle_zurueckgeben()

        self.assertRedirects(
            self._entfernen(), reverse("training:kuratieren", args=[self.training.pk])
        )

    def test_fremde_sitzung_ist_unbekannt(self) -> None:
        """Ohne Rolle ist eine fremde Sitzung unbekannt, mit Rolle wieder lesbar."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )

        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 404)
        self._rolle_zurueckgeben()
        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 200)

    def test_eigene_sitzung_bleibt_sichtbar(self) -> None:
        """Die Selbsteinsicht hängt an der eigenen Bindung, nicht an der Rolle."""
        self.training.beitreten(self.ausbilderin)
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.ausbilderin, self.vignette
        )

        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 200)

    def test_detail_und_wahl_nur_mit_rolle(self) -> None:
        """Der Kreis-Pfad öffnet Detail und Wahl erst wieder mit der Rolle."""
        detail_url: str = reverse("training:detail", args=[self.training.pk])

        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.assertEqual(self.client.get(self._wahl_url()).status_code, 404)
        self._rolle_zurueckgeben()
        self.assertEqual(self.client.get(detail_url).status_code, 200)

    def test_mit_eigener_bindung_wie_jede_teilnehmerin(self) -> None:
        """Mit aktiver Trainingsbindung erreicht sie Detail und Wahl."""
        self.training.beitreten(self.ausbilderin)

        self.assertEqual(
            self.client.get(
                reverse("training:detail", args=[self.training.pk])
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get(self._wahl_url()).status_code, 200)

    def test_gesperrter_beitritt_greift_auch_im_kreis(self) -> None:
        """Ohne Rolle führt der Kreis nicht an der Beitrittssperre vorbei."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        beitreten_url: str = reverse(
            "training:beitreten", args=[self.training.trainings_link]
        )

        self.assertEqual(self.client.get(beitreten_url).status_code, 403)
        self._rolle_zurueckgeben()
        self.assertRedirects(
            self.client.get(beitreten_url),
            reverse("training:detail", args=[self.training.pk]),
        )

    def test_offener_beitritt_bindet_wie_jede_teilnehmerin(self) -> None:
        """Ohne Rolle legt der offene Link eine Trainingsbindung an."""
        self.client.get(
            reverse("training:beitreten", args=[self.training.trainings_link])
        )

        self.assertTrue(
            self.training.trainingsbindung_set.aktiv()
            .filter(konto=self.ausbilderin)
            .exists()
        )

    def test_administration_bleibt_zugelassen(self) -> None:
        """Administration ohne Fachrolle liest, öffnet und entfernt weiter."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)
        self.client.force_login(administratorin)

        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("training:detail", args=[self.training.pk])
            ).status_code,
            200,
        )
        self.assertEqual(self._entfernen().status_code, 302)

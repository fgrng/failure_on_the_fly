"""HTTP-Tests der Abschrift-Freigabe für ein Training (ADR-0049)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import time_machine
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE, AUTORIN_GRUPPE
from simulation.models import Verwendung
from sitzungen.models import Sitzung
from training.models import Abschrift, Training
from training.tests.aufbau import abschrift
from vignetten.models import Vignette


def _sitzung(abschrift: Abschrift) -> Sitzung:
    # Die eine kopierte Sitzung der Abschrift.
    return abschrift.teilnahme.sitzung_set.get()


def _ansehen_url(sitzung: Sitzung) -> str:
    # Adresse der lesenden Sitzungsansicht.
    return reverse("training:sitzung_ansehen", args=[sitzung.pk])


class FreigabeTestCase(TestCase):
    """Eine Teilnehmerin mit einer Abschrift, beigetreten zu einem Training.

    Die Vignette der Abschrift gehört einer Forschenden, nicht dem Kreis, und
    steht nicht im Training.
    """

    def setUp(self) -> None:
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        self.ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.forschende: Konto = konto_mit_rollen("rosalind", AUTORIN_GRUPPE)
        self.teilnehmerin: Konto = Konto.objects.create_user(
            username="grace", first_name="Grace", last_name="Hopper"
        )
        self.erhebungsvignette: Vignette = finale_vignette(
            self.forschende,
            name="Brüche kürzen",
            lernauftrag_text="Kürze den Bruch aus der Erhebung.",
        )
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.veroeffentlichen()
        self.training.beitreten(self.teilnehmerin)
        self.abschrift: Abschrift = abschrift(self.teilnehmerin, self.erhebungsvignette)

    def _freigeben(self, *trainings: Training) -> HttpResponse:
        # Speichert die Freigaben der Abschrift aus Sicht der Teilnehmerin.
        self.client.force_login(self.teilnehmerin)
        return self.client.post(
            reverse("training:abschrift_freigaben", args=[self.abschrift.pk]),
            {"training": [training.pk for training in trainings]},
        )

    def _abschriftseite(self) -> str:
        # Liest die Abschriftseite aus Sicht der Teilnehmerin.
        self.client.force_login(self.teilnehmerin)
        response: HttpResponse = self.client.get(
            reverse("training:abschrift", args=[self.abschrift.pk])
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _kuratierseite(self, konto: Konto | None = None) -> str:
        # Liest die Kuratierseite des Trainings aus Sicht des Kreises.
        self.client.force_login(konto or self.ausbilderin)
        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[self.training.pk])
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _status_fuer(self, konto: Konto) -> int:
        # Öffnet die Sitzung der Abschrift aus Sicht des Kontos.
        self.client.force_login(konto)
        return self.client.get(_ansehen_url(_sitzung(self.abschrift))).status_code


class FreigebenTests(FreigabeTestCase):
    """Freigeben und Widerrufen auf der Abschriftseite."""

    def test_freigabe_leitet_zur_abschriftseite_zurueck(self) -> None:
        """Nach dem Speichern steht die Teilnehmerin wieder bei ihrer Abschrift."""
        response: HttpResponse = self._freigeben(self.training)

        self.assertRedirects(
            response, reverse("training:abschrift", args=[self.abschrift.pk])
        )

    def test_freigabe_fuer_ein_training_ohne_eigene_bindung_wird_abgewiesen(
        self,
    ) -> None:
        """Ein Training, dem die Teilnehmerin nicht beigetreten ist, gibt es nicht."""
        fremdes_training: Training = Training.objects.anlegen(
            konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE), name="Anderes Seminar"
        )
        fremdes_training.veroeffentlichen()

        response: HttpResponse = self._freigeben(fremdes_training)

        self.assertEqual(response.status_code, 404)

    def test_abgewiesene_freigabe_oeffnet_keine_fremdeinsicht(self) -> None:
        """Auch der Kreis des fremden Trainings sieht danach nichts."""
        fremder_kreis: Konto = konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)
        fremdes_training: Training = Training.objects.anlegen(
            fremder_kreis, name="Anderes Seminar"
        )
        fremdes_training.veroeffentlichen()

        self._freigeben(self.training, fremdes_training)

        self.assertEqual(self._status_fuer(fremder_kreis), 404)

    def test_fremde_abschrift_laesst_sich_nicht_freigeben(self) -> None:
        """Freigeben kann nur, wem die Abschrift gehört."""
        fremde: Konto = Konto.objects.create_user(username="linus")
        self.training.beitreten(fremde)
        self.client.force_login(fremde)

        response: HttpResponse = self.client.post(
            reverse("training:abschrift_freigaben", args=[self.abschrift.pk]),
            {"training": [self.training.pk]},
        )

        self.assertEqual(response.status_code, 404)

    def test_freigabe_mit_unlesbarer_auswahl_wird_abgewiesen(self) -> None:
        """Eine Auswahl, die keine Trainingsnummer ist, gibt es nicht."""
        self.client.force_login(self.teilnehmerin)

        response: HttpResponse = self.client.post(
            reverse("training:abschrift_freigaben", args=[self.abschrift.pk]),
            {"training": ["abc"]},
        )

        self.assertEqual(response.status_code, 404)

    def test_freigabe_mit_hochgestellter_ziffer_wird_abgewiesen(self) -> None:
        """Eine Unicode-Ziffer ist keine Trainingsnummer."""
        self.client.force_login(self.teilnehmerin)

        response: HttpResponse = self.client.post(
            reverse("training:abschrift_freigaben", args=[self.abschrift.pk]),
            {"training": ["²"]},
        )

        self.assertEqual(response.status_code, 404)

    def test_abgewiesene_freigabe_laesst_die_bisherige_freigabe_stehen(self) -> None:
        """Nennt die Auswahl ein fremdes Training, bleibt alles, wie es war."""
        fremdes_training: Training = Training.objects.anlegen(
            konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE), name="Anderes Seminar"
        )
        self._freigeben(self.training)

        self._freigeben(fremdes_training)

        self.assertEqual(self._status_fuer(self.ausbilderin), 200)

    def test_freigeben_verlangt_post(self) -> None:
        """Ein GET ändert keine Freigabe."""
        self.client.force_login(self.teilnehmerin)

        response: HttpResponse = self.client.get(
            reverse("training:abschrift_freigaben", args=[self.abschrift.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_abschrift_laesst_sich_fuer_mehrere_trainings_freigeben(self) -> None:
        """Beide Kreise sehen dieselbe Abschrift."""
        zweiter_kreis: Konto = konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)
        zweites_training: Training = Training.objects.anlegen(
            zweiter_kreis, name="Zweites Seminar"
        )
        zweites_training.veroeffentlichen()
        zweites_training.beitreten(self.teilnehmerin)

        self._freigeben(self.training, zweites_training)

        self.assertEqual(self._status_fuer(self.ausbilderin), 200)
        self.assertEqual(self._status_fuer(zweiter_kreis), 200)

    def test_abschriftseite_bietet_nur_beigetretene_trainings_an(self) -> None:
        """Ein Training ohne eigene Bindung steht nicht zur Auswahl."""
        Training.objects.anlegen(
            konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE), name="Anderes Seminar"
        ).veroeffentlichen()

        seite: str = self._abschriftseite()

        self.assertInHTML(
            '<label><input type="checkbox" name="training" '
            f'value="{self.training.pk}"> Bruchrechnung</label>',
            seite,
        )
        self.assertNotIn("Anderes Seminar", seite)

    def test_abschriftseite_zeigt_die_aktuelle_freigabe_angehakt(self) -> None:
        """Ein freigegebenes Training ist in der Liste angehakt."""
        self._freigeben(self.training)

        seite: str = self._abschriftseite()

        self.assertInHTML(
            '<input type="checkbox" name="training" '
            f'value="{self.training.pk}" checked>',
            seite,
        )

    def test_abschriftseite_zeigt_ohne_freigabe_nichts_angehakt(self) -> None:
        """Eine private Abschrift hat keinen Haken."""
        self.assertInHTML(
            f'<input type="checkbox" name="training" value="{self.training.pk}">',
            self._abschriftseite(),
        )

    def test_abschriftseite_nennt_die_freigegebenen_trainings_im_kopf(self) -> None:
        """Der Untertitel sagt, wer mitliest."""
        self._freigeben(self.training)

        seite: str = self._abschriftseite()

        self.assertIn("Freigegeben für Bruchrechnung.", seite)
        self.assertNotIn("nur Sie lesen sie", seite)

    def test_abschriftseite_ohne_beitritt_bietet_keine_freigabe_an(self) -> None:
        """Wer keinem Training beigetreten ist, bekommt keine Checkbox-Liste."""
        ohne_training: Konto = Konto.objects.create_user(username="linus")
        self.abschrift = abschrift(ohne_training, self.erhebungsvignette)
        self.teilnehmerin = ohne_training

        seite: str = self._abschriftseite()

        self.assertIn("Sie sind noch keinem Training beigetreten.", seite)
        self.assertNotIn("Freigaben speichern", seite)

    def test_private_abschrift_bleibt_im_kopf_privat(self) -> None:
        """Ohne Freigabe liest nur die Teilnehmerin."""
        self.assertIn("nur Sie lesen sie", self._abschriftseite())

    def test_widerruf_beendet_die_fremdeinsicht_sofort(self) -> None:
        """Eine gemerkte Adresse liefert nach dem Widerruf 404."""
        self._freigeben(self.training)

        self._freigeben()

        self.assertEqual(self._status_fuer(self.ausbilderin), 404)


class FremdeinsichtInAbschriftenTests(FreigabeTestCase):
    """Die freigegebene Abschrift in der Fremdeinsicht des Kreises."""

    def test_private_abschrift_ist_fuer_den_kreis_nicht_einsehbar(self) -> None:
        """Ohne Freigabe antwortet die Sitzung mit 404."""
        self.assertEqual(self._status_fuer(self.ausbilderin), 404)

    def test_private_abschrift_ist_fuer_die_administration_nicht_einsehbar(
        self,
    ) -> None:
        """Auch die Administration hat ohne Freigabe keine Einsicht."""
        self.assertEqual(
            self._status_fuer(konto_mit_rollen("root", is_superuser=True)), 404
        )

    def test_private_abschrift_fehlt_auf_der_kuratierseite(self) -> None:
        """Weder Kreis noch Administration finden sie unter der Tabelle."""
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)

        self.assertNotIn("Studie Bruchrechnung", self._kuratierseite())
        self.assertNotIn("Studie Bruchrechnung", self._kuratierseite(administratorin))

    def test_kuratierseite_meldet_wenn_niemand_freigegeben_hat(self) -> None:
        """Die leere Liste sagt es ausdrücklich."""
        self.assertIn("Niemand hat eine Abschrift freigegeben.", self._kuratierseite())

    def test_freigegebene_abschrift_steht_mit_name_erhebung_und_importzeit(
        self,
    ) -> None:
        """Beschriftet wird der Importzeitpunkt, nicht die Spielzeit."""
        with time_machine.travel(
            datetime(2026, 7, 2, 0, 30, tzinfo=ZoneInfo("Europe/Berlin"))
        ):
            self.abschrift = abschrift(self.teilnehmerin, self.erhebungsvignette)
        self._freigeben(self.training)

        seite: str = self._kuratierseite()

        self.assertInHTML('<th scope="row">Grace Hopper</th>', seite)
        self.assertInHTML("<td>Studie Bruchrechnung</td>", seite)
        self.assertInHTML("<td>02.07.2026 00:30</td>", seite)

    def test_administration_findet_die_freigegebene_abschrift_unter_der_tabelle(
        self,
    ) -> None:
        """Die Liste folgt der Sichtbarkeit des Trainings."""
        self._freigeben(self.training)

        seite: str = self._kuratierseite(konto_mit_rollen("root", is_superuser=True))

        self.assertIn("Studie Bruchrechnung", seite)

    def test_freigegebene_abschrift_verlinkt_ihre_abgeschlossene_sitzung(
        self,
    ) -> None:
        """Die Sitzung lässt sich aus der Liste lesend öffnen."""
        self._freigeben(self.training)

        self.assertIn(_ansehen_url(_sitzung(self.abschrift)), self._kuratierseite())

    def test_nicht_abgeschlossene_sitzung_der_abschrift_ist_nicht_verlinkt(
        self,
    ) -> None:
        """Auch in der Abschrift zählen nur abgeschlossene Sitzungen."""
        abgebrochen: Abschrift = abschrift(
            self.teilnehmerin, self.erhebungsvignette, Sitzung.Status.ABGEBROCHEN
        )
        self.abschrift = abgebrochen
        self._freigeben(self.training)

        self.assertNotIn(_ansehen_url(_sitzung(abgebrochen)), self._kuratierseite())
        self.assertEqual(self._status_fuer(self.ausbilderin), 404)

    def test_freigegebene_abschriften_stehen_nach_namen_sortiert(self) -> None:
        """Die Liste folgt dem Namen der Person, nicht dem Importzeitpunkt."""
        ada_lovelace: Konto = Konto.objects.create_user(
            username="lovelace", first_name="ada", last_name="Lovelace"
        )
        self.training.beitreten(ada_lovelace)
        frueh: Abschrift = self.abschrift
        self.abschrift = abschrift(ada_lovelace, self.erhebungsvignette)
        self.teilnehmerin = ada_lovelace
        self._freigeben(self.training)
        self.abschrift, self.teilnehmerin = frueh, frueh.konto
        self._freigeben(self.training)

        seite: str = self._kuratierseite()

        self.assertLess(seite.index("ada Lovelace"), seite.index("Grace Hopper"))

    def test_kreis_liest_die_freigegebene_sitzung_samt_fremder_szene(self) -> None:
        """Transkript, Diagnose und Szene der fremden Vignette sind lesbar."""
        self._freigeben(self.training)
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(_ansehen_url(_sitzung(self.abschrift)))

        self.assertContains(response, "Ich habe nur oben geteilt.")
        self.assertContains(response, "Nur den Zähler gekürzt.")
        self.assertContains(response, "Kürze den Bruch aus der Erhebung.")

    def test_freigegebene_sitzung_verschweigt_die_denkspur(self) -> None:
        """Der Kreis sieht, was die Teilnehmerin sieht."""
        self._freigeben(self.training)
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(_ansehen_url(_sitzung(self.abschrift)))

        self.assertNotContains(response, "Geheime Denkspur aus der Erhebung.")

    def test_administration_liest_die_freigegebene_sitzung(self) -> None:
        """Die Administration folgt allein aus der Sichtbarkeit des Trainings."""
        self._freigeben(self.training)

        self.assertEqual(
            self._status_fuer(konto_mit_rollen("root", is_superuser=True)), 200
        )

    def test_fremder_kreis_liest_die_freigegebene_sitzung_nicht(self) -> None:
        """Die Freigabe gilt dem Training, nicht jeder Ausbilder:in."""
        self._freigeben(self.training)

        self.assertEqual(
            self._status_fuer(konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)), 404
        )

    def test_fremde_vignette_bleibt_ausserhalb_des_vignettenbestands(self) -> None:
        """Die Kuratierseite bietet die Vignette der Abschrift nicht zum Aufnehmen."""
        self._freigeben(self.training)
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.post(
            reverse(
                "training:vignette_hinzufuegen",
                args=[self.training.pk, self.erhebungsvignette.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_fremde_vignette_fehlt_in_der_vignettenliste_des_kreises(self) -> None:
        """Auch der eigene Vignettenbestand zeigt sie nicht."""
        self.ausbilderin.groups.add(Group.objects.get(name=AUTORIN_GRUPPE))
        self._freigeben(self.training)
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertNotContains(response, "Brüche kürzen")

    def test_fremde_vignette_ist_im_detail_nicht_erreichbar(self) -> None:
        """Der Bestand schützt die Vignette weiter (ADR-0015)."""
        self.ausbilderin.groups.add(Group.objects.get(name=AUTORIN_GRUPPE))
        self._freigeben(self.training)
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(
            reverse("vignetten:detail", args=[self.erhebungsvignette.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_eigene_abschrift_bleibt_der_trainings_sitzungsansicht_fremd(
        self,
    ) -> None:
        """Die Teilnehmerin liest ihre Abschrift weiter auf der Abschriftseite."""
        self._freigeben(self.training)

        self.assertEqual(self._status_fuer(self.teilnehmerin), 404)

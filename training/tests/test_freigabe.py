"""HTTP-Tests der Abschrift-Freigabe für ein Training (ADR-0049)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from konten.navigation import AUTORIN_GRUPPE, AUSBILDERIN_GRUPPE
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.models import Diagnose, Gespraechsschritt, Sitzung, Teilnahme
from training.models import Abschrift, Training
from vignetten.models import Vignette


def _konto(username: str, gruppe: str | None = None, **felder: object) -> Konto:
    # Legt ein Konto an, auf Wunsch mit Rolle.
    konto: Konto = get_user_model().objects.create_user(username=username, **felder)
    if gruppe is not None:
        konto.groups.add(Group.objects.get_or_create(name=gruppe)[0])
    return konto


def _finale_vignette(autorin: Konto, name: str) -> Vignette:
    # Legt eine finale Fassung im Bestand der Autorin an.
    if not Simulationskern.objects.filter(
        zustand=Simulationskern.Zustand.FINAL
    ).exists():
        Simulationskern.objects.anlegen().finalisieren()
    vignette: Vignette = Vignette.objects.anlegen(autorin)
    vignette.historie.name = name
    vignette.historie.save(update_fields=["name"])
    vignette.fehlermuster_beschreibung = "Zähler und Nenner addieren"
    vignette.arbeitsheft_bildbeschreibung = "Falsche Bruchrechnung"
    vignette.lernauftrag_text = "Kürze den Bruch aus der Erhebung."
    vignette.arbeitsheft_text = "4/8 = 2/8"
    vignette.schuelerin_name = "Lea"
    vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.lehrperson_name = "Weber"
    vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.fach = "Mathematik"
    vignette.thema = "Brüche"
    vignette.klassenstufe = "6"
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 3
    vignette.save()
    vignette.finalisieren()
    return vignette


def _abschrift(
    konto: Konto,
    vignette: Vignette,
    status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN,
) -> Abschrift:
    # Legt eine Abschrift mit einer kopierten Sitzung samt Denkspur an.
    abschrift: Abschrift = Abschrift.objects.create(
        teilnahme=Teilnahme.objects.create(),
        konto=konto,
        erhebungsname="Studie Bruchrechnung",
    )
    sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=abschrift.teilnahme,
        vignette=vignette,
        simulationskern=Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.FINAL
        ),
        modell_konfiguration=ModellKonfiguration.objects.belegte(Verwendung.SCHUELERIN),
        status=status,
    )
    Gespraechsschritt.objects.create(
        sitzung=sitzung,
        eingabe="Wie hast du gekürzt?",
        denkspur="Geheime Denkspur aus der Erhebung.",
        aeusserung="Ich habe nur oben geteilt.",
        reihenfolge=1,
    )
    Diagnose.objects.create(sitzung=sitzung, text="Nur den Zähler gekürzt.")
    return abschrift


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
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(bezeichnung="Test", sprachmodell="fake"),
            Verwendung.SCHUELERIN,
        )
        self.ausbilderin: Konto = _konto("ada", AUSBILDERIN_GRUPPE)
        self.forschende: Konto = _konto("rosalind", AUTORIN_GRUPPE)
        self.teilnehmerin: Konto = _konto(
            "grace", first_name="Grace", last_name="Hopper"
        )
        self.erhebungsvignette: Vignette = _finale_vignette(
            self.forschende, "Brüche kürzen"
        )
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.veroeffentlichen()
        self.training.beitreten(self.teilnehmerin)
        self.abschrift: Abschrift = _abschrift(
            self.teilnehmerin, self.erhebungsvignette
        )

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
        return self.client.get(
            reverse("training:abschrift", args=[self.abschrift.pk])
        ).content.decode()

    def _kuratierseite(self, konto: Konto | None = None) -> str:
        # Liest die Kuratierseite des Trainings aus Sicht des Kreises.
        self.client.force_login(konto or self.ausbilderin)
        return self.client.get(
            reverse("training:kuratieren", args=[self.training.pk])
        ).content.decode()

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
            _konto("hedy", AUSBILDERIN_GRUPPE), name="Anderes Seminar"
        )
        fremdes_training.veroeffentlichen()

        response: HttpResponse = self._freigeben(fremdes_training)

        self.assertEqual(response.status_code, 404)

    def test_abgewiesene_freigabe_oeffnet_keine_fremdeinsicht(self) -> None:
        """Auch der Kreis des fremden Trainings sieht danach nichts."""
        fremder_kreis: Konto = _konto("hedy", AUSBILDERIN_GRUPPE)
        fremdes_training: Training = Training.objects.anlegen(
            fremder_kreis, name="Anderes Seminar"
        )
        fremdes_training.veroeffentlichen()

        self._freigeben(self.training, fremdes_training)

        self.assertEqual(self._status_fuer(fremder_kreis), 404)

    def test_fremde_abschrift_laesst_sich_nicht_freigeben(self) -> None:
        """Freigeben kann nur, wem die Abschrift gehört."""
        fremde: Konto = _konto("linus")
        self.training.beitreten(fremde)
        self.client.force_login(fremde)

        response: HttpResponse = self.client.post(
            reverse("training:abschrift_freigaben", args=[self.abschrift.pk]),
            {"training": [self.training.pk]},
        )

        self.assertEqual(response.status_code, 404)

    def test_freigeben_verlangt_post(self) -> None:
        """Ein GET ändert keine Freigabe."""
        self.client.force_login(self.teilnehmerin)

        response: HttpResponse = self.client.get(
            reverse("training:abschrift_freigaben", args=[self.abschrift.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_freigabe_gelingt_unabhaengig_von_den_vignetten_des_trainings(
        self,
    ) -> None:
        """Das Training ist leer; die Abschrift wird trotzdem eingesehen."""
        self._freigeben(self.training)

        self.assertEqual(self._status_fuer(self.ausbilderin), 200)

    def test_abschrift_laesst_sich_fuer_mehrere_trainings_freigeben(self) -> None:
        """Beide Kreise sehen dieselbe Abschrift."""
        zweiter_kreis: Konto = _konto("hedy", AUSBILDERIN_GRUPPE)
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
            _konto("hedy", AUSBILDERIN_GRUPPE), name="Anderes Seminar"
        ).veroeffentlichen()

        seite: str = self._abschriftseite()

        self.assertIn("Bruchrechnung", seite)
        self.assertNotIn("Anderes Seminar", seite)

    def test_abschriftseite_zeigt_die_aktuelle_freigabe_angehakt(self) -> None:
        """Ein freigegebenes Training ist in der Liste angehakt."""
        self._freigeben(self.training)

        seite: str = self._abschriftseite()

        self.assertIn(f'value="{self.training.pk}" checked', seite)

    def test_abschriftseite_zeigt_ohne_freigabe_nichts_angehakt(self) -> None:
        """Eine private Abschrift hat keinen Haken."""
        self.assertNotIn("checked", self._abschriftseite())

    def test_abschriftseite_nennt_die_freigegebenen_trainings_im_kopf(self) -> None:
        """Der Untertitel sagt, wer mitliest."""
        self._freigeben(self.training)

        seite: str = self._abschriftseite()

        self.assertIn("Freigegeben für Bruchrechnung.", seite)
        self.assertNotIn("nur Sie lesen sie", seite)

    def test_private_abschrift_bleibt_im_kopf_privat(self) -> None:
        """Ohne Freigabe liest nur die Teilnehmerin."""
        self.assertIn("nur Sie lesen sie", self._abschriftseite())

    def test_abschriftseite_nennt_keinen_export(self) -> None:
        """Kein Hinweis zu bereits gezogenen Trainingsexporten (#362)."""
        self.assertNotIn("Export", self._abschriftseite())

    def test_widerruf_beendet_die_fremdeinsicht_sofort(self) -> None:
        """Eine gemerkte Adresse liefert nach dem Widerruf 404."""
        self._freigeben(self.training)

        self._freigeben()

        self.assertEqual(self._status_fuer(self.ausbilderin), 404)

    def test_widerruf_entfernt_die_abschrift_aus_der_kuratierseite(self) -> None:
        """Die Liste unter der Tabelle zeigt sie nicht mehr."""
        self._freigeben(self.training)

        self._freigeben()

        self.assertNotIn("Studie Bruchrechnung", self._kuratierseite())

    def test_loeschen_der_abschrift_beendet_die_fremdeinsicht(self) -> None:
        """Mit der Abschrift verschwinden ihre Freigaben und Sitzungen."""
        self._freigeben(self.training)
        url: str = _ansehen_url(_sitzung(self.abschrift))
        self.client.post(
            reverse("training:abschrift_loeschen", args=[self.abschrift.pk])
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class FremdeinsichtInAbschriftenTests(FreigabeTestCase):
    """Die freigegebene Abschrift in der Fremdeinsicht des Kreises."""

    def test_private_abschrift_ist_fuer_den_kreis_nicht_einsehbar(self) -> None:
        """Ohne Freigabe antwortet die Sitzung mit 404."""
        self.assertEqual(self._status_fuer(self.ausbilderin), 404)

    def test_private_abschrift_ist_fuer_die_administration_nicht_einsehbar(
        self,
    ) -> None:
        """Auch die Administration hat ohne Freigabe keine Einsicht."""
        self.assertEqual(self._status_fuer(_konto("root", is_superuser=True)), 404)

    def test_private_abschrift_fehlt_auf_der_kuratierseite(self) -> None:
        """Weder Kreis noch Administration finden sie unter der Tabelle."""
        administratorin: Konto = _konto("root", is_superuser=True)

        self.assertNotIn("Studie Bruchrechnung", self._kuratierseite())
        self.assertNotIn("Studie Bruchrechnung", self._kuratierseite(administratorin))

    def test_kuratierseite_meldet_wenn_niemand_freigegeben_hat(self) -> None:
        """Die leere Liste sagt es ausdrücklich."""
        self.assertIn("Niemand hat eine Abschrift freigegeben.", self._kuratierseite())

    def test_freigegebene_abschrift_steht_mit_name_erhebung_und_importzeit(
        self,
    ) -> None:
        """Beschriftet wird der Importzeitpunkt, nicht die Spielzeit."""
        self._freigeben(self.training)
        importiert: str = self.abschrift.importiert_am.astimezone().strftime("%d.%m.%Y")

        seite: str = self._kuratierseite()

        self.assertIn("Grace Hopper", seite)
        self.assertIn("Studie Bruchrechnung", seite)
        self.assertIn(importiert, seite)

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
        abgebrochen: Abschrift = _abschrift(
            self.teilnehmerin, self.erhebungsvignette, Sitzung.Status.ABGEBROCHEN
        )
        self.abschrift = abgebrochen
        self._freigeben(self.training)

        self.assertNotIn(_ansehen_url(_sitzung(abgebrochen)), self._kuratierseite())
        self.assertEqual(self._status_fuer(self.ausbilderin), 404)

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

        self.assertEqual(self._status_fuer(_konto("root", is_superuser=True)), 200)

    def test_fremder_kreis_liest_die_freigegebene_sitzung_nicht(self) -> None:
        """Die Freigabe gilt dem Training, nicht jeder Ausbilder:in."""
        self._freigeben(self.training)

        self.assertEqual(self._status_fuer(_konto("hedy", AUSBILDERIN_GRUPPE)), 404)

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
        self.ausbilderin.groups.add(Group.objects.get_or_create(name=AUTORIN_GRUPPE)[0])
        self._freigeben(self.training)
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(reverse("vignetten:liste"))

        self.assertNotContains(response, "Brüche kürzen")

    def test_fremde_vignette_ist_im_detail_nicht_erreichbar(self) -> None:
        """Der Bestand schützt die Vignette weiter (ADR-0015)."""
        self.ausbilderin.groups.add(Group.objects.get_or_create(name=AUTORIN_GRUPPE)[0])
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

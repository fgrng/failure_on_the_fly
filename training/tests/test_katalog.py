"""HTTP-Tests für den Trainingskatalog."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.models import (
    Diagnose,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
)
from training.models import Training, Trainingsbindung
from training.tests.seite import tabellenzeilen
from vignetten.models import Vignette


def _katalogzeilen(response: HttpResponse) -> list[tuple[object, object, object]]:
    # Liest je Katalogzeile Name, Ziel und Aktion.

    return [
        (zeile["name"], zeile["url"], zeile["action_label"])
        for zeile in tabellenzeilen(response)
    ]


class TrainingskatalogTests(TestCase):
    """Beigetretene Konten wählen frei aus ihren Trainings."""

    def test_zeigt_beigetretene_trainings_im_katalog_und_in_der_navigation(
        self,
    ) -> None:
        """Ein beigetretenes Konto findet das Training im Katalog."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        training.veroeffentlichen()
        self.client.force_login(studierende)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertContains(response, "Bruchrechnung")
        self.assertContains(response, reverse("training:detail", args=[training.pk]))
        self.assertContains(response, reverse("training:katalog"))

    def test_zeilen_sind_ueber_den_namen_verlinkt(self) -> None:
        """Eine Zeile nennt Name, Ziel und Aktion des beigetretenen Trainings."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        training.veroeffentlichen()
        self.client.force_login(studierende)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        detail_url: str = reverse("training:detail", args=[training.pk])
        self.assertContains(response, detail_url)
        self.assertEqual(
            _katalogzeilen(response),
            [("Bruchrechnung", detail_url, "Öffnen")],
        )

    def test_ausbilderin_kuratiert_eigene_entwuerfe_aus_dem_katalog(self) -> None:
        """Der Kreis findet seinen Entwurf im Katalog und gelangt zum Kuratieren."""
        ausbilderin: Konto = konto_mit_rollen("ada", "Ausbilder:in")
        entwurf: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        self.client.force_login(ausbilderin)

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        kuratier_url: str = reverse("training:kuratieren", args=[entwurf.pk])
        self.assertContains(response, kuratier_url)
        self.assertEqual(
            _katalogzeilen(response),
            [("Bruchrechnung", kuratier_url, "Kuratieren")],
        )

    def test_versteckt_unveroeffentlichte_trainings(self) -> None:
        """Entwürfe erscheinen weder im Katalog noch über ihre Detail-URL."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        entwurf: Training = Training.objects.anlegen(
            ausbilderin, name="Versteckte Bruchrechnung"
        )
        self.client.force_login(studierende)

        katalog: HttpResponse = self.client.get(reverse("training:katalog"))
        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[entwurf.pk])
        )

        self.assertNotContains(katalog, "Versteckte Bruchrechnung")
        self.assertEqual(detail.status_code, 404)

    def test_listet_finale_vignetten_und_bestaetigt_freie_wahl(self) -> None:
        """Eine veröffentlichte Sammlung verlinkt jede eingebundene Vignette."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        vignette: Vignette = finale_vignette(ausbilderin, name="Brüche vergleichen")
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(studierende)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))

        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[training.pk])
        )
        wahl_url: str = reverse("training:wahl", args=[training.pk, vignette.pk])
        wahl: HttpResponse = self.client.get(wahl_url)

        self.assertContains(detail, "Brüche vergleichen")
        self.assertContains(detail, wahl_url)
        self.assertContains(wahl, "Vignette gewählt")

    def test_katalog_erfordert_anmeldung(self) -> None:
        """Ohne Konto führt der Katalog zum Login statt Inhalte preiszugeben."""
        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('training:katalog')}",
            fetch_redirect_response=False,
        )

    def test_versteckt_nachtraeglich_archivierte_vignette(self) -> None:
        """Archivierte Fassungen bleiben trotz bestehender Bindung unspielbar."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        vignette: Vignette = finale_vignette(ausbilderin, name="Archivierte Brüche")
        training.vignetten.add(vignette)
        vignette.archivieren()
        training.veroeffentlichen()
        self.client.force_login(studierende)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))

        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[training.pk])
        )
        wahl: HttpResponse = self.client.get(
            reverse("training:wahl", args=[training.pk, vignette.pk])
        )

        self.assertNotContains(detail, "Archivierte Brüche")
        self.assertEqual(wahl.status_code, 404)

    def test_spielt_vignette_persistiert_und_verwendet_die_trainingsbindung_wieder(
        self,
    ) -> None:
        """Die freie Wahl führt über den DB-Sink zu einer abgeschlossenen Sitzung."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        kern: Simulationskern = Simulationskern.objects.anlegen(
            rahmenhandlung_einleitung="Frau Weber begleitet Sie.",
            rahmenhandlung_gespraechseinleitung="Mia zeigt Ihnen ihre Bearbeitung.",
            rahmenhandlung_debrief="Frau Weber fragt nach Ihrer Diagnose.",
        )
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Mia addiert Zähler und Nenner.",
                        "aeusserung": "Ich addiere einfach alles.",
                    }
                ]
            },
        )
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        vignette: Vignette = finale_vignette(ausbilderin, name="Brüche vergleichen")
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(studierende)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        wahl_url: str = reverse("training:wahl", args=[training.pk, vignette.pk])

        self.client.post(wahl_url)
        einleitung: HttpResponse = self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "ja"},
        )

        self.assertContains(einleitung, "Frau Weber begleitet Sie.")
        self.assertContains(einleitung, "Mia zeigt Ihnen ihre Bearbeitung.")
        self.assertEqual(Teilnahme.objects.count(), 1)
        self.assertEqual(Trainingsbindung.objects.count(), 1)
        gespraech: HttpResponse = self.client.post(
            reverse("training:gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(gespraech, "Ich addiere einfach alles.")
        self.assertNotContains(gespraech, "Mia addiert Zähler und Nenner.")
        schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
        self.assertEqual(schritt.denkspur, "Mia addiert Zähler und Nenner.")
        debrief: HttpResponse = self.client.post(reverse("training:gespraech_beenden"))

        self.assertContains(debrief, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertContains(debrief, "Diagnose aufnehmen")
        fertig: HttpResponse = self.client.post(
            reverse("training:debrief"),
            {"diagnose": "Mia addiert Zähler und Nenner."},
        )

        self.assertRedirects(fertig, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertEqual(
            Diagnose.objects.get(sitzung=sitzung).text, "Mia addiert Zähler und Nenner."
        )

        self.client.post(wahl_url)

        self.assertEqual(Sitzung.objects.count(), 2)
        self.assertEqual(Teilnahme.objects.count(), 1)
        self.assertEqual(
            Trainingsbindung.objects.get().teilnahme_id, sitzung.teilnahme_id
        )

    def test_einwilligung_wird_an_der_teilnahme_gespeichert_bevor_die_sitzung_startet(
        self,
    ) -> None:
        """Audioverarbeitung beginnt erst nach der dokumentierten Einwilligung."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        teilnehmerin: Konto = konto_mit_rollen("grace")
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        vignette: Vignette = finale_vignette(ausbilderin, name="Brüche vergleichen")
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        wahl_url: str = reverse("training:wahl", args=[training.pk, vignette.pk])

        einwilligung: HttpResponse = self.client.post(wahl_url)

        self.assertContains(einwilligung, "Audio zur Transkription")
        self.assertFalse(Sitzung.objects.exists())
        teilnahme: Teilnahme = Teilnahme.objects.get()
        self.assertFalse(teilnahme.hat_in_audioverarbeitung_eingewilligt)

        ungueltig: HttpResponse = self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "vielleicht"},
        )

        self.assertEqual(ungueltig.status_code, 400)
        teilnahme.refresh_from_db()
        self.assertIsNone(teilnahme.audioverarbeitung_eingewilligt)
        self.assertFalse(Sitzung.objects.exists())

        start: HttpResponse = self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "ja"},
        )

        teilnahme.refresh_from_db()
        self.assertTrue(teilnahme.hat_in_audioverarbeitung_eingewilligt)
        self.assertContains(start, "Die Ausgangslage")

        wiederholung: HttpResponse = self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "nein"},
        )

        self.assertEqual(wiederholung.status_code, 400)
        teilnahme.refresh_from_db()
        self.assertTrue(teilnahme.hat_in_audioverarbeitung_eingewilligt)


class TrainingshistorieTests(TestCase):
    """Die Historie fasst je Trainingsbindung Fortschritt und Sitzungen zusammen."""

    def test_historie_zeigt_fortschritt_und_sitzungen_nach_status(self) -> None:
        """Eine abgeschlossene von zwei Vignetten, dazu eine abgebrochene Sitzung."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        teilnehmerin: Konto = konto_mit_rollen("grace")
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        erste: Vignette = finale_vignette(ausbilderin, name="Erste")
        zweite: Vignette = finale_vignette(ausbilderin, name="Zweite")
        training.vignetten.add(erste, zweite)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.client.post(reverse("training:wahl", args=[training.pk, erste.pk]))
        self.client.post(
            reverse("training:einwilligung", args=[training.pk, erste.pk]),
            {"audioverarbeitung_eingewilligt": "nein"},
        )
        self.client.post(reverse("training:gespraech_beenden"))
        self.client.post(reverse("training:debrief"), {"diagnose": "Bruch"})
        self.client.post(reverse("training:wahl", args=[training.pk, zweite.pk]))
        self.client.post(
            reverse("training:einwilligung", args=[training.pk, zweite.pk]),
            {"audioverarbeitung_eingewilligt": "nein"},
        )
        self.client.post(reverse("training:abbrechen"))

        response: HttpResponse = self.client.get(reverse("training:historie"))

        detail_url: str = reverse("training:detail", args=[training.pk])
        self.assertContains(response, detail_url)
        self.assertContains(response, "Ansehen ›")
        [zeile] = tabellenzeilen(response)
        self.assertEqual(
            (zeile["name"], zeile["url"], zeile["fortschritt"]),
            ("Bruchrechnung", detail_url, "1 / 2"),
        )
        self.assertEqual(
            zeile["sitzungen_nach_status"],
            {"laufend": 0, "abgeschlossen": 1, "abgebrochen": 1, "gescheitert": 0},
        )


class TrainingsabbruchTests(TestCase):
    """Teilnehmer:innen können eine Trainingssitzung gewollt abbrechen."""

    def _sitzung_starten(
        self,
        skript: list[dict[str, str]] | None = None,
        *,
        audioverarbeitung_eingewilligt: bool = True,
    ) -> Training:
        """Startet eine persistierte Trainingssitzung mit einem Fake-Skript."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        teilnehmerin: Konto = konto_mit_rollen("grace")
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test", sprachmodell="fake", parameter={"skript": skript or []}
        )
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        vignette: Vignette = finale_vignette(ausbilderin, name="Brüche vergleichen")
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.client.post(reverse("training:wahl", args=[training.pk, vignette.pk]))
        self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {
                "audioverarbeitung_eingewilligt": (
                    "ja" if audioverarbeitung_eingewilligt else "nein"
                )
            },
        )
        return training

    def test_ablehnung_startet_das_training_mit_tastatureingabe(self) -> None:
        """Die verweigerte Einwilligung ist kein Abbruch der Teilnahme."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}],
            audioverarbeitung_eingewilligt=False,
        )

        response: HttpResponse = self.client.post(
            reverse("training:gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(response, "Ich addiere alles.")
        self.assertFalse(Teilnahme.objects.get().hat_in_audioverarbeitung_eingewilligt)

    def test_abbrechen_beendet_die_sitzung_ohne_diagnose(self) -> None:
        """Der aktive Abbruch bleibt von Abschluss und technischem Fehlschlag getrennt."""
        training: Training = self._sitzung_starten()

        response: HttpResponse = self.client.post(reverse("training:abbrechen"))

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

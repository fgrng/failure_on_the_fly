"""HTTP-Tests für den offenen Trainingskatalog."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Diagnose, Fehlversuch, Gespraechsschritt, Sitzung, Teilnahme
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette, Vignettenhistorie


class TrainingskatalogTests(TestCase):
    """Eingeloggte Konten wählen frei aus veröffentlichten Trainings."""

    def test_zeigt_veroeffentlichte_trainings_im_katalog_und_in_der_navigation(
        self,
    ) -> None:
        """Jedes eingeloggte Konto findet alle veröffentlichten Trainings."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        training.veroeffentlichen()
        self.client.force_login(studierende)

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertContains(response, "Bruchrechnung")
        self.assertContains(response, reverse("training:detail", args=[training.pk]))
        self.assertContains(response, reverse("training:katalog"))

    def test_versteckt_unveroeffentlichte_trainings(self) -> None:
        """Entwürfe erscheinen weder im Katalog noch über ihre Detail-URL."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        entwurf: Training = Training.objects.create(
            name="Versteckte Bruchrechnung", eigentuemerin=ausbilderin
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
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Brüche vergleichen"
        )
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="3/4 ist größer als 2/3.",
        )
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(studierende)

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
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Archivierte Brüche"
        )
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="3/4 ist größer als 2/3.",
        )
        training.vignetten.add(vignette)
        vignette.archivieren()
        training.veroeffentlichen()
        self.client.force_login(studierende)

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
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        kern: Simulationskern = Simulationskern.objects.anlegen(
            rahmenhandlung_einleitung="Frau Weber begleitet Sie.",
            rahmenhandlung_gespraechseinleitung="Mia zeigt Ihnen ihre Bearbeitung.",
            rahmenhandlung_debrief="Frau Weber fragt nach Ihrer Diagnose.",
        )
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
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
        ModellKonfiguration.objects.aktivieren(konfiguration)
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Brüche vergleichen"
        )
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag="Addiere zwei Brüche.",
            arbeitsheft_beschreibung="Mia rechnet 1/2 + 1/3 = 2/5.",
            arbeitsheft_text="1/2 + 1/3 = 2/5",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Weber",
            lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
            fach="Mathematik",
            thema="Brüche",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=3,
            gepinnter_kern=kern,
        )
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(studierende)
        wahl_url: str = reverse("training:wahl", args=[training.pk, vignette.pk])

        einleitung: HttpResponse = self.client.post(wahl_url)

        self.assertContains(einleitung, "Frau Weber begleitet Sie.")
        self.assertContains(einleitung, "Mia zeigt Ihnen ihre Bearbeitung.")
        self.assertEqual(Teilnahme.objects.count(), 1)
        self.assertEqual(Trainingsbindung.objects.count(), 1)
        gespraech: HttpResponse = self.client.post(
            reverse("sitzungen:training_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(gespraech, "Ich addiere einfach alles.")
        self.assertNotContains(gespraech, "Mia addiert Zähler und Nenner.")
        schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
        self.assertEqual(schritt.denkspur, "Mia addiert Zähler und Nenner.")
        debrief: HttpResponse = self.client.post(reverse("sitzungen:training_beenden"))

        self.assertContains(debrief, "Frau Weber fragt nach Ihrer Diagnose.")
        fertig: HttpResponse = self.client.post(
            reverse("sitzungen:training_debrief"),
            {"diagnose": "Mia addiert Zähler und Nenner."},
        )

        self.assertRedirects(fertig, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertEqual(Diagnose.objects.get(sitzung=sitzung).text, "Mia addiert Zähler und Nenner.")

        self.client.post(wahl_url)

        self.assertEqual(Sitzung.objects.count(), 2)
        self.assertEqual(Teilnahme.objects.count(), 1)
        self.assertEqual(Trainingsbindung.objects.get().teilnahme_id, sitzung.teilnahme_id)


class TrainingsabbruchTests(TestCase):
    """Teilnehmer:innen können eine Trainingssitzung gewollt abbrechen."""

    def _sitzung_starten(
        self, skript: list[dict[str, str]] | None = None
    ) -> Training:
        """Startet eine persistierte Trainingssitzung mit einem Fake-Skript."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        teilnehmerin: Konto = get_user_model().objects.create_user(username="grace")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter={"skript": skript or []}
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        vignette: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(name="Brüche vergleichen"),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="1/2 + 1/3 = 2/5",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Weber",
            lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
            gepinnter_kern=kern,
        )
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.post(reverse("training:wahl", args=[training.pk, vignette.pk]))
        return training

    def test_abbrechen_beendet_die_sitzung_ohne_diagnose(self) -> None:
        """Der aktive Abbruch bleibt von Abschluss und technischem Fehlschlag getrennt."""
        training: Training = self._sitzung_starten()

        response: HttpResponse = self.client.post(reverse("sitzungen:training_abbrechen"))

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

    def test_endgueltiger_fehlschlag_bewahrt_abbruchschritt_und_fehler(self) -> None:
        """Der technische Abbruch bleibt mit Fehlversuchen statt Diagnose erhalten."""
        self._sitzung_starten([{"fehler": "anbieterfehler"}] * 3)

        response: HttpResponse = self.client.post(
            reverse("sitzungen:training_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(response, "Die Antwort konnte nicht erzeugt werden.")
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.GESCHEITERT)
        schritt: Gespraechsschritt = Gespraechsschritt.objects.get(sitzung=sitzung)
        self.assertIsNone(schritt.aeusserung)
        self.assertEqual(Fehlversuch.objects.filter(gespraechsschritt=schritt).count(), 3)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

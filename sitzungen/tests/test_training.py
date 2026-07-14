"""HTTP-Tests der persistierten Trainingssitzung."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Diagnose, Gespraechsschritt, Sitzung
from training.models import Training
from vignetten.models import Vignette, Vignettenhistorie


class TrainingssitzungTests(TestCase):
    """Die Sitzungs-Views bewahren terminale Trainingszustände."""

    def _sitzung_starten(self, skript: list[dict[str, str]]) -> Training:
        """Startet eine Trainingssitzung mit dem übergebenen Fake-Skript."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        teilnehmerin: Konto = get_user_model().objects.create_user(username="grace")
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={"skript": skript},
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        vignette: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(name="Brüche vergleichen"),
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
        self.client.force_login(teilnehmerin)
        self.client.post(reverse("training:wahl", args=[training.pk, vignette.pk]))
        return training

    def test_endgueltiger_fehlschlag_bleibt_gescheitert(self) -> None:
        """Ein answerless Schritt zeigt den Fehler und lässt keine Diagnose mehr zu."""
        self._sitzung_starten([{"fehler": "anbieterfehler"}] * 3)

        fehlermeldung: HttpResponse = self.client.post(
            reverse("sitzungen:training_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(fehlermeldung, "Die Antwort konnte nicht erzeugt werden.")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.GESCHEITERT)
        self.assertIsNone(Gespraechsschritt.objects.get().aeusserung)
        self.client.post(reverse("sitzungen:training_beenden"))
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.GESCHEITERT)

    def test_abbrechen_setzt_den_gewollten_status_ohne_diagnose(self) -> None:
        """Ein aktiver Abbruch bleibt vom technischen Scheitern unterscheidbar."""
        training: Training = self._sitzung_starten([])

        response: HttpResponse = self.client.post(reverse("sitzungen:training_abbrechen"))

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

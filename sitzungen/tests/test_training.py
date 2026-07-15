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

    def _sitzung_starten(
        self,
        skript: list[dict[str, str]],
        *,
        budget_typ: Vignette.BudgetTyp = Vignette.BudgetTyp.SCHRITTE,
        budget_wert: int = 3,
        audioverarbeitung_eingewilligt: bool = True,
    ) -> Training:
        """Startet eine Trainingssitzung mit dem übergebenen Fake-Skript."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        teilnehmerin: Konto = get_user_model().objects.create_user(username="grace")
        kern: Simulationskern = Simulationskern.objects.anlegen(
            rahmenhandlung_gespraechseinleitung=(
                "$schuelerin_name zeigt Ihnen die Bearbeitung."
            )
        )
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
            budget_typ=budget_typ,
            budget_wert=budget_wert,
            gepinnter_kern=kern,
        )
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.post(
            reverse("training:wahl", args=[training.pk, vignette.pk])
        )
        self.start_response: HttpResponse = self.client.post(
            reverse("training:einwilligung", args=[training.pk, vignette.pk]),
            {
                "audioverarbeitung_eingewilligt": (
                    "ja" if audioverarbeitung_eingewilligt else "nein"
                )
            },
        )
        return training

    def test_training_startet_mit_rahmenhandlung_und_eingabefeld(self) -> None:
        """Auch die persistierte Sitzung beginnt vollständig auf einer Seite."""

        self._sitzung_starten([])

        self.assertContains(self.start_response, "Die Ausgangslage")
        self.assertContains(self.start_response, "rahmenhandlung-einstieg.webp")
        self.assertContains(self.start_response, "gespraechsanlass.webp")
        self.assertContains(self.start_response, "Mia zeigt Ihnen die Bearbeitung.")
        self.assertContains(self.start_response, "Addiere zwei Brüche.")
        self.assertContains(self.start_response, "1/2 + 1/3 = 2/5")
        self.assertContains(self.start_response, "Ihre nächste Frage")
        self.assertContains(self.start_response, "Aufnahme starten")
        self.assertNotContains(self.start_response, "Gespräch beginnen")

    def test_training_ohne_audioeinwilligung_zeigt_nur_tastatureingabe(self) -> None:
        """Abgelehnte Einwilligung blendet die Aufnahme-Steuerung aus."""

        self._sitzung_starten([], audioverarbeitung_eingewilligt=False)

        self.assertContains(self.start_response, "Ihre nächste Frage")
        self.assertNotContains(self.start_response, "Aufnahme starten")

    def test_debrief_ohne_audioeinwilligung_zeigt_nur_tastatureingabe(self) -> None:
        """Auch die Diagnose bleibt ohne Einwilligung per Tastatur abschließbar."""
        training: Training = self._sitzung_starten([], audioverarbeitung_eingewilligt=False)

        debrief: HttpResponse = self.client.post(reverse("sitzungen:training_beenden"))

        self.assertContains(debrief, 'id="diagnose"')
        self.assertNotContains(debrief, "data-spracheingabe")
        ende: HttpResponse = self.client.post(
            reverse("sitzungen:training_debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertRedirects(ende, reverse("training:detail", args=[training.pk]))
        self.assertEqual(Diagnose.objects.get().text, "Bruchfehler")

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
        self.client.post(reverse("sitzungen:training_beenden"))

        response: HttpResponse = self.client.post(reverse("sitzungen:training_abbrechen"))

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

        session = self.client.session
        session["training_sitzung_pk"] = sitzung.pk
        session.save()
        stale_diagnose: HttpResponse = self.client.post(
            reverse("sitzungen:training_debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertRedirects(stale_diagnose, reverse("training:detail", args=[training.pk]))
        sitzung.refresh_from_db()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

    def test_schrittbudget_zeigt_debrief_bei_laufender_sitzung(self) -> None:
        """Auch ein ausgeschöpftes Schrittbudget schließt erst mit Diagnose ab."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}],
            budget_wert=1,
        )

        debrief: HttpResponse = self.client.post(
            reverse("sitzungen:training_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(debrief, "Debrief")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.exists())

        fertig: HttpResponse = self.client.post(
            reverse("sitzungen:training_debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertEqual(fertig.status_code, 302)
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertEqual(Diagnose.objects.get().text, "Bruchfehler")

    def test_debrief_nach_vorzeitigem_gespraechsende_bleibt_laufend(self) -> None:
        """Der Debrief schließt die Sitzung erst mit ihrer Diagnose ab."""
        training: Training = self._sitzung_starten([])
        self.client.post(reverse("sitzungen:training_beenden"))

        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

        response: HttpResponse = self.client.post(
            reverse("sitzungen:training_debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertEqual(Diagnose.objects.get(sitzung=sitzung).text, "Bruchfehler")

    def test_zeitbudget_zeigt_debrief_bei_laufender_sitzung(self) -> None:
        """Auch ein ausgeschöpftes Zeitbudget schließt erst mit Diagnose ab."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}],
            budget_typ=Vignette.BudgetTyp.ZEIT,
            budget_wert=0,
        )

        debrief: HttpResponse = self.client.post(
            reverse("sitzungen:training_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(debrief, "Debrief")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.exists())

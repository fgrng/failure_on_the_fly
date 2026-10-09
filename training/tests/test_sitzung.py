"""HTTP-Tests der persistierten Trainingssitzung."""

from datetime import UTC, datetime

import time_machine
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from config.tests.formular import submit_knoepfe
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.models import Diagnose, Eingabemodus, Gespraechsschritt, Sitzung
from training.models import Training
from vignetten.models import Vignette


class TrainingssitzungTests(TestCase):
    """Die Sitzungs-Views bewahren terminale Trainingszustände."""

    def _sitzung_starten(
        self,
        skript: list[dict[str, str]],
        *,
        budget_typ: Vignette.BudgetTyp = Vignette.BudgetTyp.SCHRITTE,
        budget_wert: int = 3,
        audioverarbeitung_eingewilligt: bool = True,
        kern_ueberholen: bool = False,
        lernauftrag_text: str = "Addiere zwei Brüche.",
        arbeitsheft_text: str = "1/2 + 1/3 = 2/5",
    ) -> Training:
        """Startet eine Trainingssitzung mit dem übergebenen Fake-Skript."""
        ausbilderin: Konto = konto_mit_rollen("ada")
        teilnehmerin: Konto = konto_mit_rollen("grace")
        kern: Simulationskern = Simulationskern.objects.anlegen(
            rahmenhandlung_gespraechseinleitung=(
                "**$schuelerin_name** zeigt Ihnen die Bearbeitung."
            )
        )
        kern.finalisieren()
        self.konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={"skript": skript},
        )
        ModellKonfiguration.objects.aktivieren(
            self.konfiguration, Verwendung.SCHUELERIN
        )
        training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
        vignette: Vignette = finale_vignette(
            ausbilderin,
            name="Brüche vergleichen",
            lernauftrag_text=lernauftrag_text,
            arbeitsheft_bildbeschreibung="Mia rechnet 1/2 + 1/3 = 2/5.",
            arbeitsheft_text=arbeitsheft_text,
            schuelerin_name="Mia",
            lehrperson_name="Weber",
            thema="Brüche",
            klassenstufe="5",
            budget_typ=budget_typ,
            budget_wert=budget_wert,
        )
        if kern_ueberholen:
            kern.bearbeiten().finalisieren()
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(teilnehmerin)
        self.client.get(reverse("training:beitreten", args=[training.trainings_link]))
        self.client.post(reverse("training:wahl", args=[training.pk, vignette.pk]))
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
        self.assertContains(self.start_response, "rahmenhandlung-einstieg-w.webp")
        self.assertContains(self.start_response, "gespraechsanlass-w.webp")
        self.assertContains(
            self.start_response, "<strong>Mia</strong> zeigt Ihnen die Bearbeitung."
        )
        self.assertContains(self.start_response, "Addiere zwei Brüche.")
        self.assertContains(self.start_response, "1/2 + 1/3 = 2/5")
        self.assertContains(self.start_response, "Ihre nächste Frage")
        self.assertContains(self.start_response, "Spracheingabe starten")
        self.assertNotContains(self.start_response, "Gespräch beginnen")

    def test_aktionszeile_traegt_beenden_erklaersatz_und_abbrechen(self) -> None:
        """Die Aktionszeile bietet Beenden mit Erklärsatz und den Abbruch an."""

        self._sitzung_starten([])

        self.assertIn(("Gespräch beenden →", None), submit_knoepfe(self.start_response))
        self.assertContains(
            self.start_response,
            "Genug gefragt? Danach folgt der Debrief mit Ihrer Diagnose.",
        )
        self.assertContains(
            self.start_response, f'action="{reverse("training:abbrechen")}"'
        )

    def test_training_liest_die_schuelerin_nicht_lehrperson_oder_bewerter(
        self,
    ) -> None:
        """Ein Wechsel der Eval-Verwendungen ändert am Training nichts."""

        andere: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Andere", sprachmodell="fake"
        )
        ModellKonfiguration.objects.aktivieren(andere, Verwendung.LEHRPERSON)
        ModellKonfiguration.objects.aktivieren(andere, Verwendung.BEWERTER)

        self._sitzung_starten([])

        self.assertEqual(Sitzung.objects.get().modell_konfiguration, self.konfiguration)

    def test_training_spielt_eine_vignette_mit_ueberholtem_kern(self) -> None:
        """Gespielt wird, worauf gepinnt wurde (ADR-0003) — auch überholt."""

        self._sitzung_starten([], kern_ueberholen=True)

        self.assertContains(
            self.start_response, "<strong>Mia</strong> zeigt Ihnen die Bearbeitung."
        )
        self.assertEqual(
            Sitzung.objects.get().simulationskern.zustand,
            Simulationskern.Zustand.ARCHIVIERT,
        )

    def test_startseite_bindet_die_spracheingabe_an_die_laufende_sitzung(self) -> None:
        """Schon die erste Seite kennt die Sitzung, der Aufnahmen zugeordnet werden."""

        self._sitzung_starten([])

        self.assertContains(
            self.start_response, f'data-sitzung-pk="{Sitzung.objects.get().pk}"'
        )

    def test_training_ohne_audioeinwilligung_zeigt_nur_tastatureingabe(self) -> None:
        """Abgelehnte Einwilligung blendet die Aufnahme-Steuerung aus."""

        self._sitzung_starten([], audioverarbeitung_eingewilligt=False)

        self.assertContains(self.start_response, "Ihre nächste Frage")
        self.assertNotContains(self.start_response, "Spracheingabe starten")
        self.assertContains(
            self.start_response,
            "Spracheingabe nicht freigegeben. Sie nutzen die Tastatur.",
        )

    def test_debrief_ohne_audioeinwilligung_zeigt_nur_tastatureingabe(self) -> None:
        """Auch die Diagnose bleibt ohne Einwilligung per Tastatur abschließbar."""
        self._sitzung_starten([], audioverarbeitung_eingewilligt=False)

        debrief: HttpResponse = self.client.post(reverse("training:gespraech_beenden"))

        self.assertContains(debrief, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(debrief, "Spracheingabe starten")
        self.assertContains(
            debrief, "Spracheingabe nicht freigegeben. Sie nutzen die Tastatur."
        )

    def test_endgueltiger_fehlschlag_bleibt_gescheitert(self) -> None:
        """Ein answerless Schritt zeigt den Fehler und lässt keine Diagnose mehr zu."""
        self._sitzung_starten([{"fehler": "anbieterfehler"}] * 3)

        fehlermeldung: HttpResponse = self.client.post(
            reverse("training:gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(fehlermeldung, "Die Antwort konnte nicht erzeugt werden.")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.GESCHEITERT)
        self.assertIsNone(Gespraechsschritt.objects.get().aeusserung)
        self.client.post(reverse("training:gespraech_beenden"))
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.GESCHEITERT)

    def test_abbrechen_setzt_den_gewollten_status_ohne_diagnose(self) -> None:
        """Ein aktiver Abbruch bleibt vom technischen Scheitern unterscheidbar."""
        training: Training = self._sitzung_starten([])
        self.client.post(reverse("training:gespraech_beenden"))

        response: HttpResponse = self.client.post(reverse("training:abbrechen"))

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

        session = self.client.session
        session["training_sitzung_pk"] = sitzung.pk
        session.save()
        stale_diagnose: HttpResponse = self.client.post(
            reverse("training:debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertRedirects(
            stale_diagnose, reverse("training:detail", args=[training.pk])
        )
        sitzung.refresh_from_db()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

    def test_trainingssitzung_fuehrt_den_eingabemodus_mit(self) -> None:
        """Training folgt der Erhebung: Der Modus kommt aus dem Formular (Spec: #122)."""

        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}]
        )

        self.client.post(
            reverse("training:gespraech"),
            {"eingabe": "Wie rechnest du?", "eingabemodus": "transkribiert"},
        )

        self.assertEqual(
            Gespraechsschritt.objects.get().eingabemodus,
            Eingabemodus.TRANSKRIBIERT,
        )

    def test_trainingsdiagnose_fuehrt_den_eingabemodus_mit(self) -> None:
        """Training folgt der Erhebung auch an der Diagnose (Spec: #122)."""

        self._sitzung_starten([])
        self.client.post(reverse("training:gespraech_beenden"))

        self.client.post(
            reverse("training:debrief"),
            {"diagnose": "Bruchfehler", "eingabemodus": "gemischt"},
        )

        self.assertEqual(Diagnose.objects.get().eingabemodus, Eingabemodus.GEMISCHT)

    def test_schrittbudget_zeigt_debrief_bei_laufender_sitzung(self) -> None:
        """Auch ein ausgeschöpftes Schrittbudget schließt erst mit Diagnose ab."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}],
            budget_wert=1,
        )

        debrief: HttpResponse = self.client.post(
            reverse("training:gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(debrief, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(debrief, "Ihre nächste Frage")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.exists())

        fertig: HttpResponse = self.client.post(
            reverse("training:debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertEqual(fertig.status_code, 302)
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertEqual(Diagnose.objects.get().text, "Bruchfehler")

    def test_debrief_nach_vorzeitigem_gespraechsende_bleibt_laufend(self) -> None:
        """Der Debrief schließt die Sitzung erst mit ihrer Diagnose ab."""
        training: Training = self._sitzung_starten([])
        self.client.post(reverse("training:gespraech_beenden"))

        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

        response: HttpResponse = self.client.post(
            reverse("training:debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertEqual(Diagnose.objects.get(sitzung=sitzung).text, "Bruchfehler")

    def test_zeitbudget_zeigt_debrief_bei_laufender_sitzung(self) -> None:
        """Auch ein ausgeschöpftes Zeitbudget schließt erst mit Diagnose ab."""
        with time_machine.travel(datetime(2026, 7, 1, 10, 0, tzinfo=UTC), tick=False):
            self._sitzung_starten(
                [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}],
                budget_typ=Vignette.BudgetTyp.ZEIT,
                budget_wert=1,
            )
            self.client.get(reverse("training:gespraech"))

        with time_machine.travel(
            datetime(2026, 7, 1, 10, 0, 5, tzinfo=UTC), tick=False
        ):
            debrief: HttpResponse = self.client.post(
                reverse("training:gespraech"), {"eingabe": "Wie rechnest du?"}
            )

        self.assertContains(debrief, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(debrief, "Ihre nächste Frage")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.exists())

    def test_denkspur_bleibt_im_training_verborgen(self) -> None:
        """Die Denkspur ist laut ADR-0005 ausschließlich im Probelauf sichtbar."""
        self._sitzung_starten(
            [{"denkspur": "Interne Denkspur", "aeusserung": "Sichtbare Antwort."}]
        )
        response: HttpResponse = self.client.post(
            reverse("training:gespraech"), {"eingabe": "Wie rechnest du?"}
        )
        self.assertContains(response, "Sichtbare Antwort.")
        self.assertNotContains(response, "Interne Denkspur")

    def test_vergangene_sitzung_ansehen_ist_schreibgeschuetzt(self) -> None:
        """Eine abgeschlossene Sitzung kann schreibgeschützt eingesehen werden."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}]
        )
        self.client.post(reverse("training:gespraech"), {"eingabe": "Wie rechnest du?"})
        self.client.post(reverse("training:gespraech_beenden"))
        self.client.post(reverse("training:debrief"), {"diagnose": "Bruchfehler"})
        sitzung: Sitzung = Sitzung.objects.get()

        response: HttpResponse = self.client.get(
            reverse("training:sitzung_ansehen", args=[sitzung.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ich addiere alles.")
        self.assertContains(response, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(response, "Ihre nächste Frage")
        self.assertNotContains(response, "Spracheingabe starten")

    def test_vergangene_sitzung_anderer_konten_nicht_einsehbar(self) -> None:
        """Fremde Sitzungen bleiben durch 404 geschützt."""
        self._sitzung_starten([])
        sitzung: Sitzung = Sitzung.objects.get()

        andere_person: Konto = konto_mit_rollen("margaret")
        self.client.force_login(andere_person)

        response: HttpResponse = self.client.get(
            reverse("training:sitzung_ansehen", args=[sitzung.pk])
        )
        self.assertEqual(response.status_code, 404)

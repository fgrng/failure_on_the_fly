"""HTTP-Tests der persistierten Trainingssitzung."""

from datetime import UTC, datetime

import time_machine
from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from config.tests.formular import submit_knoepfe
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.models import (
    Diagnose,
    Eingabemodus,
    Gespraechsschritt,
    Sitzung,
    Vignettenposition,
)
from training.models import Training
from training.tests.aufbau import route_der_letzten_sitzung
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
            lernauftrag_text="Addiere zwei Brüche.",
            arbeitsheft_bildbeschreibung="Mia rechnet 1/2 + 1/3 = 2/5.",
            arbeitsheft_text="1/2 + 1/3 = 2/5",
            schuelerin_name="Mia",
            lehrperson_name="Weber",
            thema="Brüche",
            klassenstufe="5",
            budget_typ=budget_typ,
            budget_wert=budget_wert,
        )
        if kern_ueberholen:
            kern.bearbeiten().finalisieren()
        training.vignette_aufnehmen(vignette)
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
            self.start_response, f'action="{route_der_letzten_sitzung("abbrechen")}"'
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
        """Gespielt wird, worauf gepinnt wurde (ADR-0040) — auch überholt."""

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

        debrief: HttpResponse = self.client.post(
            route_der_letzten_sitzung("gespraech_beenden")
        )

        self.assertContains(debrief, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(debrief, "Spracheingabe starten")
        self.assertContains(
            debrief, "Spracheingabe nicht freigegeben. Sie nutzen die Tastatur."
        )

    def test_endgueltiger_fehlschlag_bleibt_gescheitert(self) -> None:
        """Ein answerless Schritt zeigt den Fehler und lässt keine Diagnose mehr zu."""
        self._sitzung_starten([{"fehler": "anbieterfehler"}] * 3)

        fehlermeldung: HttpResponse = self.client.post(
            route_der_letzten_sitzung("gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(fehlermeldung, "Die Antwort konnte nicht erzeugt werden.")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.GESCHEITERT)
        self.assertIsNone(Gespraechsschritt.objects.get().aeusserung)
        self.client.post(route_der_letzten_sitzung("gespraech_beenden"))
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.GESCHEITERT)

    def test_abbrechen_setzt_den_gewollten_status_ohne_diagnose(self) -> None:
        """Ein aktiver Abbruch bleibt vom technischen Scheitern unterscheidbar."""
        training: Training = self._sitzung_starten([])
        self.client.post(route_der_letzten_sitzung("gespraech_beenden"))

        response: HttpResponse = self.client.post(
            route_der_letzten_sitzung("abbrechen")
        )

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

        stale_diagnose: HttpResponse = self.client.post(
            route_der_letzten_sitzung("debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertRedirects(
            stale_diagnose, reverse("training:detail", args=[training.pk])
        )
        sitzung.refresh_from_db()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGEBROCHEN)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

    def test_abgebrochene_sitzung_bietet_beim_beenden_keinen_debrief(self) -> None:
        """Über ihre Adresse führt eine abgebrochene Sitzung nicht zur Diagnose."""
        training: Training = self._sitzung_starten([])
        self.client.post(route_der_letzten_sitzung("abbrechen"))

        response: HttpResponse = self.client.post(
            route_der_letzten_sitzung("gespraech_beenden")
        )

        self.assertRedirects(response, reverse("training:detail", args=[training.pk]))
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGEBROCHEN)

    def test_trainingssitzung_fuehrt_den_eingabemodus_mit(self) -> None:
        """Training folgt der Erhebung: Der Modus kommt aus dem Formular (Spec: #122)."""

        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}]
        )

        self.client.post(
            route_der_letzten_sitzung("gespraech"),
            {"eingabe": "Wie rechnest du?", "eingabemodus": "transkribiert"},
        )

        self.assertEqual(
            Gespraechsschritt.objects.get().eingabemodus,
            Eingabemodus.TRANSKRIBIERT,
        )

    def test_trainingsdiagnose_fuehrt_den_eingabemodus_mit(self) -> None:
        """Training folgt der Erhebung auch an der Diagnose (Spec: #122)."""

        self._sitzung_starten([])
        self.client.post(route_der_letzten_sitzung("gespraech_beenden"))

        self.client.post(
            route_der_letzten_sitzung("debrief"),
            {"diagnose": "Bruchfehler", "eingabemodus": "gemischt"},
        )

        self.assertEqual(Diagnose.objects.get().eingabemodus, Eingabemodus.GEMISCHT)

    def test_trainingssitzung_schreibt_keine_vignettenposition(self) -> None:
        """Die Position gehört der Erhebung; Training hält sie im Training (#442)."""

        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}]
        )
        self.client.post(
            route_der_letzten_sitzung("gespraech"), {"eingabe": "Wie rechnest du?"}
        )
        self.client.post(route_der_letzten_sitzung("gespraech_beenden"))
        self.client.post(
            route_der_letzten_sitzung("debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertFalse(Vignettenposition.objects.exists())

    def test_schrittbudget_zeigt_debrief_bei_laufender_sitzung(self) -> None:
        """Auch ein ausgeschöpftes Schrittbudget schließt erst mit Diagnose ab."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}],
            budget_wert=1,
        )

        debrief: HttpResponse = self.client.post(
            route_der_letzten_sitzung("gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(debrief, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(debrief, "Ihre nächste Frage")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.exists())

        fertig: HttpResponse = self.client.post(
            route_der_letzten_sitzung("debrief"), {"diagnose": "Bruchfehler"}
        )

        self.assertEqual(fertig.status_code, 302)
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGESCHLOSSEN)
        self.assertEqual(Diagnose.objects.get().text, "Bruchfehler")

    def test_debrief_nach_vorzeitigem_gespraechsende_bleibt_laufend(self) -> None:
        """Der Debrief schließt die Sitzung erst mit ihrer Diagnose ab."""
        training: Training = self._sitzung_starten([])
        self.client.post(route_der_letzten_sitzung("gespraech_beenden"))

        sitzung: Sitzung = Sitzung.objects.get()
        self.assertEqual(sitzung.status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.filter(sitzung=sitzung).exists())

        response: HttpResponse = self.client.post(
            route_der_letzten_sitzung("debrief"), {"diagnose": "Bruchfehler"}
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
            self.client.get(route_der_letzten_sitzung("gespraech"))

        with time_machine.travel(
            datetime(2026, 7, 1, 10, 0, 5, tzinfo=UTC), tick=False
        ):
            debrief: HttpResponse = self.client.post(
                route_der_letzten_sitzung("gespraech"), {"eingabe": "Wie rechnest du?"}
            )

        self.assertContains(debrief, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(debrief, "Ihre nächste Frage")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)
        self.assertFalse(Diagnose.objects.exists())

    def test_denkspur_bleibt_im_training_verborgen(self) -> None:
        """Die Denkspur ist laut ADR-0064 ausschließlich im Probelauf sichtbar."""
        self._sitzung_starten(
            [{"denkspur": "Interne Denkspur", "aeusserung": "Sichtbare Antwort."}]
        )
        response: HttpResponse = self.client.post(
            route_der_letzten_sitzung("gespraech"), {"eingabe": "Wie rechnest du?"}
        )
        self.assertContains(response, "Sichtbare Antwort.")
        self.assertNotContains(response, "Interne Denkspur")

    def test_vergangene_sitzung_ansehen_ist_schreibgeschuetzt(self) -> None:
        """Eine abgeschlossene Sitzung kann schreibgeschützt eingesehen werden."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}]
        )
        self.client.post(
            route_der_letzten_sitzung("gespraech"), {"eingabe": "Wie rechnest du?"}
        )
        self.client.post(route_der_letzten_sitzung("gespraech_beenden"))
        self.client.post(
            route_der_letzten_sitzung("debrief"), {"diagnose": "Bruchfehler"}
        )
        sitzung: Sitzung = Sitzung.objects.get()

        response: HttpResponse = self.client.get(
            reverse("training:sitzung_ansehen", args=[sitzung.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ich addiere alles.")
        self.assertContains(response, "Was ist Ihnen aufgefallen?")
        self.assertNotContains(response, "Ihre nächste Frage")
        self.assertNotContains(response, "Spracheingabe starten")

    def _abgeschlossene_sitzung_ansehen(self) -> str:
        """Schließt eine Sitzung mit Diagnose ab und liefert ihren Seiteninhalt."""
        self._sitzung_starten(
            [{"denkspur": "Interne Denkspur", "aeusserung": "Ich addiere alles."}]
        )
        self.client.post(
            route_der_letzten_sitzung("gespraech"), {"eingabe": "Wie rechnest du?"}
        )
        self.client.post(route_der_letzten_sitzung("gespraech_beenden"))
        self.client.post(
            route_der_letzten_sitzung("debrief"),
            {"diagnose": "Mia addiert Zähler und Nenner."},
        )
        inhalt: str = self.client.get(
            reverse("training:sitzung_ansehen", args=[Sitzung.objects.get().pk])
        ).content.decode()
        # Ohne die Navigation, deren Abmelden ein Formular ist.
        return inhalt[inhalt.index('<article class="sitzung-seite"') :]

    def test_vergangene_sitzung_zeigt_die_diagnose_als_text(self) -> None:
        """Die lesende Ansicht nennt die abgegebene Diagnose."""
        self.assertRegex(
            self._abgeschlossene_sitzung_ansehen(),
            r"<p[^>]*>Mia addiert Zähler und Nenner.</p>",
        )

    def test_vergangene_sitzung_ohne_diagnose(self) -> None:
        """Fehlt die Diagnose, sagt die lesende Ansicht das ausdrücklich."""
        self._sitzung_starten([])
        sitzung: Sitzung = Sitzung.objects.get()
        sitzung.status = Sitzung.Status.ABGESCHLOSSEN
        sitzung.save()

        response: HttpResponse = self.client.get(
            reverse("training:sitzung_ansehen", args=[sitzung.pk])
        )

        self.assertContains(response, "Keine Diagnose abgegeben.")

    def test_vergangene_sitzung_zeigt_kein_diagnoseformular(self) -> None:
        """Die lesende Ansicht hat keine Formulare."""
        seite: str = self._abgeschlossene_sitzung_ansehen()

        for element in ("<form", "<textarea", "<button"):
            with self.subTest(element=element):
                self.assertNotIn(element, seite)

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

    def test_fremde_sitzungsadresse_ergibt_404(self) -> None:
        """Eine geratene Sitzungs-pk führt nicht in eine fremde Sitzung."""
        self._sitzung_starten([])
        sitzung: Sitzung = Sitzung.objects.get()
        self.client.force_login(konto_mit_rollen("margaret"))

        for route, methode in (
            ("training:gespraech", self.client.get),
            ("training:gespraech_beenden", self.client.post),
            ("training:abbrechen", self.client.post),
            ("training:debrief", self.client.post),
            ("training:transkription", self.client.post),
        ):
            with self.subTest(route=route):
                response: HttpResponse = methode(reverse(route, args=[sitzung.pk]))
                self.assertEqual(response.status_code, 404)
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)

    def test_laufende_sitzung_laesst_sich_aus_frischem_client_fortsetzen(
        self,
    ) -> None:
        """Ein anderer Browser mit demselben Konto setzt das Gespräch fort."""
        self._sitzung_starten(
            [{"denkspur": "Bruchfehler", "aeusserung": "Ich addiere alles."}]
        )
        sitzung: Sitzung = Sitzung.objects.get()
        gespraech_url: str = reverse("training:gespraech", args=[sitzung.pk])
        self.client.post(gespraech_url, {"eingabe": "Wie rechnest du?"})
        anderer_browser: Client = Client()
        anderer_browser.force_login(Konto.objects.get(username="grace"))

        fortgesetzt: HttpResponse = anderer_browser.get(gespraech_url)

        self.assertContains(fortgesetzt, "Wie rechnest du?")
        self.assertContains(fortgesetzt, "Ich addiere alles.")
        self.assertContains(fortgesetzt, "Ihre nächste Frage")
        weiter: HttpResponse = anderer_browser.post(
            gespraech_url, {"eingabe": "Und dann?"}
        )
        self.assertContains(weiter, "Wie rechnest du?")
        self.assertContains(weiter, "Und dann?")
        self.assertEqual(Gespraechsschritt.objects.count(), 2)

    def test_trainingsseite_bietet_laufende_sitzung_zum_fortsetzen_an(self) -> None:
        """Die laufende Sitzung trägt den Link auf ihre Gesprächsroute."""
        training: Training = self._sitzung_starten([])
        sitzung: Sitzung = Sitzung.objects.get()

        response: HttpResponse = self.client.get(
            reverse("training:detail", args=[training.pk])
        )

        self.assertContains(
            response,
            f'href="{reverse("training:gespraech", args=[sitzung.pk])}">Fortsetzen',
        )

    def test_trainingsseite_bietet_abgebrochene_sitzung_nicht_zum_fortsetzen_an(
        self,
    ) -> None:
        """Eine beendete Sitzung lässt sich von der Trainingsseite nicht fortsetzen."""
        training: Training = self._sitzung_starten([])
        self.client.post(route_der_letzten_sitzung("abbrechen"))

        response: HttpResponse = self.client.get(
            reverse("training:detail", args=[training.pk])
        )

        self.assertNotContains(response, "Fortsetzen")

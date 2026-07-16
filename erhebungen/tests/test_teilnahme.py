"""HTTP-Tests für den pseudonymen Erhebungszugang."""

from datetime import timedelta
from unittest.mock import patch

from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsvignette,
    Stichprobe,
    Vignettenposition,
)
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Gespraechsschritt, Sitzung
from vignetten.models import Vignette, Vignettenhistorie


class ErhebungsteilnahmeTests(TestCase):
    """Teilnahmen entstehen ausschließlich über den Teilnahme-Link."""

    def setUp(self) -> None:
        """Legt eine finale Erhebung mit laufender Stichprobe an."""

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"denkspur": "Geheime Regel.", "aeusserung": "Ich addiere."}
                ]
            },
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche",
            eigentuemerin=Konto.objects.create_user(username="ada"),
            einwilligungstext="Ich willige in die Teilnahme ein.",
            instruktionstext="Fragen Sie gezielt nach dem Rechenweg.",
        )
        self.erhebung.finalisieren()
        self.stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now(),
            ende=timezone.now() + timedelta(days=1),
        )
        self.url: str = reverse(
            "erhebungen:teilnehmen", args=[self.stichprobe.teilnahme_link]
        )

    def _vignette_anlegen(
        self,
        *,
        budget_typ: str = Vignette.BudgetTyp.SCHRITTE,
        budget_wert: int = 1,
    ) -> Vignette:
        """Bindet eine spielbare finale Vignette an die Erhebung."""

        kern: Simulationskern = Simulationskern.objects.anlegen(
            rahmenhandlung_gespraechseinleitung="$schuelerin_name rechnet vor."
        )
        kern.finalisieren()
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Brüche vergleichen"
        )
        historie.eigentuemerinnen.add(self.erhebung.eigentuemerin)
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag="Addiere Brüche.",
            arbeitsheft_beschreibung="Eine falsche Bruchrechnung.",
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
        Erhebungsvignette.objects.create(
            erhebung=self.erhebung,
            vignette=vignette,
            position=1,
        )
        return vignette

    def test_teilnahme_link_legt_bindung_an_setzt_token_und_zeigt_einwilligung(
        self,
    ) -> None:
        """Ohne Einwilligung führt der erste Link-Aufruf zum Einwilligungstor."""

        erste_antwort: HttpResponse = self.client.get(self.url)
        erste_bindung: Erhebungsbindung = Erhebungsbindung.objects.get()

        self.assertRedirects(
            erste_antwort,
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
        )
        self.assertEqual(Erhebungsbindung.objects.count(), 1)
        self.assertEqual(
            self.client.session["erhebung_teilnahme_tokens"][
                str(self.stichprobe.teilnahme_link)
            ],
            erste_bindung.token,
        )

    def test_einwilligung_oeffnet_instruktion_und_bleibt_an_der_teilnahme(
        self,
    ) -> None:
        """Dieselbe pseudonyme Teilnahme setzt nach Zustimmung bei der Instruktion fort."""

        self.client.get(self.url)
        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            {"einwilligung": "ja"},
        )

        self.assertRedirects(
            antwort,
            reverse("erhebungen:instruktion", args=[self.stichprobe.teilnahme_link]),
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.get()
        self.assertTrue(bindung.teilnahme.einwilligung_erteilt)
        fortsetzung: HttpResponse = self.client.get(self.url)
        self.assertRedirects(
            fortsetzung,
            reverse("erhebungen:instruktion", args=[self.stichprobe.teilnahme_link]),
        )
        self.assertEqual(Erhebungsbindung.objects.count(), 1)
        self.assertEqual(Erhebungsbindung.objects.get().teilnahme_id, bindung.teilnahme_id)

    def test_einwilligung_und_instruktion_zeigen_die_erhebungstexte(self) -> None:
        """Die Teilnahme informiert vor dem Spiel über Zustimmung und Begrenzung."""

        self.client.get(self.url)

        einwilligung: HttpResponse = self.client.get(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link])
        )
        self.client.post(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            {"einwilligung": "ja"},
        )
        instruktion: HttpResponse = self.client.get(
            reverse("erhebungen:instruktion", args=[self.stichprobe.teilnahme_link])
        )

        self.assertContains(einwilligung, "Ich willige in die Teilnahme ein.")
        self.assertContains(instruktion, "Fragen Sie gezielt nach dem Rechenweg.")
        self.assertContains(instruktion, "Das Diagnosegespräch ist begrenzt.")

    def test_ausserhalb_des_laufenden_zeitraums_ist_einstieg_und_fortsetzung_gesperrt(
        self,
    ) -> None:
        """Die Stichprobe lässt vor und nach ihrem Fenster keinen Ablauf zu."""

        self.stichprobe.beginn = timezone.now() + timedelta(days=1)
        self.stichprobe.ende = timezone.now() + timedelta(days=2)
        self.stichprobe.save(update_fields=["beginn", "ende"])

        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertFalse(Erhebungsbindung.objects.exists())

        self.stichprobe.beginn = timezone.now() - timedelta(days=2)
        self.stichprobe.ende = timezone.now() - timedelta(days=1)
        self.stichprobe.save(update_fields=["beginn", "ende"])

        for url in (
            self.url,
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            reverse("erhebungen:instruktion", args=[self.stichprobe.teilnahme_link]),
        ):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_neuer_browser_erzeugt_eine_neue_leere_teilnahme(self) -> None:
        """Ohne gespeichertes Token wird keine bestehende Teilnahme wiederverwendet."""

        self.client.get(self.url)
        erster_browser: Erhebungsbindung = Erhebungsbindung.objects.get()
        anderer_browser: Client = Client()

        antwort: HttpResponse = anderer_browser.get(self.url)

        self.assertRedirects(
            antwort,
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
        )
        self.assertEqual(Erhebungsbindung.objects.count(), 2)
        zweite_bindung: Erhebungsbindung = Erhebungsbindung.objects.exclude(
            pk=erster_browser.pk
        ).get()
        self.assertNotEqual(zweite_bindung.teilnahme_id, erster_browser.teilnahme_id)
        self.assertFalse(zweite_bindung.teilnahme.einwilligung_erteilt)

    def test_token_spielt_eine_vignette_bis_zum_abschluss(self) -> None:
        """Die pseudonyme Teilnahme bewahrt die Datenspur ohne Denkspuransicht."""

        self._vignette_anlegen()

        self.client.get(self.url)
        self.client.post(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            {"einwilligung": "ja"},
        )
        start_antwort: HttpResponse = self.client.post(
            reverse("erhebungen:spielen", args=[self.stichprobe.teilnahme_link])
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.get()
        gespraech_url: str = reverse(
            "erhebungen:gespraech", args=[bindung.token]
        )
        self.assertRedirects(start_antwort, gespraech_url)
        self.assertEqual(Vignettenposition.objects.get().position, 1)
        fortsetzung: HttpResponse = self.client.post(
            reverse("erhebungen:spielen", args=[self.stichprobe.teilnahme_link])
        )
        self.assertRedirects(fortsetzung, gespraech_url)
        self.assertEqual(Sitzung.objects.count(), 1)

        debrief: HttpResponse = self.client.post(
            gespraech_url, {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(debrief, "Debrief")
        self.assertNotContains(debrief, "Geheime Regel.")
        self.assertEqual(Gespraechsschritt.objects.get().denkspur, "Geheime Regel.")
        sitzung: Sitzung = Sitzung.objects.get()
        abschluss_antwort: HttpResponse = self.client.post(
            reverse("erhebungen:debrief", args=[bindung.token]),
            {"diagnose": "Bruchfehler"},
        )
        self.assertRedirects(
            abschluss_antwort,
            reverse("erhebungen:abschluss", args=[self.stichprobe.teilnahme_link]),
        )
        sitzung.refresh_from_db()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGESCHLOSSEN)

    def test_zeitbudget_ist_von_training_und_anderen_sitzungen_getrennt(self) -> None:
        """Fremder Zeitverbrauch beendet die Erhebungssitzung nicht."""

        self._vignette_anlegen(
            budget_typ=Vignette.BudgetTyp.ZEIT,
            budget_wert=5,
        )
        self.client.get(self.url)
        self.client.post(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            {"einwilligung": "ja"},
        )
        self.client.post(
            reverse("erhebungen:spielen", args=[self.stichprobe.teilnahme_link])
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.get()
        gespraech_url: str = reverse("erhebungen:gespraech", args=[bindung.token])
        session = self.client.session
        session["training_verbrauchte_zeit"] = 999.0
        session.save()

        with patch("sitzungen.views.monotonic", side_effect=[10.0, 11.0, 11.0]):
            self.client.get(gespraech_url)
            antwort: HttpResponse = self.client.post(
                gespraech_url, {"eingabe": "Wie rechnest du?"}
            )

        self.assertNotContains(antwort, "Debrief")
        self.assertContains(antwort, "Ich addiere.")

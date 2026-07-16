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
from sitzungen.models import Fehlversuch, Gespraechsschritt, Sitzung
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
        self.kern: Simulationskern | None = None

    def _vignette_anlegen(
        self,
        *,
        budget_typ: str = Vignette.BudgetTyp.SCHRITTE,
        budget_wert: int = 1,
        position: int = 1,
    ) -> Vignette:
        """Bindet eine spielbare finale Vignette an die Erhebung."""

        if self.kern is None:
            self.kern = Simulationskern.objects.anlegen(
                rahmenhandlung_gespraechseinleitung="$schuelerin_name rechnet vor."
            )
            self.kern.finalisieren()
        kern: Simulationskern = self.kern
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
            position=position,
        )
        return vignette

    def _laufende_sitzung_starten(self) -> Erhebungsbindung:
        """Startet die Teilnahme bis zur laufenden Sitzung und gibt ihre Bindung zurück."""

        self.client.get(self.url)
        self.client.post(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            {"einwilligung": "ja"},
        )
        self.client.post(
            reverse("erhebungen:spielen", args=[self.stichprobe.teilnahme_link])
        )
        return Erhebungsbindung.objects.get()

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

    def test_archivierte_stichprobe_ist_fuer_teilnahmen_gesperrt(self) -> None:
        """Eine archivierte Stichprobe sammelt auch im Zeitfenster keine Daten."""

        self.stichprobe.archivieren()

        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertFalse(Erhebungsbindung.objects.exists())

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
            {"diagnose": "Bruchfehler", "sitzung_pk": sitzung.pk},
        )
        self.assertRedirects(
            abschluss_antwort,
            reverse("erhebungen:abschluss", args=[self.stichprobe.teilnahme_link]),
        )
        sitzung.refresh_from_db()
        self.assertEqual(sitzung.status, Sitzung.Status.ABGESCHLOSSEN)

    def test_debrief_setzt_direkt_mit_der_naechsten_vignette_fort(self) -> None:
        """Der Ablauf startet nach einer Diagnose sofort die nächste Ziehung."""

        erste: Vignette = self._vignette_anlegen()
        zweite: Vignette = self._vignette_anlegen(position=2)
        self.client.get(self.url)
        self.client.post(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            {"einwilligung": "ja"},
        )
        self.client.post(
            reverse("erhebungen:spielen", args=[self.stichprobe.teilnahme_link])
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.get()

        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:debrief", args=[bindung.token]),
            {"diagnose": "Bruchfehler", "sitzung_pk": Sitzung.objects.get().pk},
        )

        self.assertRedirects(
            antwort, reverse("erhebungen:gespraech", args=[bindung.token])
        )
        self.assertEqual(
            list(
                Vignettenposition.objects.values_list("vignette_id", "position")
            ),
            [(erste.pk, 1), (zweite.pk, 2)],
        )

    def test_staler_debrief_beendet_die_folgesitzung_nicht(self) -> None:
        """Ein zweiter Debrief-POST bleibt an seiner abgeschlossenen Sitzung gebunden."""

        self._vignette_anlegen()
        self._vignette_anlegen(position=2)
        self.client.get(self.url)
        self.client.post(
            reverse("erhebungen:einwilligung", args=[self.stichprobe.teilnahme_link]),
            {"einwilligung": "ja"},
        )
        self.client.post(
            reverse("erhebungen:spielen", args=[self.stichprobe.teilnahme_link])
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.get()
        erste_sitzung: Sitzung = Sitzung.objects.get()
        debrief_url: str = reverse("erhebungen:debrief", args=[bindung.token])
        daten: dict[str, str | int] = {
            "diagnose": "Bruchfehler",
            "sitzung_pk": erste_sitzung.pk,
        }

        self.client.post(debrief_url, daten)
        antwort: HttpResponse = self.client.post(debrief_url, daten)

        self.assertEqual(antwort.status_code, 400)
        self.assertEqual(
            Sitzung.objects.get(pk=erste_sitzung.pk).status,
            Sitzung.Status.ABGESCHLOSSEN,
        )
        self.assertEqual(
            Sitzung.objects.exclude(pk=erste_sitzung.pk).get().status,
            Sitzung.Status.LAUFEND,
        )

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

    def test_aktiver_abbruch_setzt_die_sitzung_auf_abgebrochen(self) -> None:
        """Die Teilnahme kann eine laufende Sitzung ohne Diagnose abbrechen."""

        self._vignette_anlegen()
        bindung: Erhebungsbindung = self._laufende_sitzung_starten()

        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:abbrechen", args=[bindung.token])
        )

        self.assertRedirects(
            antwort,
            reverse("erhebungen:instruktion", args=[self.stichprobe.teilnahme_link]),
        )
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.ABGEBROCHEN)

    def test_endgueltiger_fehlschlag_bewahrt_gespraechsschritt_ohne_antwort(
        self,
    ) -> None:
        """Ein Modellfehler beendet die Erhebungssitzung lesbar und persistent."""

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={"skript": [{"fehler": "anbieterfehler"}] * 3},
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.erhebung = Erhebung.objects.create(
            name="Fehlschlag",
            eigentuemerin=self.erhebung.eigentuemerin,
        )
        self.erhebung.finalisieren()
        self.stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now(),
            ende=timezone.now() + timedelta(days=1),
        )
        self.url = reverse("erhebungen:teilnehmen", args=[self.stichprobe.teilnahme_link])
        self._vignette_anlegen()
        bindung: Erhebungsbindung = self._laufende_sitzung_starten()

        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:gespraech", args=[bindung.token]),
            {"eingabe": "Wie rechnest du?"},
        )

        self.assertContains(antwort, "Die Antwort konnte nicht erzeugt werden.")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.GESCHEITERT)
        schritt: Gespraechsschritt = Gespraechsschritt.objects.get()
        self.assertIsNone(schritt.aeusserung)
        self.assertEqual(Fehlversuch.objects.filter(gespraechsschritt=schritt).count(), 3)

    def test_vorzeitiges_gespraechsende_zeigt_den_debrief(self) -> None:
        """Ein freiwilliges Ende führt bei laufender Sitzung in den Debrief."""

        self._vignette_anlegen()
        bindung: Erhebungsbindung = self._laufende_sitzung_starten()

        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:gespraech_beenden", args=[bindung.token])
        )

        self.assertContains(antwort, "Debrief")
        self.assertEqual(Sitzung.objects.get().status, Sitzung.Status.LAUFEND)

    def test_nach_fensterende_verfaellt_die_laufende_teilnahme(self) -> None:
        """Ein abgelaufenes Fenster sperrt die laufende Sitzung ohne Kulanz."""

        self._vignette_anlegen()
        bindung: Erhebungsbindung = self._laufende_sitzung_starten()
        self.stichprobe.ende = timezone.now() - timedelta(seconds=1)
        self.stichprobe.save(update_fields=["ende"])

        self.assertTrue(bindung.verfallen)
        self.assertEqual(
            self.client.get(
                reverse("erhebungen:gespraech", args=[bindung.token])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("erhebungen:spielen", args=[self.stichprobe.teilnahme_link])
            ).status_code,
            403,
        )

    def test_nach_fensterende_verfaellt_teilnahme_mit_offener_vignette(self) -> None:
        """Auch nach einer fertigen Sitzung bleibt eine offene Ziehung unfertig."""

        self._vignette_anlegen()
        self._vignette_anlegen(position=2)
        bindung: Erhebungsbindung = self._laufende_sitzung_starten()
        Sitzung.objects.update(status=Sitzung.Status.ABGESCHLOSSEN)
        self.stichprobe.ende = timezone.now() - timedelta(seconds=1)
        self.stichprobe.save(update_fields=["ende"])

        self.assertTrue(bindung.verfallen)

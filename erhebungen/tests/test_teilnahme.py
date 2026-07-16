"""HTTP-Tests für den pseudonymen Erhebungszugang."""

from datetime import timedelta

from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from erhebungen.models import Erhebung, Erhebungsbindung, Stichprobe
from konten.models import Konto
from simulation.models import ModellKonfiguration


class ErhebungsteilnahmeTests(TestCase):
    """Teilnahmen entstehen ausschließlich über den Teilnahme-Link."""

    def setUp(self) -> None:
        """Legt eine finale Erhebung mit laufender Stichprobe an."""

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake"
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

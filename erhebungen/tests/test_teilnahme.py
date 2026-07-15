"""HTTP-Tests für den pseudonymen Erhebungszugang."""

from datetime import timedelta

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from erhebungen.models import Erhebung, Erhebungsbindung, Stichprobe
from konten.models import Konto


class ErhebungsteilnahmeTests(TestCase):
    """Teilnahmen entstehen ausschließlich über den Teilnahme-Link."""

    def test_teilnahme_link_legt_bindung_an_und_setzt_token_in_der_session(
        self,
    ) -> None:
        """Ein erneuter Link-Aufruf im selben Browser setzt dieselbe Teilnahme fort."""

        erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
        )
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now(),
            ende=timezone.now() + timedelta(days=1),
        )
        url: str = reverse("erhebungen:teilnehmen", args=[stichprobe.teilnahme_link])

        erste_antwort: HttpResponse = self.client.get(url)
        erste_bindung: Erhebungsbindung = Erhebungsbindung.objects.get()
        zweite_antwort: HttpResponse = self.client.get(url)

        self.assertEqual(erste_antwort.status_code, 204)
        self.assertEqual(zweite_antwort.status_code, 204)
        self.assertEqual(Erhebungsbindung.objects.count(), 1)
        self.assertEqual(
            self.client.session["erhebung_teilnahme_tokens"][
                str(stichprobe.teilnahme_link)
            ],
            erste_bindung.token,
        )

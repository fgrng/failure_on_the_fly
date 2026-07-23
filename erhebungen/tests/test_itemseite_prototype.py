"""Sichtprüfung für den datenbankfreien Itemseiten-Prototyp."""

from django.test import SimpleTestCase
from django.urls import reverse


class ItemseitePrototypeTests(SimpleTestCase):
    """Der Prototyp zeigt alle Vergleichsaspekte ohne Teilnahme-Daten."""

    def test_jede_variante_zeigt_itemtypen_kontexte_und_zustaende(self) -> None:
        """Die Sichtung bleibt ohne Datenbank und deckt die Designfragen ab."""

        url = reverse("erhebungen:itemseite_prototype")
        for variante in ("a", "b", "c", "vergleich"):
            with self.subTest(variante=variante):
                response = self.client.get(url, {"variant": variante})

                self.assertContains(response, "Freitext")
                self.assertContains(response, "Likert")
                self.assertContains(response, "Nach der Vignettensitzung")
                self.assertContains(response, "Am Ende der Erhebung")
                self.assertContains(response, "Noch nicht beantwortet")
                self.assertContains(response, "Gerade beantwortet")
                self.assertContains(response, "Gespeichert")
                self.assertContains(response, "Antwort zurückgenommen")

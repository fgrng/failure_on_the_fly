"""Sichtprüfung für den datenbankfreien Itemseiten-Prototyp."""

from django.test import SimpleTestCase
from django.urls import reverse

_VARIANTEN: tuple[str, ...] = ("a", "b", "c", "vergleich")


class ItemseitePrototypeTests(SimpleTestCase):
    """Der Prototyp zeigt alle Vergleichsaspekte ohne Teilnahme-Daten."""

    def test_jede_variante_zeigt_beide_itemtypen(self) -> None:
        """Jede Ansicht enthält Freitext- und Likert-Items."""

        for variante in _VARIANTEN:
            with self.subTest(variante=variante):
                response = self.client.get(
                    reverse("erhebungen:itemseite_prototype"), {"variant": variante}
                )

                self.assertContains(response, "Freitext")
                self.assertContains(response, "Likert")

    def test_jede_variante_zeigt_beide_kontexte(self) -> None:
        """Jede Ansicht zeigt die Items an beiden Andockpunkten."""

        for variante in _VARIANTEN:
            with self.subTest(variante=variante):
                response = self.client.get(
                    reverse("erhebungen:itemseite_prototype"), {"variant": variante}
                )

                self.assertContains(response, "Nach der Vignettensitzung")
                self.assertContains(response, "Am Ende der Erhebung")

    def test_jede_variante_zeigt_offene_und_gerade_beantwortete_items(self) -> None:
        """Jede Ansicht zeigt optionale und gerade beantwortete Items."""

        for variante in _VARIANTEN:
            with self.subTest(variante=variante):
                response = self.client.get(
                    reverse("erhebungen:itemseite_prototype"), {"variant": variante}
                )

                self.assertContains(response, "Noch nicht beantwortet")
                self.assertContains(response, "Gerade beantwortet")

    def test_jede_variante_zeigt_gespeicherte_und_zurueckgenommene_items(
        self,
    ) -> None:
        """Jede Ansicht zeigt gespeicherte und zurückgenommene Items."""

        url = reverse("erhebungen:itemseite_prototype")
        for variante in _VARIANTEN:
            with self.subTest(variante=variante):
                response = self.client.get(url, {"variant": variante})

                self.assertContains(response, "Gespeichert")
                self.assertContains(response, "Antwort zurückgenommen")

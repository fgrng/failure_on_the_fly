"""Tests für das Anlegen der Entwicklungsdaten."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from vignetten.models import Vignette


@override_settings(DEBUG=True)
class EntwicklungsdatenTests(TestCase):
    """Das Command befüllt eine Entwicklungsinstanz mit Testdaten."""

    def test_legt_vignetten_mit_allen_neuen_feldern_an(self) -> None:
        """Der Seed belegt alle neuen Aufgabenkontext-Felder mit plausiblen Werten."""

        ausgabe: StringIO = StringIO()
        call_command("entwicklungsdaten_anlegen", stdout=ausgabe)

        vignetten = list(
            Vignette.objects.filter(zustand=Vignette.Zustand.FINAL)
        )
        self.assertGreaterEqual(len(vignetten), 2)

        # Mindestens eine Beispielvignette trägt einen Marker mitten im Text
        marker_mitten_im_text = any(
            vignette.lernauftrag_text_vor_bild and vignette.lernauftrag_text_nach_bild
            or vignette.arbeitsheft_text_vor_bild and vignette.arbeitsheft_text_nach_bild
            for vignette in vignetten
        )
        self.assertTrue(
            marker_mitten_im_text,
            "Mindestens eine Vignette muss einen [bild]-Marker mitten im Text tragen.",
        )

        # Mindestens eine Beispielvignette trägt ein Arbeitsheft, das nur aus einem Bild besteht
        reines_bild_arbeitsheft = any(
            not vignette.arbeitsheft_text and bool(vignette.arbeitsheft_bild)
            for vignette in vignetten
        )
        self.assertTrue(
            reines_bild_arbeitsheft,
            "Mindestens eine Vignette muss ein reines Bild-Arbeitsheft tragen.",
        )

        # Alle neuen Felder sind über die Vignetten hinweg mit Werten belegt
        self.assertTrue(any(bool(v.lernauftrag_bild) for v in vignetten))
        self.assertTrue(any(bool(v.lernauftrag_bildbeschreibung) for v in vignetten))
        self.assertTrue(any(bool(v.lernauftrag_simulationshinweise) for v in vignetten))
        self.assertTrue(any(bool(v.arbeitsheft_bild) for v in vignetten))
        self.assertTrue(any(bool(v.arbeitsheft_bildbeschreibung) for v in vignetten))
        self.assertTrue(any(bool(v.arbeitsheft_simulationshinweise) for v in vignetten))

    def test_zweiter_lauf_ist_idempotent(self) -> None:
        """Ein wiederholter Aufruf wirft keine Fehler und dupliziert nichts."""

        ausgabe: StringIO = StringIO()
        call_command("entwicklungsdaten_anlegen", stdout=ausgabe)
        anzahl_vorher: int = Vignette.objects.count()

        call_command("entwicklungsdaten_anlegen", stdout=ausgabe)
        self.assertEqual(Vignette.objects.count(), anzahl_vorher)

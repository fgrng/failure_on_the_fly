"""Tests für das Anlegen der Entwicklungsdaten."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from konten.models import Konto
from simulation.models import ModellKonfiguration, Verwendung
from texte.markdown import szenentext
from training.models import Training
from vignetten.models import Vignette


@override_settings(DEBUG=True)
class EntwicklungsdatenTests(TestCase):
    """Das Command befüllt eine Entwicklungsinstanz mit Testdaten."""

    def test_legt_vignetten_mit_allen_neuen_feldern_an(self) -> None:
        """Der Seed belegt alle neuen Aufgabenkontext-Felder mit plausiblen Werten."""

        ausgabe: StringIO = StringIO()
        call_command("entwicklungsdaten_anlegen", stdout=ausgabe)

        vignetten: list[Vignette] = list(
            Vignette.objects.filter(zustand=Vignette.Zustand.FINAL)
        )
        self.assertGreaterEqual(len(vignetten), 2)

        # Mindestens eine Beispielvignette trägt einen Marker mitten im Text
        marker_mitten_im_text: bool = any(
            teil.text_vor_bild and teil.text_nach_bild
            for vignette in vignetten
            for teil in (vignette.lernauftrag, vignette.arbeitsheft)
        )
        self.assertTrue(
            marker_mitten_im_text,
            "Mindestens eine Vignette muss einen [bild]-Marker mitten im Text tragen.",
        )

        # Mindestens eine Beispielvignette trägt ein Arbeitsheft, das nur aus einem Bild besteht
        reines_bild_arbeitsheft: bool = any(
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

    def test_aufgabenkontext_erscheint_als_szenentext_unverfaelscht(self) -> None:
        """Keine Schülernotation im Seed wird ungewollt zu Markdown-Auszeichnung."""

        call_command("entwicklungsdaten_anlegen", stdout=StringIO())

        for vignette in Vignette.objects.filter(zustand=Vignette.Zustand.FINAL):
            for teil in (vignette.lernauftrag, vignette.arbeitsheft):
                for text in (teil.text_vor_bild, teil.text_nach_bild):
                    html: str = szenentext(text)
                    for auszeichnung in ("<strong>", "<em>", "<ul>", "<ol>", "<h"):
                        self.assertNotIn(auszeichnung, html, text)

    def test_belegt_jede_verwendung_mit_der_fake_konfiguration(self) -> None:
        """Eine frische Entwicklungsinstanz ist sofort spielbar, auch für Evals."""

        call_command("entwicklungsdaten_anlegen", stdout=StringIO())
        call_command("entwicklungsdaten_anlegen", stdout=StringIO())

        fake: ModellKonfiguration = ModellKonfiguration.objects.get()
        self.assertEqual(fake.bezeichnung, "Offline (fake)")
        self.assertEqual(
            ModellKonfiguration.objects.aktive_je_verwendung(),
            {verwendung.value: fake.pk for verwendung in Verwendung},
        )

    def test_zweiter_lauf_ist_idempotent(self) -> None:
        """Ein wiederholter Aufruf wirft keine Fehler und dupliziert nichts."""

        ausgabe: StringIO = StringIO()
        call_command("entwicklungsdaten_anlegen", stdout=ausgabe)
        anzahl_vorher: int = Vignette.objects.count()

        call_command("entwicklungsdaten_anlegen", stdout=ausgabe)
        self.assertEqual(Vignette.objects.count(), anzahl_vorher)

    def test_trainings_werden_fuer_die_ausbilderin_im_eigentuemerinnenkreis_angelegt(
        self,
    ) -> None:
        """Der Seed legt Trainings mit der Ausbilderin im Eigentümer-Kreis an."""
        call_command("entwicklungsdaten_anlegen", stdout=StringIO())
        ausbilderin: Konto = Konto.objects.get(username="autor")

        self.assertTrue(Training.objects.filter(eigentuemerinnen=ausbilderin).exists())

    def test_autor_ist_administrationskonto(self) -> None:
        """Der Entwicklungs-Seed macht das Administrationskonto zum Superuser."""
        call_command("entwicklungsdaten_anlegen", stdout=StringIO())

        konto: Konto = Konto.objects.get(username="autor")

        self.assertEqual((konto.is_superuser, konto.is_staff), (True, True))

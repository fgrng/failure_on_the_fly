"""Seitenköpfe und Knöpfe folgen einem Vokabular (#287, #313)."""

import re

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from erhebungen.models import Erhebung
from fragebogen_items.models import FragebogenItem
from konten.models import Konto
from simulation.models import Simulationskern
from training.models import Training
from vignetten.models import Vignette, Vignettenhistorie


def _text(html: str) -> str:
    """Entfernt Tags und fasst Leerraum zusammen."""
    return " ".join(re.sub(r"<[^>]+>", "", html).split())


class SeitenvokabularTests(TestCase):
    """Überzeile, Titel und Absendeknopf je Seite wie in der Entscheidung zu #287."""

    def setUp(self) -> None:
        self.linus: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.kern_entwurf: Simulationskern = kern.bearbeiten()
        self.vignette: Vignette = Vignette.objects.anlegen(self.linus)
        self.training: Training = Training.objects.anlegen(self.linus, name="Brüche")
        self.veroeffentlicht: Training = Training.objects.anlegen(
            self.linus, name="Prozente"
        )
        self.finale: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(name="Brüche vergleichen"),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Vergleiche Brüche.",
            arbeitsheft_text="3/4 ist größer als 2/3.",
        )
        self.veroeffentlicht.vignetten.add(self.finale)
        self.veroeffentlicht.veroeffentlichen()
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.linus, name="Pilot")
        self.item: FragebogenItem = FragebogenItem.objects.anlegen(self.linus)
        self.client.force_login(self.linus)

    def _kopf(self, antwort: HttpResponse) -> tuple[str, str]:
        """Liest Überzeile und Titel aus dem Seitenkopf."""
        self.assertEqual(antwort.status_code, 200)
        kopf: str = re.search(
            r'<header class="page-head">(.*?)</header>',
            antwort.content.decode(),
            re.DOTALL,
        ).group(1)
        ueberzeile: str = re.search(r"<p>(.*?)</p>", kopf, re.DOTALL).group(1)
        titel: re.Match[str] | None = re.search(r"<h1>(.*?)</h1>", kopf, re.DOTALL)
        return _text(ueberzeile), _text(titel.group(1)) if titel else ""

    def _knoepfe(self, antwort: HttpResponse) -> list[str]:
        """Nennt die Beschriftungen aller Absendeknöpfe der Seite."""
        return [
            _text(knopf)
            for knopf in re.findall(
                r'<button[^>]*type="submit"[^>]*>(.*?)</button>',
                antwort.content.decode(),
                re.DOTALL,
            )
        ]

    def test_seiten_zeigen_ueberzeile_titel_und_knopf(self) -> None:
        """Jede Seite der Tabelle nennt Bereich, Aktion bzw. Objekt und Knopf."""
        wahl_url: str = reverse(
            "training:wahl", args=[self.veroeffentlicht.pk, self.finale.pk]
        )
        seiten: tuple[tuple[str, str, str, str | None], ...] = (
            (
                reverse("vignetten:anlegen"),
                "Entwicklung / Vignetten",
                "Vignette anlegen",
                "Vignette anlegen",
            ),
            (
                reverse("vignetten:bearbeiten", args=[self.vignette.pk]),
                "Entwicklung / Vignetten",
                "Vignette bearbeiten",
                "Änderungen speichern",
            ),
            (
                reverse("vignetten:liste"),
                "Entwicklung / Vignetten",
                "Meine Vignetten",
                None,
            ),
            (
                reverse("vignetten:detail", args=[self.vignette.pk]),
                "Entwicklung / Vignetten",
                "Vignette",
                None,
            ),
            (
                reverse("simulation:kern"),
                "Entwicklung / Simulationskern",
                "Aktueller Kern",
                None,
            ),
            (
                reverse("simulation:kern_verwalten"),
                "Entwicklung / Simulationskern",
                "Kern verwalten",
                # »Neuen Entwurf anlegen« erscheint nur ohne offenen Entwurf.
                "Entwurf ziehen",
            ),
            (
                reverse("simulation:kern_bearbeiten", args=[self.kern_entwurf.pk]),
                "Entwicklung / Simulationskern",
                "Kern-Entwurf bearbeiten",
                "Änderungen speichern",
            ),
            (
                reverse("training:anlegen"),
                "Ausbildung / Trainings",
                "Training anlegen",
                "Training anlegen",
            ),
            (
                reverse("training:kuratieren", args=[self.training.pk]),
                "Ausbildung / Trainings",
                "Brüche",
                None,
            ),
            (reverse("training:katalog"), "Ausbildung", "Trainingskataloge", None),
            (reverse("training:liste"), "Ausbildung", "Meine Trainings", None),
            (
                reverse("training:detail", args=[self.veroeffentlicht.pk]),
                "Ausbildung / Training starten",
                "Prozente",
                None,
            ),
            (wahl_url, "Ausbildung / Training starten", "Vignette gewählt", None),
            (
                reverse("erhebungen:anlegen"),
                "Forschung / Meine Erhebungen",
                "Erhebung anlegen",
                "Erhebung anlegen",
            ),
            (
                reverse("erhebungen:detail", args=[self.erhebung.pk]),
                "Forschung / Meine Erhebungen",
                "Pilot",
                "Konfiguration speichern",
            ),
            (
                reverse("fragebogen_items:anlegen"),
                "Forschung / Fragebogen-Items",
                "Fragebogen-Item anlegen",
                "Fragebogen-Item anlegen",
            ),
            (
                reverse("fragebogen_items:bearbeiten", args=[self.item.pk]),
                "Forschung / Fragebogen-Items",
                "Fragebogen-Item bearbeiten",
                "Änderungen speichern",
            ),
            (
                reverse("simulation:modell_konfiguration"),
                "System / Modell-Konfiguration",
                "Modell-Konfiguration",
                None,
            ),
            (
                reverse("simulation:modell_konfiguration_neu"),
                "System / Modell-Konfiguration",
                "Modell-Konfiguration anlegen",
                "Konfiguration anlegen",
            ),
            (
                reverse("simulation:transkriptions_konfiguration"),
                "System / Transkriptions-Konfiguration",
                "Transkriptions-Konfiguration",
                "Änderungen speichern",
            ),
        )
        for url, ueberzeile, titel, knopf in seiten:
            with self.subTest(url=url):
                antwort: HttpResponse = self.client.get(url)
                self.assertEqual(self._kopf(antwort), (ueberzeile, titel))
                if knopf:
                    self.assertIn(knopf, self._knoepfe(antwort))

    def test_einwilligung_nennt_training_starten(self) -> None:
        """Die Einwilligung vor dem Start steht unter »Training starten«."""
        antwort: HttpResponse = self.client.post(
            reverse("training:wahl", args=[self.veroeffentlicht.pk, self.finale.pk])
        )

        self.assertEqual(
            self._kopf(antwort), ("Ausbildung / Training starten", "Audioverarbeitung")
        )

    def test_vignettenformular_ohne_schritt_fuer_schritt(self) -> None:
        """Der alte Titel entfällt ganz, auch als Untertitel."""
        antwort: HttpResponse = self.client.get(reverse("vignetten:anlegen"))

        self.assertNotContains(antwort, "Schritt für Schritt")

    def test_seitenkoepfe_und_knoepfe_sagen_anlegen_statt_erstellen(self) -> None:
        """Das Verb heißt überall »anlegen«."""
        for url in (
            reverse("vignetten:liste"),
            reverse("training:katalog"),
            reverse("training:anlegen"),
        ):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), "erstellen")

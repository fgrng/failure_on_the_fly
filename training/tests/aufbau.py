"""Aufbau der Trainingstests für Fremdeinsicht, Freigabe und Trainingsexport.

Gespielte Sitzungen und Abschriften entstehen hier über ``objects.create``:
Ein Ablauf über HTTP bräuchte Fake-Skripte bzw. eine ganze Erhebung und
ergäbe dieselben Zeilen. Konten, Modell-Konfiguration und Vignetten kommen
aus den gemeinsamen Helfern.
"""

from django.test import TestCase

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    finaler_kern,
    konto_mit_rollen,
)
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE, AUTORIN_GRUPPE
from simulation.models import ModellKonfiguration, Verwendung
from sitzungen.models import Diagnose, Gespraechsschritt, Sitzung, Teilnahme
from training.models import Abschrift, Training
from vignetten.models import Vignette


def gespielte_sitzung(
    training: Training,
    konto: Konto,
    vignette: Vignette,
    status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN,
    aeusserung: str = "Ich habe oben und unten zusammengezählt.",
) -> Sitzung:
    """Legt eine gespielte Sitzung unter der Trainingsbindung des Kontos an."""

    sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=training.bindung_fuer(konto).teilnahme,
        vignette=vignette,
        simulationskern=finaler_kern(),
        modell_konfiguration=ModellKonfiguration.objects.belegte(Verwendung.SCHUELERIN),
        status=status,
    )
    Gespraechsschritt.objects.create(
        sitzung=sitzung,
        eingabe="Wie hast du gerechnet?",
        denkspur="Geheime Denkspur der Schülerin.",
        aeusserung=aeusserung,
        reihenfolge=1,
    )
    Diagnose.objects.create(sitzung=sitzung, text="Zähler und Nenner addiert.")
    return sitzung


def abschrift(
    konto: Konto,
    vignette: Vignette,
    status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN,
) -> Abschrift:
    """Legt eine Abschrift mit einer kopierten Sitzung samt Denkspur an."""

    angelegt: Abschrift = Abschrift.objects.create(
        teilnahme=Teilnahme.objects.create(),
        konto=konto,
        erhebungsname="Studie Bruchrechnung",
    )
    sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=angelegt.teilnahme,
        vignette=vignette,
        simulationskern=finaler_kern(),
        modell_konfiguration=ModellKonfiguration.objects.belegte(Verwendung.SCHUELERIN),
        status=status,
    )
    Gespraechsschritt.objects.create(
        sitzung=sitzung,
        eingabe="Wie hast du gekürzt?",
        denkspur="Geheime Denkspur aus der Erhebung.",
        aeusserung="Ich habe nur oben geteilt.",
        reihenfolge=1,
    )
    Diagnose.objects.create(sitzung=sitzung, text="Nur den Zähler gekürzt.")
    return angelegt


class FremdeinsichtTestCase(TestCase):
    """Ein veröffentlichtes Training mit Kreis, Vignette und einer Teilnehmerin."""

    def setUp(self) -> None:
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        self.ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.autorin: Konto = konto_mit_rollen("barbara", AUTORIN_GRUPPE)
        self.teilnehmerin: Konto = Konto.objects.create_user(
            username="grace", first_name="Grace", last_name="Hopper"
        )
        self.vignette: Vignette = finale_vignette(self.autorin, name="Brüche addieren")
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.vignetten.add(self.vignette)
        self.training.veroeffentlichen()
        self.training.beitreten(self.teilnehmerin)

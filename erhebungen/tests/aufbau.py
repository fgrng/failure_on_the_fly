"""Aufbau der Erhebungstests über die gemeinsamen Helfer und den öffentlichen Weg."""

from collections.abc import Iterable

from config.tests.aufbau import aktive_modell_konfiguration, konto_mit_rollen
from erhebungen.models import Erhebung, Erhebungsvignette
from konten.models import Konto
from simulation.models import ModellKonfiguration, Verwendung
from vignetten.models import Vignette


def forschende(username: str) -> Konto:
    """Legt ein Konto mit der Rolle Forschende:r an."""

    return konto_mit_rollen(username, "Forschende:r")


def finale_erhebung(
    konto: Konto,
    name: str = "Brüche",
    vignetten: Iterable[Vignette] = (),
    **felder: object,
) -> Erhebung:
    """Legt eine Erhebung des Kontos an, nimmt die Vignetten auf und finalisiert.

    Ist für die Schüler:in noch keine Konfiguration aktiv, aktiviert der Helfer
    eine des Fake-Anbieters; eine schon aktive wird gepinnt.
    """

    if ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN) is None:
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name=name, **felder)
    for position, vignette in enumerate(vignetten, start=1):
        Erhebungsvignette.objects.create(
            erhebung=erhebung, vignette=vignette, position=position
        )
    erhebung.finalisieren()
    return erhebung

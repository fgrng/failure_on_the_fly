"""Sink-agnostische Orchestrierung eines Diagnosegesprächs."""

from collections.abc import Sequence

from simulation import Antwortversuch, antwort_versuchen
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.sink import FehlversuchDaten, SitzungSink
from vignetten.models import Vignette


def sitzung_starten(
    sink: SitzungSink,
    vignette: Vignette,
    simulationskern: Simulationskern,
    modell_konfiguration: ModellKonfiguration,
) -> None:
    """Beginnt die Sitzung bei ihrem übergebenen Ziel."""

    sink.sitzung_starten(vignette, simulationskern, modell_konfiguration)


def gespraechsschritt_ausfuehren(
    sink: SitzungSink,
    vignette: Vignette,
    simulationskern: Simulationskern,
    modell_konfiguration: ModellKonfiguration,
    verlauf: Sequence[str],
    eingabe: str,
) -> Antwortversuch:
    """Versucht eine Antwort und übergibt ihren Schritt ausschließlich dem Sink."""

    antwortversuch: Antwortversuch = antwort_versuchen(
        vignette,
        simulationskern,
        modell_konfiguration,
        verlauf,
        eingabe,
    )
    fehlversuche: list[FehlversuchDaten] = [
        {"grund": fehlversuch.grund, "rohantwort": fehlversuch.rohantwort}
        for fehlversuch in antwortversuch.fehlversuche
    ]
    if antwortversuch.antwort is None:
        sink.gescheiterten_schritt_anhaengen(
            eingabe=eingabe,
            fehlversuche=fehlversuche,
        )
        return antwortversuch
    sink.gespraechsschritt_anhaengen(
        eingabe=eingabe,
        denkspur=antwortversuch.antwort.denkspur,
        aeusserung=antwortversuch.antwort.aeusserung,
        native_reasoning_spur=antwortversuch.native_reasoning_spur,
        fehlversuche=fehlversuche,
    )
    return antwortversuch

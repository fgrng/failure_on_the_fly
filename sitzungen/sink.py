"""Naht für die Ziele einer Spielorchestrierung."""

from collections.abc import MutableMapping
from typing import Any, Protocol, TypedDict, cast

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Sitzung
from vignetten.models import Vignette


_PROBELAUF_SESSION_SCHLUESSEL: str = "probelauf"


class FehlversuchDaten(TypedDict):
    """Die speicherbare Form eines Fehlversuchs."""

    grund: str
    rohantwort: str


class GespraechsschrittDaten(TypedDict):
    """Die gemeinsame Speicherform eines Gesprächsschritts."""

    reihenfolge: int
    eingabe: str
    denkspur: str | None
    aeusserung: str | None
    native_reasoning_spur: str | None
    fehlversuche: list[FehlversuchDaten]


class SitzungSink(Protocol):
    """Das Ziel, an das die Spielorchestrierung ihre Ergebnisse übergibt."""

    def sitzung_starten(
        self,
        vignette: Vignette,
        simulationskern: Simulationskern,
        modell_konfiguration: ModellKonfiguration,
    ) -> None:
        """Beginnt eine Sitzung über ihrem festgelegten Tripel."""

    def gespraechsschritt_anhaengen(
        self,
        *,
        eingabe: str,
        denkspur: str,
        aeusserung: str,
        native_reasoning_spur: str | None,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Bewahrt einen geglückten Gesprächsschritt auf."""

    def gescheiterten_schritt_anhaengen(
        self, *, eingabe: str, fehlversuche: list[FehlversuchDaten]
    ) -> None:
        """Bewahrt einen endgültig gescheiterten Gesprächsschritt auf."""

    def diagnose_setzen(self, text: str) -> None:
        """Bewahrt die abschließende Diagnose auf."""

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Setzt den Lebenszyklusstatus der Sitzung."""


class ScratchSink:
    """Hält einen Probelauf ausschließlich in der Django-Session."""

    def __init__(self, session: MutableMapping[str, Any]) -> None:
        """Bindet den Sink an den Session-Speicher eines Probelaufs."""

        self.session: MutableMapping[str, Any] = session

    def sitzung_starten(
        self,
        vignette: Vignette,
        simulationskern: Simulationskern,
        modell_konfiguration: ModellKonfiguration,
    ) -> None:
        """Initialisiert den verworfenen Sitzungszustand in der Session."""

        self.session[_PROBELAUF_SESSION_SCHLUESSEL] = {
            "vignette_pk": vignette.pk,
            "kern_pk": simulationskern.pk,
            "modell_konfiguration_pk": modell_konfiguration.pk,
            "gespraechsschritte": [],
        }

    @property
    def gespraechsschritte(self) -> list[GespraechsschrittDaten]:
        """Liefert die gespeicherten Schritte für Ansicht und Modellverlauf."""

        return cast(list[GespraechsschrittDaten], self.zustand["gespraechsschritte"])

    @property
    def zustand(self) -> MutableMapping[str, Any]:
        """Liefert den privaten Session-Zustand des Scratch-Sinks."""

        return cast(
            MutableMapping[str, Any], self.session[_PROBELAUF_SESSION_SCHLUESSEL]
        )

    def gespraechsschritt_anhaengen(
        self,
        *,
        eingabe: str,
        denkspur: str,
        aeusserung: str,
        native_reasoning_spur: str | None,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Hängt den geglückten Schritt in gemeinsamer Speicherform an."""

        self.gespraechsschritte.append(
            {
                "reihenfolge": len(self.gespraechsschritte) + 1,
                "eingabe": eingabe,
                "denkspur": denkspur,
                "aeusserung": aeusserung,
                "native_reasoning_spur": native_reasoning_spur,
                "fehlversuche": fehlversuche,
            }
        )
        self._als_geaendert_markieren()

    def gescheiterten_schritt_anhaengen(
        self, *, eingabe: str, fehlversuche: list[FehlversuchDaten]
    ) -> None:
        """Hängt den answerless Schritt in gemeinsamer Speicherform an."""

        self.gespraechsschritte.append(
            {
                "reihenfolge": len(self.gespraechsschritte) + 1,
                "eingabe": eingabe,
                "denkspur": None,
                "aeusserung": None,
                "native_reasoning_spur": None,
                "fehlversuche": fehlversuche,
            }
        )
        self._als_geaendert_markieren()

    def diagnose_setzen(self, text: str) -> None:
        """Hält die im Probelauf verworfene Diagnose in der Session."""

        self.zustand["diagnose"] = text
        self._als_geaendert_markieren()

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Hält den Sitzungsstatus für den Probelauf fest."""

        self.zustand["status"] = status
        self._als_geaendert_markieren()

    def _als_geaendert_markieren(self) -> None:
        # Markiert verschachtelte Session-Änderungen für Django als speicherwürdig.

        if hasattr(self.session, "modified"):
            self.session.modified = True

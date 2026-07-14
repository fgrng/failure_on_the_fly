"""Naht für die Ziele einer Spielorchestrierung."""

from collections.abc import MutableMapping
from time import monotonic
from typing import Any, Protocol, TypedDict, cast

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Sitzung
from vignetten.models import Vignette


_PROBELAUF_SESSION_SCHLUESSEL: str = "probelauf"
_VERBRAUCHTE_ZEIT_SCHLUESSEL: str = "verbrauchte_zeit"
_ZEIT_LAEUFT_SEIT_SCHLUESSEL: str = "zeit_laeuft_seit"


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
        if vignette.budget_typ == Vignette.BudgetTyp.ZEIT:
            self._zustand[_VERBRAUCHTE_ZEIT_SCHLUESSEL] = 0.0

    @property
    def gespraechsschritte(self) -> list[GespraechsschrittDaten]:
        """Liefert die gespeicherten Schritte für Ansicht und Modellverlauf."""

        return cast(
            list[GespraechsschrittDaten], self._zustand["gespraechsschritte"]
        )

    @property
    def vignette_pk(self) -> int:
        """Liefert die beim Probelaufstart gepinnte Vignette."""

        return cast(int, self._zustand["vignette_pk"])

    @property
    def kern_pk(self) -> int:
        """Liefert den beim Probelaufstart gepinnten Simulationskern."""

        return cast(int, self._zustand["kern_pk"])

    @property
    def modell_konfiguration_pk(self) -> int:
        """Liefert die beim Probelaufstart gepinnte Modell-Konfiguration."""

        return cast(int, self._zustand["modell_konfiguration_pk"])

    @property
    def ist_gescheitert(self) -> bool:
        """Kennzeichnet einen terminal fehlgeschlagenen Probelauf."""

        return self._zustand.get("status") == Sitzung.Status.GESCHEITERT

    @property
    def ist_beendet(self) -> bool:
        """Kennzeichnet einen Probelauf, dessen Debrief bereits erreicht ist."""

        return self._zustand.get("status") == Sitzung.Status.ABGESCHLOSSEN

    @property
    def freie_auswahl(self) -> bool:
        """Kennzeichnet ein administrativ frei gewähltes Tripel."""

        return bool(self._zustand.get("freie_auswahl"))

    @property
    def _zustand(self) -> MutableMapping[str, Any]:
        # Kapselt die untypisierte Session-Struktur innerhalb des Scratch-Sinks.

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

    def gescheiterten_schritt_verwerfen(self) -> None:
        """Entfernt einen endgültig gescheiterten Schritt aus dem Probelauf."""

        self.gespraechsschritte.pop()
        self._zustand.pop("status")
        self._als_geaendert_markieren()

    def gescheiterten_schritt_anhaengen(
        self, *, eingabe: str, fehlversuche: list[FehlversuchDaten]
    ) -> None:
        """Hängt den antwortlosen Schritt in gemeinsamer Speicherform an."""

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

        self._zustand["diagnose"] = text
        self._als_geaendert_markieren()

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Hält den Sitzungsstatus für den Probelauf fest."""

        self._zustand["status"] = status
        self._als_geaendert_markieren()

    def freie_auswahl_setzen(self) -> None:
        """Markiert das Tripel als administrativ frei gewählt."""

        self._zustand["freie_auswahl"] = True
        self._als_geaendert_markieren()

    def budget_erschoepft(self, vignette: Vignette) -> bool:
        """Meldet, ob erfolgreiche Schritte oder Nutzungszeit das Budget aufbrauchen."""

        if vignette.budget_wert is None:
            return False
        if vignette.budget_typ == Vignette.BudgetTyp.SCHRITTE:
            return len(self.gespraechsschritte) >= vignette.budget_wert
        return self.verbrauchte_zeit >= vignette.budget_wert

    @property
    def verbrauchte_zeit(self) -> float:
        """Liefert die allein während des Autorinnenzugs gemessene Zeit."""

        return cast(float, self._zustand.get(_VERBRAUCHTE_ZEIT_SCHLUESSEL, 0.0))

    def zeitbudget_fortsetzen(self) -> None:
        """Startet die Uhr, wenn die Autorin wieder eine Eingabe verfassen kann."""

        if (
            _VERBRAUCHTE_ZEIT_SCHLUESSEL in self._zustand
            and _ZEIT_LAEUFT_SEIT_SCHLUESSEL not in self._zustand
        ):
            self._zustand[_ZEIT_LAEUFT_SEIT_SCHLUESSEL] = monotonic()
            self._als_geaendert_markieren()

    def zeitbudget_anhalten(self) -> None:
        """Hält die Uhr für Modellaufruf und Fehlversuche an."""

        startzeit: float | None = self._zustand.pop(
            _ZEIT_LAEUFT_SEIT_SCHLUESSEL, None
        )
        if startzeit is not None:
            self._zustand[_VERBRAUCHTE_ZEIT_SCHLUESSEL] = self.verbrauchte_zeit + (
                monotonic() - startzeit
            )
            self._als_geaendert_markieren()

    def verwerfen(self) -> None:
        """Entfernt den vollständigen Probelaufzustand aus der Session."""

        self.session.pop(_PROBELAUF_SESSION_SCHLUESSEL, None)

    def _als_geaendert_markieren(self) -> None:
        # Markiert verschachtelte Session-Änderungen für Django als speicherwürdig.

        if hasattr(self.session, "modified"):
            self.session.modified = True

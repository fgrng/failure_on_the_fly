"""Naht für die Ziele eines Sitzungslaufs."""

from collections.abc import Iterable, MutableMapping
from time import monotonic
from typing import Any, Protocol, TypedDict, cast

from django.db import transaction
from django.db.models import QuerySet

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
)
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
    eingabemodus: str
    denkspur: str | None
    aeusserung: str | None
    fehlversuche: list[FehlversuchDaten]


class SitzungSink(Protocol):
    """Das Ziel, an das der Lauf einer Sitzung seine Ergebnisse übergibt."""

    def sitzung_starten(
        self,
        vignette: Vignette,
        simulationskern: Simulationskern,
        modell_konfiguration: ModellKonfiguration,
    ) -> None:
        """Beginnt eine Sitzung über ihrem festgelegten Tripel."""

    @property
    def gespraechsschritte(
        self,
    ) -> Iterable[GespraechsschrittDaten | Gespraechsschritt]:
        """Liefert die bisherigen Gesprächsschritte in gespeicherter Reihenfolge."""

    def gespraechsschritt_anhaengen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Bewahrt einen geglückten Gesprächsschritt auf."""

    def gescheiterten_schritt_behandeln(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Behält oder verwirft den endgültig fehlgeschlagenen Schritt."""

    def diagnose_setzen(self, text: str) -> None:
        """Bewahrt die abschließende Diagnose auf."""

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Setzt den Lebenszyklusstatus der Sitzung."""

    @property
    def verbrauchte_zeit(self) -> float:
        """Liefert die während der Züge verbrauchte Zeit in Sekunden."""

    def budget_erschoepft(self, vignette: Vignette) -> bool:
        """Meldet, ob erfolgreiche Schritte oder Nutzungszeit das Budget aufbrauchen."""

    def gespraechsende_vermerken(self) -> None:
        """Hält fest, dass das erschöpfte Budget das Diagnosegespräch beendet hat."""

    def zeitbudget_fortsetzen(self) -> None:
        """Startet die Uhr, wenn die teilnehmende Person wieder eine Eingabe verfassen kann."""

    def zeitbudget_anhalten(self) -> None:
        """Hält die Uhr für Modellaufruf und Fehlversuche an."""


class DBSink:
    """Persistiert eine Sitzung inkrementell über die ORM-Modelle."""

    def __init__(
        self,
        teilnahme: Teilnahme,
        session: MutableMapping[str, Any] | None = None,
    ) -> None:
        """Bindet den Sink an die Teilnahme und optional an die Browser-Session."""

        self.teilnahme: Teilnahme = teilnahme
        self.sitzung: Sitzung | None = None
        self.session: MutableMapping[str, Any] = {} if session is None else session

    @classmethod
    def fuer_sitzung(
        cls,
        sitzung: Sitzung,
        session: MutableMapping[str, Any] | None = None,
    ) -> "DBSink":
        """Stellt den Sink für eine bereits persistierte Sitzung wieder her."""

        sink: DBSink = cls(sitzung.teilnahme, session=session)
        sink.sitzung = sitzung
        return sink

    def sitzung_starten(
        self,
        vignette: Vignette,
        simulationskern: Simulationskern,
        modell_konfiguration: ModellKonfiguration,
    ) -> None:
        """Legt die identitätstragende Sitzung sofort an."""

        self.sitzung = Sitzung.objects.create(
            teilnahme=self.teilnahme,
            vignette=vignette,
            simulationskern=simulationskern,
            modell_konfiguration=modell_konfiguration,
        )

    def gespraechsschritt_anhaengen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Schreibt einen geglückten Schritt und seine Fehlversuche atomar."""

        with transaction.atomic():
            schritt: Gespraechsschritt = Gespraechsschritt.objects.create(
                sitzung=self._sitzung,
                eingabe=eingabe,
                eingabemodus=eingabemodus,
                denkspur=denkspur,
                aeusserung=aeusserung,
                reihenfolge=self._naechste_reihenfolge(),
            )
            Fehlversuch.objects.bulk_create(
                [
                    Fehlversuch(gespraechsschritt=schritt, **fehlversuch)
                    for fehlversuch in fehlversuche
                ]
            )

    def gescheiterten_schritt_behandeln(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Behält den Abbruchschritt und schreibt den gescheiterten Status atomar (ADR-0011)."""

        with transaction.atomic():
            Gespraechsschritt.objects.answerless_anlegen(
                sitzung=self._sitzung,
                eingabe=eingabe,
                eingabemodus=eingabemodus,
                reihenfolge=self._naechste_reihenfolge(),
                fehlversuche=[
                    Fehlversuch(**fehlversuch) for fehlversuch in fehlversuche
                ],
            )
            self.status_setzen(Sitzung.Status.GESCHEITERT)

    def diagnose_setzen(self, text: str) -> None:
        """Speichert die Diagnose und schließt die Sitzung gemeinsam ab."""

        with transaction.atomic():
            Diagnose.objects.create(sitzung=self._sitzung, text=text)
            self.status_setzen(Sitzung.Status.ABGESCHLOSSEN)

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Persistiert einen Statusübergang sofort."""

        self._sitzung.status = status
        self._sitzung.save(update_fields=["status"])

    @property
    def gespraechsschritte(self) -> QuerySet[Gespraechsschritt]:
        """Liefert die gespeicherten Schritte in ihrer Reihenfolge."""

        return self._sitzung.gespraechsschritte

    @property
    def _sitzung(self) -> Sitzung:
        # Liefert die gestartete Sitzung oder weist auf einen falschen Ablauf hin.

        if self.sitzung is None:
            raise RuntimeError("Der DB-Sink braucht zuerst eine gestartete Sitzung.")
        return self.sitzung

    def _naechste_reihenfolge(self) -> int:
        # Bestimmt die fortlaufende Position des nächsten Gesprächsschritts.

        return self.gespraechsschritte.count() + 1

    def _zeitbudget_schluessel(self, name: str) -> str:
        # Isoliert die Uhr jeder persistierten Sitzung von allen anderen Sitzungen.

        return f"sitzung_{self._sitzung.pk}_{name}"

    def budget_erschoepft(self, vignette: Vignette) -> bool:
        """Meldet, ob erfolgreiche Schritte oder Nutzungszeit das Budget aufbrauchen."""

        if vignette.budget_wert is None:
            return False
        if vignette.budget_typ == Vignette.BudgetTyp.SCHRITTE:
            return self.gespraechsschritte.count() >= vignette.budget_wert
        return self.verbrauchte_zeit >= vignette.budget_wert

    def gespraechsende_vermerken(self) -> None:
        """Lässt die Sitzung laufen: Erst die Diagnose schließt sie ab (ADR-0009)."""

    @property
    def verbrauchte_zeit(self) -> float:
        """Liefert die verbrauchte Zeit aus der Session."""

        return cast(
            float,
            self.session.get(
                self._zeitbudget_schluessel(_VERBRAUCHTE_ZEIT_SCHLUESSEL), 0.0
            ),
        )

    def zeitbudget_fortsetzen(self) -> None:
        """Startet die unsichtbare Uhr ausschließlich während des Teilnahmezugs."""

        schluessel: str = self._zeitbudget_schluessel(_ZEIT_LAEUFT_SEIT_SCHLUESSEL)
        if (
            self._sitzung.vignette.budget_typ == Vignette.BudgetTyp.ZEIT
            and schluessel not in self.session
        ):
            self.session[schluessel] = monotonic()
            self._als_geaendert_markieren()

    def zeitbudget_anhalten(self) -> None:
        """Hält die Uhr vor Modellaufruf und schreibt die verbrauchte Zeit fort."""

        schluessel_startzeit: str = self._zeitbudget_schluessel(
            _ZEIT_LAEUFT_SEIT_SCHLUESSEL
        )
        startzeit: float | None = self.session.pop(schluessel_startzeit, None)
        if startzeit is not None:
            schluessel_verbraucht: str = self._zeitbudget_schluessel(
                _VERBRAUCHTE_ZEIT_SCHLUESSEL
            )
            self.session[schluessel_verbraucht] = self.verbrauchte_zeit + (
                monotonic() - startzeit
            )
            self._als_geaendert_markieren()

    def _als_geaendert_markieren(self) -> None:
        # Markiert Session-Änderungen für Django als speicherwürdig.

        if hasattr(self.session, "modified"):
            self.session.modified = True


def probelauf_laeuft(session: MutableMapping[str, Any]) -> bool:
    """Meldet, ob die Session einen laufenden Probelauf trägt."""

    return _PROBELAUF_SESSION_SCHLUESSEL in session


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

        return cast(list[GespraechsschrittDaten], self._zustand["gespraechsschritte"])

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
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Hängt den geglückten Schritt in gemeinsamer Speicherform an."""

        self.gespraechsschritte.append(
            {
                "reihenfolge": len(self.gespraechsschritte) + 1,
                "eingabe": eingabe,
                "eingabemodus": eingabemodus,
                "denkspur": denkspur,
                "aeusserung": aeusserung,
                "fehlversuche": fehlversuche,
            }
        )
        self._als_geaendert_markieren()

    def gescheiterten_schritt_behandeln(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Verwirft den gescheiterten Schritt: Der Probelauf hält keinen Abbruch fest.

        Er dokumentiert nichts (ADR-0014) und bleibt offen, damit die Autor:in
        dieselbe Eingabe erneut senden kann.
        """

    def diagnose_setzen(self, text: str) -> None:
        """Hält die im Probelauf verworfene Diagnose in der Session."""

        self._zustand["diagnose"] = text
        self.status_setzen(Sitzung.Status.ABGESCHLOSSEN)

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Hält den Sitzungsstatus für den Probelauf fest."""

        self._zustand["status"] = status
        self._als_geaendert_markieren()

    def gespraechsende_vermerken(self) -> None:
        """Schließt den Probelauf ab, den keine gespeicherte Diagnose beenden wird."""

        self.status_setzen(Sitzung.Status.ABGESCHLOSSEN)

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

        startzeit: float | None = self._zustand.pop(_ZEIT_LAEUFT_SEIT_SCHLUESSEL, None)
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

"""Naht für die Ziele eines Sitzungslaufs."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, MutableMapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, TypedDict, cast

from django.db import transaction
from django.db.models import QuerySet

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Eingabemodus,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
)
from vignetten.models import Vignette


_PROBELAUF_SESSION_SCHLUESSEL: str = "probelauf"
_FLUECHTIGE_SITZUNGEN_SCHLUESSEL: str = "fluechtige_sitzungen"
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


@dataclass
class Budgetstand:
    """Der speicherlose Verbrauch eines Gesprächsbudgets."""

    verbrauchte_zeit: float = 0.0
    geglueckte_schritte: int = 0
    offene_spanne_seit: datetime | None = None

    def zug_beginnen(self, jetzt: datetime) -> None:
        """Setzt die offene Spanne eines neu angezeigten Zuges neu an."""

        self.offene_spanne_seit = jetzt

    def zug_beenden(self, jetzt: datetime) -> None:
        """Bucht die offene Spanne und hält die Uhr an."""

        if self.offene_spanne_seit is not None:
            self.verbrauchte_zeit += (jetzt - self.offene_spanne_seit).total_seconds()
            self.offene_spanne_seit = None

    def gespraechsschritt_anhaengen(self) -> None:
        """Zählt einen erfolgreich zu Ende geführten Gesprächsschritt."""

        self.geglueckte_schritte += 1

    def ist_erschoepft(self, budget_typ: str, budget_wert: int | None) -> bool:
        """Prüft die eine Budgetgrenze nach ihrem aktiven Maß."""

        if budget_wert is None:
            return False
        if budget_typ == Vignette.BudgetTyp.SCHRITTE:
            return self.geglueckte_schritte >= budget_wert
        return self.verbrauchte_zeit >= budget_wert


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
    ) -> bool:
        """Bewahrt einen geglückten Schritt und meldet die Budgeterschöpfung."""

    def gescheiterten_schritt_behandeln(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Behält oder verwirft den endgültig fehlgeschlagenen Schritt."""

    def diagnose_setzen(
        self, text: str, *, eingabemodus: str = Eingabemodus.GETIPPT
    ) -> None:
        """Bewahrt die abschließende Diagnose auf."""

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Setzt den Lebenszyklusstatus der Sitzung."""

    def zug_beginnen(self, jetzt: datetime) -> None:
        """Setzt die offene Spanne der angezeigten Gesprächsseite neu an."""

    def zug_beenden(self, jetzt: datetime) -> None:
        """Bucht die offene Spanne vor Modellaufruf oder Sitzungsende."""


class GeruestSink(ABC):
    """Führt das Ablaufgerüst einer Sitzung inkrementell in der DB.

    Sitzung, Status und Budget-Uhr stehen an der Sitzungszeile. Wo
    Gesprächsschritte, Fehlversuche und Diagnose liegen, legen die beiden
    Senken selbst fest (ADR-0045).
    """

    def __init__(self, teilnahme: Teilnahme) -> None:
        """Bindet den Sink an die Teilnahme."""

        self.teilnahme: Teilnahme = teilnahme
        self.sitzung: Sitzung | None = None

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
    ) -> bool:
        """Bewahrt einen geglückten Schritt und meldet die Budgeterschöpfung."""

        budgetstand: Budgetstand = self._budgetstand_laden()
        self._geglueckten_schritt_ablegen(
            eingabe=eingabe,
            eingabemodus=eingabemodus,
            denkspur=denkspur,
            aeusserung=aeusserung,
            fehlversuche=fehlversuche,
        )
        budgetstand.gespraechsschritt_anhaengen()
        self._budgetstand_speichern(budgetstand)
        return budgetstand.ist_erschoepft(
            self._sitzung.vignette.budget_typ, self._sitzung.vignette.budget_wert
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
            self._abbruchschritt_ablegen(
                eingabe=eingabe, eingabemodus=eingabemodus, fehlversuche=fehlversuche
            )
            self.status_setzen(Sitzung.Status.GESCHEITERT)

    def diagnose_setzen(
        self, text: str, *, eingabemodus: str = Eingabemodus.GETIPPT
    ) -> None:
        """Bewahrt die Diagnose und schließt die Sitzung gemeinsam ab."""

        with transaction.atomic():
            self._diagnose_ablegen(text, eingabemodus=eingabemodus)
            self.status_setzen(Sitzung.Status.ABGESCHLOSSEN)

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Persistiert einen Statusübergang sofort."""

        self._sitzung.status = status
        self._sitzung.save(update_fields=["status"])

    @property
    @abstractmethod
    def gespraechsschritte(
        self,
    ) -> Iterable[GespraechsschrittDaten | Gespraechsschritt]:
        """Liefert die bisherigen Schritte in ihrer Reihenfolge."""

    @property
    @abstractmethod
    def verlauf_fehlt(self) -> bool:
        """Meldet, ob der Verlauf der Sitzung hier nicht greifbar ist."""

    @property
    @abstractmethod
    def abgegebene_diagnose(self) -> str | None:
        """Liefert den Text der bereits abgegebenen Diagnose, sonst nichts."""

    @abstractmethod
    def _geglueckten_schritt_ablegen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Legt einen geglückten Schritt samt Fehlversuchen dort ab, wo dieser
        # Sink Inhalte hält.
        ...

    @abstractmethod
    def _abbruchschritt_ablegen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Legt den antwortlosen Schritt eines endgültigen Fehlschlags ab.
        ...

    @abstractmethod
    def _diagnose_ablegen(self, text: str, *, eingabemodus: str) -> None:
        # Legt die Diagnose dort ab, wo dieser Sink Inhalte hält.
        ...

    @abstractmethod
    def _schrittzahl(self) -> int:
        # Zählt die bisherigen Schritte dort, wo dieser Sink sie hält.
        ...

    @property
    def _sitzung(self) -> Sitzung:
        # Liefert die gestartete Sitzung oder weist auf einen falschen Ablauf hin.

        if self.sitzung is None:
            raise RuntimeError("Der Sink braucht zuerst eine gestartete Sitzung.")
        return self.sitzung

    def _naechste_reihenfolge(self) -> int:
        # Bestimmt die fortlaufende Position des nächsten Gesprächsschritts.

        return self._schrittzahl() + 1

    def zug_beginnen(self, jetzt: datetime) -> None:
        """Setzt die offene Spanne der Teilnehmerin neu an."""

        if not self._sitzung.vignette.uhr_laeuft:
            return
        budgetstand: Budgetstand = self._budgetstand_laden()
        budgetstand.zug_beginnen(jetzt)
        self._budgetstand_speichern(budgetstand)

    def zug_beenden(self, jetzt: datetime) -> None:
        """Bucht die offene Spanne vor einem Modellaufruf."""

        if not self._sitzung.vignette.uhr_laeuft:
            return
        budgetstand: Budgetstand = self._budgetstand_laden()
        budgetstand.zug_beenden(jetzt)
        self._budgetstand_speichern(budgetstand)

    def _budgetstand_laden(self) -> Budgetstand:
        # Rekonstruiert den Stand aus den Feldern der zugehörigen Sitzung.

        return Budgetstand(
            verbrauchte_zeit=self._sitzung.verbrauchte_zeit,
            geglueckte_schritte=self._schrittzahl(),
            offene_spanne_seit=self._sitzung.offene_spanne_seit,
        )

    def _budgetstand_speichern(self, budgetstand: Budgetstand) -> None:
        # Schreibt Zeitstand und offene Spanne an die Sitzungszeile zurück.

        self._sitzung.verbrauchte_zeit = budgetstand.verbrauchte_zeit
        self._sitzung.offene_spanne_seit = budgetstand.offene_spanne_seit
        self._sitzung.save(update_fields=["verbrauchte_zeit", "offene_spanne_seit"])


class DBSink(GeruestSink):
    """Persistiert eine Sitzung samt Inhalten inkrementell über die ORM-Modelle."""

    @classmethod
    def fuer_sitzung(cls, sitzung: Sitzung) -> "DBSink":
        """Stellt den Sink für eine bereits persistierte Sitzung wieder her."""

        sink: DBSink = cls(sitzung.teilnahme)
        sink.sitzung = sitzung
        return sink

    @property
    def gespraechsschritte(self) -> QuerySet[Gespraechsschritt]:
        """Liefert die gespeicherten Schritte in ihrer Reihenfolge."""

        return self._sitzung.gespraechsschritte

    @property
    def verlauf_fehlt(self) -> bool:
        """Die DB trägt den Verlauf in jeden Browser; er fehlt nie."""

        return False

    @property
    def abgegebene_diagnose(self) -> str | None:
        """Liefert den Text der bereits abgegebenen Diagnose, sonst nichts."""

        return (
            Diagnose.objects.filter(sitzung=self._sitzung)
            .values_list("text", flat=True)
            .first()
        )

    def _geglueckten_schritt_ablegen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Schreibt einen geglückten Schritt und seine Fehlversuche atomar.

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

    def _abbruchschritt_ablegen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Behält den antwortlosen Schritt samt Fehlversuchen in der DB.

        Gespraechsschritt.objects.answerless_anlegen(
            sitzung=self._sitzung,
            eingabe=eingabe,
            eingabemodus=eingabemodus,
            reihenfolge=self._naechste_reihenfolge(),
            fehlversuche=[Fehlversuch(**fehlversuch) for fehlversuch in fehlversuche],
        )

    def _diagnose_ablegen(self, text: str, *, eingabemodus: str) -> None:
        # Speichert die Diagnose als eigene Zeile.

        Diagnose.objects.create(
            sitzung=self._sitzung, text=text, eingabemodus=eingabemodus
        )

    def _schrittzahl(self) -> int:
        # Zählt die Zeilen der DB.

        return self._sitzung.gespraechsschritte.count()


class FluechtigerSink(GeruestSink):
    """Führt das Ablaufgerüst in der DB und die Inhalte nur in der Session.

    Die Senke der flüchtigen Teilnahme: Gesprächsschritte samt Fehlversuchen
    und die Diagnose liegen allein in der Browser-Session, je Sitzung unter
    ihrem Primärschlüssel, und erreichen die DB nie.
    """

    def __init__(self, teilnahme: Teilnahme, session: MutableMapping[str, Any]) -> None:
        """Bindet den Sink an die Teilnahme und den Session-Speicher des Browsers."""

        super().__init__(teilnahme)
        self.session: MutableMapping[str, Any] = session

    @classmethod
    def fuer_sitzung(
        cls, sitzung: Sitzung, session: MutableMapping[str, Any]
    ) -> "FluechtigerSink":
        """Stellt den Sink für eine laufende oder beendete Sitzung wieder her."""

        sink: FluechtigerSink = cls(sitzung.teilnahme, session)
        sink.sitzung = sitzung
        return sink

    def sitzung_starten(
        self,
        vignette: Vignette,
        simulationskern: Simulationskern,
        modell_konfiguration: ModellKonfiguration,
    ) -> None:
        """Legt die Sitzung in der DB und ihren Verlauf in dieser Session an."""

        super().sitzung_starten(vignette, simulationskern, modell_konfiguration)
        self._verlauf_anlegen()

    @property
    def verlauf_fehlt(self) -> bool:
        """Meldet eine Sitzung, deren Verlauf nicht in dieser Session liegt.

        Das ist in einem anderen Browser oder nach Ablauf der Session der Fall.
        """

        return str(self._sitzung.pk) not in self._sitzungsverlaeufe

    @property
    def gespraechsschritte(self) -> list[GespraechsschrittDaten]:
        """Liefert die Schritte dieser Sitzung aus der Session."""

        return cast(
            list[GespraechsschrittDaten],
            self._zustand.setdefault("gespraechsschritte", []),
        )

    @property
    def abgegebene_diagnose(self) -> str | None:
        """Liefert die in der Session gehaltene Diagnose."""

        return cast(str | None, self._zustand.get("diagnose"))

    def _geglueckten_schritt_ablegen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Hängt den geglückten Schritt an den Verlauf der Session.

        self._schritt_anhaengen(
            eingabe, eingabemodus, denkspur, aeusserung, fehlversuche
        )

    def _abbruchschritt_ablegen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Hält den antwortlosen Schritt nur im Verlauf der Session.

        self._schritt_anhaengen(eingabe, eingabemodus, None, None, fehlversuche)

    def _diagnose_ablegen(self, text: str, *, eingabemodus: str) -> None:
        # Hält die Diagnose in der Session. Der Eingabemodus gehört zum Inhalt
        # und wird deshalb nicht festgehalten.

        self._zustand["diagnose"] = text
        _session_als_geaendert_markieren(self.session)

    def _schritt_anhaengen(
        self,
        eingabe: str,
        eingabemodus: str,
        denkspur: str | None,
        aeusserung: str | None,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Legt einen Schritt in der gemeinsamen Speicherform in die Session.

        self.gespraechsschritte.append(
            _schrittdaten(
                self._naechste_reihenfolge(),
                eingabe,
                eingabemodus,
                denkspur,
                aeusserung,
                fehlversuche,
            )
        )
        _session_als_geaendert_markieren(self.session)

    def _schrittzahl(self) -> int:
        # Zählt die Schritte der Session statt der Zeilen der DB.

        return len(self.gespraechsschritte)

    def _verlauf_anlegen(self) -> None:
        # Der leere Eintrag weist diese Session als Trägerin des Verlaufs aus.

        self._sitzungsverlaeufe[str(self._sitzung.pk)] = {"gespraechsschritte": []}
        _session_als_geaendert_markieren(self.session)

    @property
    def _sitzungsverlaeufe(self) -> MutableMapping[str, Any]:
        # Die Verläufe aller flüchtigen Sitzungen dieser Session.

        return cast(
            MutableMapping[str, Any],
            self.session.setdefault(_FLUECHTIGE_SITZUNGEN_SCHLUESSEL, {}),
        )

    @property
    def _zustand(self) -> MutableMapping[str, Any]:
        # Kapselt den Session-Eintrag dieser einen Sitzung.

        return cast(
            MutableMapping[str, Any],
            self._sitzungsverlaeufe.setdefault(str(self._sitzung.pk), {}),
        )


def _schrittdaten(
    reihenfolge: int,
    eingabe: str,
    eingabemodus: str,
    denkspur: str | None,
    aeusserung: str | None,
    fehlversuche: list[FehlversuchDaten],
) -> GespraechsschrittDaten:
    # Baut die gemeinsame Speicherform der beiden Session-Senken.

    return {
        "reihenfolge": reihenfolge,
        "eingabe": eingabe,
        "eingabemodus": eingabemodus,
        "denkspur": denkspur,
        "aeusserung": aeusserung,
        "fehlversuche": fehlversuche,
    }


def _session_als_geaendert_markieren(session: MutableMapping[str, Any]) -> None:
    # Markiert verschachtelte Session-Änderungen für Django als speicherwürdig.

    if hasattr(session, "modified"):
        session.modified = True


def sink_fuer_teilnahme(
    teilnahme: Teilnahme, session: MutableMapping[str, Any]
) -> GeruestSink:
    """Wählt die Senke einer neuen Sitzung allein nach der Speicherung."""

    if teilnahme.ist_fluechtig:
        return FluechtigerSink(teilnahme, session)
    return DBSink(teilnahme)


def sink_fuer_sitzung(
    sitzung: Sitzung, session: MutableMapping[str, Any]
) -> GeruestSink:
    """Wählt die Senke einer bestehenden Sitzung allein nach der Speicherung."""

    if sitzung.teilnahme.ist_fluechtig:
        return FluechtigerSink.fuer_sitzung(sitzung, session)
    return DBSink.fuer_sitzung(sitzung)


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

        self._gestartete_vignette: Vignette = vignette
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
    ) -> bool:
        """Hängt den geglückten Schritt in gemeinsamer Speicherform an."""

        budgetstand: Budgetstand = self._budgetstand_laden()
        self.gespraechsschritte.append(
            _schrittdaten(
                len(self.gespraechsschritte) + 1,
                eingabe,
                eingabemodus,
                denkspur,
                aeusserung,
                fehlversuche,
            )
        )
        budgetstand.gespraechsschritt_anhaengen()
        self._budgetstand_speichern(budgetstand)
        erschoepft: bool = budgetstand.ist_erschoepft(
            self._vignette.budget_typ, self._vignette.budget_wert
        )
        if erschoepft:
            self.status_setzen(Sitzung.Status.ABGESCHLOSSEN)
        return erschoepft

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

    def diagnose_setzen(
        self, text: str, *, eingabemodus: str = Eingabemodus.GETIPPT
    ) -> None:
        """Hält die im Probelauf verworfene Diagnose in der Session.

        Der Modus reist bis hierher, wird aber nicht festgehalten: Der
        Probelauf verwirft die Diagnose ohnehin (ADR-0014).
        """

        self._zustand["diagnose"] = text
        self.status_setzen(Sitzung.Status.ABGESCHLOSSEN)

    def status_setzen(self, status: Sitzung.Status) -> None:
        """Hält den Sitzungsstatus für den Probelauf fest."""

        self._zustand["status"] = status
        _session_als_geaendert_markieren(self.session)

    def freie_auswahl_setzen(self) -> None:
        """Markiert das Tripel als administrativ frei gewählt."""

        self._zustand["freie_auswahl"] = True
        _session_als_geaendert_markieren(self.session)

    @property
    def _vignette(self) -> Vignette:
        # Holt die beim Start gepinnte Vignette nur für die Budgetentscheidung.

        if not hasattr(self, "_gestartete_vignette"):
            self._gestartete_vignette = Vignette.objects.get(pk=self.vignette_pk)
        return self._gestartete_vignette

    def zug_beginnen(self, jetzt: datetime) -> None:
        """Setzt die offene Spanne der Autorin neu an."""

        if not self._vignette.uhr_laeuft:
            return
        budgetstand: Budgetstand = self._budgetstand_laden()
        budgetstand.zug_beginnen(jetzt)
        self._budgetstand_speichern(budgetstand)

    def zug_beenden(self, jetzt: datetime) -> None:
        """Bucht die offene Spanne vor einem Modellaufruf."""

        if not self._vignette.uhr_laeuft:
            return
        budgetstand: Budgetstand = self._budgetstand_laden()
        budgetstand.zug_beenden(jetzt)
        self._budgetstand_speichern(budgetstand)

    def _budgetstand_laden(self) -> Budgetstand:
        # Liest die für den Probelauf eingebettete Speicherform.

        startzeit: str | None = self._zustand.get(_ZEIT_LAEUFT_SEIT_SCHLUESSEL)
        return Budgetstand(
            verbrauchte_zeit=cast(
                float, self._zustand.get(_VERBRAUCHTE_ZEIT_SCHLUESSEL, 0.0)
            ),
            geglueckte_schritte=len(self.gespraechsschritte),
            offene_spanne_seit=datetime.fromisoformat(startzeit)
            if startzeit is not None
            else None,
        )

    def _budgetstand_speichern(self, budgetstand: Budgetstand) -> None:
        # Hält den Probelauf weiter vollständig in der Browser-Session.

        self._zustand[_VERBRAUCHTE_ZEIT_SCHLUESSEL] = budgetstand.verbrauchte_zeit
        if budgetstand.offene_spanne_seit is None:
            self._zustand.pop(_ZEIT_LAEUFT_SEIT_SCHLUESSEL, None)
        else:
            self._zustand[_ZEIT_LAEUFT_SEIT_SCHLUESSEL] = (
                budgetstand.offene_spanne_seit.isoformat()
            )
        _session_als_geaendert_markieren(self.session)

    def verwerfen(self) -> None:
        """Entfernt den vollständigen Probelaufzustand aus der Session."""

        self.session.pop(_PROBELAUF_SESSION_SCHLUESSEL, None)

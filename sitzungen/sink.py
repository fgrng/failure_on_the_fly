"""Naht für die Ziele eines Sitzungslaufs."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, MutableMapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, TypedDict, cast

from django.db import transaction
from django.db.models import QuerySet

from simulation.models import (
    ModellKonfiguration,
    Simulationskern,
    TranskriptionsKonfiguration,
)
from sitzungen import kurzlebiger_speicher
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
_VERBRAUCHTE_ZEIT_SCHLUESSEL: str = "verbrauchte_zeit"
_ZEIT_LAEUFT_SEIT_SCHLUESSEL: str = "zeit_laeuft_seit"


class AntwortversuchVerfallen(Exception):
    """Der Antwortversuch kam zu spät oder wurde überholt und wird kein Schritt.

    Die Sitzung lief beim Schreiben nicht mehr, oder ein anderer Schritt hat
    den Verlauf inzwischen verlängert (ADR-0066).
    """


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

    def antwortversuch_beginnen(self, jetzt: datetime) -> None:
        """Hält die Uhr an und merkt sich den Verlauf, auf dem der Versuch aufsetzt."""

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
        """Bewahrt einen geglückten Schritt und meldet die Budgeterschöpfung.

        Wirft `AntwortversuchVerfallen`, wenn der Schritt nicht mehr gilt.
        """

    def gescheiterten_schritt_behandeln(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        """Behält oder verwirft den endgültig fehlgeschlagenen Schritt.

        Wirft `AntwortversuchVerfallen`, wenn der Schritt nicht mehr gilt.
        """

    def diagnose_setzen(
        self, text: str, *, eingabemodus: str = Eingabemodus.GETIPPT
    ) -> bool:
        """Bewahrt die abschließende Diagnose auf und meldet, ob sie galt."""

    def status_setzen(self, status: Sitzung.Status) -> bool:
        """Setzt den Lebenszyklusstatus der Sitzung und meldet, ob es gelang."""

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
        self._begonnen_bei: int | None = None

    def sitzung_starten(
        self,
        vignette: Vignette,
        simulationskern: Simulationskern,
        modell_konfiguration: ModellKonfiguration,
    ) -> None:
        """Legt die identitätstragende Sitzung sofort an.

        Sie pinnt die aktive Transkriptions-Fassung: Alle ihre Aufnahmen gehen
        an denselben Anbieter, ein Wechsel wirkt ab der nächsten Sitzung.
        """

        self.sitzung = Sitzung.objects.create(
            teilnahme=self.teilnahme,
            vignette=vignette,
            simulationskern=simulationskern,
            modell_konfiguration=modell_konfiguration,
            transkriptions_konfiguration=TranskriptionsKonfiguration.objects.aktive(),
        )

    def antwortversuch_beginnen(self, jetzt: datetime) -> None:
        """Hält die Uhr an und merkt sich die Schrittzahl, auf der der Versuch aufsetzt."""

        self.zug_beenden(jetzt)
        self._begonnen_bei = self._schrittzahl()

    def gespraechsschritt_anhaengen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> bool:
        """Bewahrt einen geglückten Schritt und meldet die Budgeterschöpfung.

        Läuft die Sitzung nicht mehr oder hat ein anderer Schritt den Verlauf
        verlängert, verfällt der Antwortversuch (ADR-0066).
        """

        with transaction.atomic():
            self._antwortversuch_pruefen()
            self._geglueckten_schritt_ablegen(
                eingabe=eingabe,
                eingabemodus=eingabemodus,
                denkspur=denkspur,
                aeusserung=aeusserung,
                fehlversuche=fehlversuche,
            )
            budgetstand: Budgetstand = self._budgetstand_laden()
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
        """Behält den Abbruchschritt und schreibt den gescheiterten Status atomar (ADR-0061).

        Ein verfallener Antwortversuch hinterlässt weder Schritt noch Status
        (ADR-0066).
        """

        with transaction.atomic():
            self._antwortversuch_pruefen()
            self._abbruchschritt_ablegen(
                eingabe=eingabe, eingabemodus=eingabemodus, fehlversuche=fehlversuche
            )
            self.status_setzen(Sitzung.Status.GESCHEITERT)

    def diagnose_setzen(
        self, text: str, *, eingabemodus: str = Eingabemodus.GETIPPT
    ) -> bool:
        """Schließt die Sitzung ab und bewahrt die Diagnose, nur solange sie läuft."""

        with transaction.atomic():
            if not self.status_setzen(Sitzung.Status.ABGESCHLOSSEN):
                return False
            self._diagnose_ablegen(text, eingabemodus=eingabemodus)
        return True

    def status_setzen(self, status: Sitzung.Status) -> bool:
        """Vollzieht einen Statusübergang nur von `laufend` aus (ADR-0066).

        Ein verlorener Übergang überschreibt nichts; der Sink kennt danach den
        tatsächlichen Status.
        """

        gelungen: bool = (
            Sitzung.objects.filter(
                pk=self._sitzung.pk, status=Sitzung.Status.LAUFEND
            ).update(status=status)
            == 1
        )
        if gelungen:
            self._sitzung.status = status
        else:
            self._sitzung.refresh_from_db(fields=["status"])
        return gelungen

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

        self._uhr_stellen(lambda budgetstand: budgetstand.zug_beginnen(jetzt))

    def zug_beenden(self, jetzt: datetime) -> None:
        """Bucht die offene Spanne vor einem Modellaufruf."""

        self._uhr_stellen(lambda budgetstand: budgetstand.zug_beenden(jetzt))

    def _uhr_stellen(self, uebergang: Callable[[Budgetstand], None]) -> None:
        # Stellt die Uhr auf dem frisch gelesenen Stand der Sitzungszeile und
        # nur, solange die Sitzung läuft: Ein veraltetes Sitzungsobjekt einer
        # anderen Anfrage setzt so keine gebuchte Zeit zurück (ADR-0066).

        if not self._sitzung.vignette.uhr_laeuft:
            return
        with transaction.atomic():
            if not self._sitzungszeile_frisch_lesen():
                return
            budgetstand: Budgetstand = self._budgetstand_laden()
            uebergang(budgetstand)
            self._budgetstand_speichern(budgetstand)

    def _sitzungszeile_frisch_lesen(self) -> bool:
        # Liest Status und Uhr in der laufenden Transaktion neu und meldet, ob
        # die Sitzung noch läuft. Auf SQLite serialisiert schon das BEGIN
        # IMMEDIATE, die Sperre wirkt auf Backends mit `select_for_update`.

        self._sitzung.refresh_from_db(
            fields=["status", "verbrauchte_zeit", "offene_spanne_seit"],
            from_queryset=Sitzung.objects.select_for_update(),
        )
        return self._sitzung.status == Sitzung.Status.LAUFEND

    def _antwortversuch_pruefen(self) -> None:
        # Lässt den Antwortversuch verfallen, wenn die Sitzung nicht mehr läuft
        # oder ein anderer Schritt den Verlauf seit seinem Beginn verlängert hat.

        begonnen_bei: int | None = self._begonnen_bei
        self._begonnen_bei = None
        if not self._sitzungszeile_frisch_lesen():
            raise AntwortversuchVerfallen
        if begonnen_bei is not None and self._schrittzahl() != begonnen_bei:
            raise AntwortversuchVerfallen

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
    """Führt das Ablaufgerüst in der DB und die Inhalte im kurzlebigen Speicher.

    Die Senke der flüchtigen Teilnahme: Gesprächsschritte samt Fehlversuchen
    und die Diagnose liegen je Sitzung unter ihrem Primärschlüssel im
    kurzlebigen Speicher und erreichen die DB nie. Weil sie über die Sitzung
    gefunden werden, setzt die Sitzung in jedem Browser fort (ADR „Flüchtige
    Inhalte liegen in einem kurzlebigen Speicher“).
    """

    @classmethod
    def fuer_sitzung(cls, sitzung: Sitzung) -> "FluechtigerSink":
        """Stellt den Sink für eine laufende oder beendete Sitzung wieder her."""

        sink: FluechtigerSink = cls(sitzung.teilnahme)
        sink.sitzung = sitzung
        return sink

    def sitzung_starten(
        self,
        vignette: Vignette,
        simulationskern: Simulationskern,
        modell_konfiguration: ModellKonfiguration,
    ) -> None:
        """Legt die Sitzung in der DB und ihren leeren Verlauf im Speicher an."""

        super().sitzung_starten(vignette, simulationskern, modell_konfiguration)
        self._inhalt_speichern({"gespraechsschritte": []})

    @property
    def verlauf_fehlt(self) -> bool:
        """Meldet eine Sitzung, deren Inhalte abgelaufen sind."""

        return self._inhalt_laden() is None

    @property
    def gespraechsschritte(self) -> list[GespraechsschrittDaten]:
        """Liefert die vorgehaltenen Schritte dieser Sitzung."""

        return cast(
            list[GespraechsschrittDaten],
            (self._inhalt_laden() or {}).get("gespraechsschritte", []),
        )

    @property
    def abgegebene_diagnose(self) -> str | None:
        """Liefert die vorgehaltene Diagnose."""

        return cast(str | None, (self._inhalt_laden() or {}).get("diagnose"))

    def _geglueckten_schritt_ablegen(
        self,
        *,
        eingabe: str,
        eingabemodus: str,
        denkspur: str,
        aeusserung: str,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Hängt den geglückten Schritt an den vorgehaltenen Verlauf.

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
        # Hält den antwortlosen Schritt nur im vorgehaltenen Verlauf.

        self._schritt_anhaengen(eingabe, eingabemodus, None, None, fehlversuche)

    def _diagnose_ablegen(self, text: str, *, eingabemodus: str) -> None:
        # Hält die Diagnose im Speicher. Der Eingabemodus gehört zum Inhalt
        # und wird deshalb nicht festgehalten.

        inhalt: dict[str, Any] = self._inhalt_laden() or {"gespraechsschritte": []}
        inhalt["diagnose"] = text
        self._inhalt_speichern(inhalt)

    def _schritt_anhaengen(
        self,
        eingabe: str,
        eingabemodus: str,
        denkspur: str | None,
        aeusserung: str | None,
        fehlversuche: list[FehlversuchDaten],
    ) -> None:
        # Legt einen Schritt in der gemeinsamen Speicherform in den Speicher.
        # Die Transaktion der Aufruferin serialisiert konkurrierende Schritte.

        inhalt: dict[str, Any] = self._inhalt_laden() or {"gespraechsschritte": []}
        schritte: list[GespraechsschrittDaten] = inhalt["gespraechsschritte"]
        schritte.append(
            _schrittdaten(
                len(schritte) + 1,
                eingabe,
                eingabemodus,
                denkspur,
                aeusserung,
                fehlversuche,
            )
        )
        self._inhalt_speichern(inhalt)

    def _schrittzahl(self) -> int:
        # Zählt die vorgehaltenen Schritte statt der Zeilen der DB.

        return len(self.gespraechsschritte)

    def _inhalt_laden(self) -> dict[str, Any] | None:
        # Liest die Inhalte dieser Sitzung frisch; abgelaufene fehlen.

        return cast(
            dict[str, Any] | None,
            kurzlebiger_speicher.lesen(_fluechtiger_schluessel(self._sitzung.pk)),
        )

    def _inhalt_speichern(self, inhalt: dict[str, Any]) -> None:
        # Schreibt die Inhalte dieser Sitzung und verschiebt damit ihre Frist.

        kurzlebiger_speicher.schreiben(
            _fluechtiger_schluessel(self._sitzung.pk), inhalt
        )


def fluechtige_inhalte_vorhalten(teilnahme: Teilnahme) -> None:
    """Verschiebt die Frist der Inhalte aller Sitzungen einer flüchtigen Teilnahme.

    Jeder Zugriff der Teilnahme ruft sie; abgelaufene Inhalte bleiben
    abgelaufen.
    """

    if not teilnahme.ist_fluechtig:
        return
    for sitzung_pk in Sitzung.objects.filter(teilnahme=teilnahme).values_list(
        "pk", flat=True
    ):
        kurzlebiger_speicher.vorhalten(_fluechtiger_schluessel(sitzung_pk))


def _fluechtiger_schluessel(sitzung_pk: int) -> str:
    # Der Schlüssel der Inhalte einer flüchtigen Sitzung im Speicher.

    return f"sitzung-{sitzung_pk}"


def _schrittdaten(
    reihenfolge: int,
    eingabe: str,
    eingabemodus: str,
    denkspur: str | None,
    aeusserung: str | None,
    fehlversuche: list[FehlversuchDaten],
) -> GespraechsschrittDaten:
    # Baut die gemeinsame Speicherform von flüchtigem Sink und Probelauf.

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


def sink_fuer_teilnahme(teilnahme: Teilnahme) -> GeruestSink:
    """Wählt die Senke einer neuen Sitzung allein nach der Speicherung."""

    if teilnahme.ist_fluechtig:
        return FluechtigerSink(teilnahme)
    return DBSink(teilnahme)


def sink_fuer_sitzung(sitzung: Sitzung) -> GeruestSink:
    """Wählt die Senke einer bestehenden Sitzung allein nach der Speicherung."""

    if sitzung.teilnahme.ist_fluechtig:
        return FluechtigerSink.fuer_sitzung(sitzung)
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

    def antwortversuch_beginnen(self, jetzt: datetime) -> None:
        """Hält die Uhr an; der Probelauf hat nur einen Tab und nichts zu verwerfen."""

        self.zug_beenden(jetzt)

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
    ) -> bool:
        """Hält die im Probelauf verworfene Diagnose in der Session.

        Der Modus reist bis hierher, wird aber nicht festgehalten: Der
        Probelauf verwirft die Diagnose ohnehin (ADR-0014).
        """

        self._zustand["diagnose"] = text
        return self.status_setzen(Sitzung.Status.ABGESCHLOSSEN)

    def status_setzen(self, status: Sitzung.Status) -> bool:
        """Hält den Sitzungsstatus für den Probelauf fest."""

        self._zustand["status"] = status
        _session_als_geaendert_markieren(self.session)
        return True

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

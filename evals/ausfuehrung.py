"""Die Ausführung eines Evallaufs, die der Hintergrundprozess aufruft (ADR-0047)."""

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from simulation import (
    Antwortversuch,
    Ausfuehrung,
    ausgabe_versuchen,
    antwort_versuchen,
    vorlage_rendern,
)
from simulation.models import Evalinput, ModellKonfiguration
from simulation.sprachmodell import BEWERTER_SCHEMA, LEHRPERSON_SCHEMA

from .models import Evalgespraech, Evallauf, Kriterium, Urteil, Wechsel

ANTWORTVERSUCH_GESCHEITERT: str = "Antwortversuch gescheitert"
BEWERTER_OHNE_AUSGABE: str = "Der Bewerter lieferte keine auswertbare Ausgabe."
LEHRPERSON_OHNE_AUSGABE: str = (
    "Die simulierte Lehrperson lieferte keine Äußerung; das Gespräch endet davor."
)


class _Protokollzeile(NamedTuple):
    # Ein gespielter Wechsel: was die Lehrperson sagte, was die Schüler:in
    # dachte und was sie antwortete.

    lehrperson: str
    denkspur: str
    aeusserung: str


class _Eingabe(NamedTuple):
    # Was eine Rolle beurteilt oder befolgt, unter dem Platzhalter ihrer Vorlage.

    platzhalter: str
    text: str


def evallauf_ausfuehren(evallauf: Evallauf) -> None:
    """Spielt alle Evals des festgehaltenen Katalogs und beurteilt jedes Gespräch.

    Je Evalinput entstehen k Evalgespräche, je Inputschritt ein Wechsel (fest
    wörtlich, gelenkt von der simulierten Lehrperson formuliert), danach
    je Evalkriterium und übergreifendem Kriterium ein Urteil. Geschrieben wird
    sofort und in kurzen Schritten: Kein Modellaufruf hält eine
    Schreibtransaktion offen, und ein Abbruch lässt das Fertige stehen.
    """

    ausfuehrung: Ausfuehrung = Ausfuehrung()
    for eval_, kriterien in evallauf.evals_mit_kriterien():
        for evalinput in eval_.inputs.all():
            for wiederholung in range(1, evallauf.katalog.k + 1):
                _gespraech_fuehren(
                    evallauf, evalinput, wiederholung, kriterien, ausfuehrung
                )


def _gespraech_fuehren(
    evallauf: Evallauf,
    evalinput: Evalinput,
    wiederholung: int,
    kriterien: Sequence[Kriterium],
    ausfuehrung: Ausfuehrung,
) -> None:
    # Spielt eine Wiederholung Schritt für Schritt und lässt sie beurteilen.

    gespraech: Evalgespraech = Evalgespraech.objects.create(
        evallauf=evallauf, evalinput=evalinput, wiederholung=wiederholung
    )
    protokoll: list[_Protokollzeile] = []
    for position, schritt in enumerate(evalinput.schritte.all(), 1):
        verlauf: list[tuple[str, str]] = [
            (zeile.lehrperson, zeile.aeusserung) for zeile in protokoll
        ]
        lehrperson_aeusserung: str | None = (
            _lehrperson_fragen(evallauf, schritt.text, protokoll, ausfuehrung)
            if schritt.gelenkt
            else schritt.text
        )
        if lehrperson_aeusserung is None:
            _alle_beurteilen(gespraech, kriterien, None, LEHRPERSON_OHNE_AUSGABE)
            return
        versuch: Antwortversuch = antwort_versuchen(
            evallauf.platzhalter,
            evallauf.kern,
            evallauf.schuelerin_konfiguration,
            verlauf,
            lehrperson_aeusserung,
            ausfuehrung,
        )
        Wechsel.objects.create(
            gespraech=gespraech,
            position=position,
            lehrperson_aeusserung=lehrperson_aeusserung,
            denkspur=versuch.antwort.denkspur if versuch.antwort else "",
            aeusserung=versuch.antwort.aeusserung if versuch.antwort else None,
            fehlversuche=[
                {"grund": fehlversuch.grund, "rohantwort": fehlversuch.rohantwort}
                for fehlversuch in versuch.fehlversuche
            ],
        )
        if versuch.antwort is None:
            _alle_beurteilen(gespraech, kriterien, False, ANTWORTVERSUCH_GESCHEITERT)
            return
        protokoll.append(
            _Protokollzeile(
                lehrperson=lehrperson_aeusserung,
                denkspur=versuch.antwort.denkspur,
                aeusserung=versuch.antwort.aeusserung,
            )
        )
    verlauf_mit_denkspur: str = _verlauf_mit_denkspur(protokoll)
    for kriterium in kriterien:
        _beurteilen(evallauf, gespraech, kriterium, verlauf_mit_denkspur, ausfuehrung)


def _lehrperson_fragen(
    evallauf: Evallauf,
    inputstrategie: str,
    protokoll: Sequence[_Protokollzeile],
    ausfuehrung: Ausfuehrung,
) -> str | None:
    # Lässt die Lehrperson nach der Strategie formulieren, mit dem bisherigen
    # Verlauf ohne Denkspur; leer, wenn sie nach allen Versuchen nichts liefert.

    ausgabe: dict[str, object] | None = _rolle_fragen(
        evallauf,
        evallauf.katalog.lehrperson_vorlage,
        evallauf.lehrperson_konfiguration,
        LEHRPERSON_SCHEMA,
        _Eingabe("inputstrategie", inputstrategie),
        _verlauf_ohne_denkspur(protokoll),
        ausfuehrung,
    )
    return None if ausgabe is None else str(ausgabe["aeusserung"])


def _alle_beurteilen(
    gespraech: Evalgespraech,
    kriterien: Sequence[Kriterium],
    erfuellt: bool | None,
    begruendung: str,
) -> None:
    # Schreibt jedem Kriterium dasselbe Urteil, ohne den Bewerter zu fragen.

    for kriterium in kriterien:
        Urteil.objects.schreiben(gespraech, kriterium, erfuellt, begruendung)


def _beurteilen(
    evallauf: Evallauf,
    gespraech: Evalgespraech,
    kriterium: Kriterium,
    verlauf_mit_denkspur: str,
    ausfuehrung: Ausfuehrung,
) -> None:
    # Fragt den Bewerter nach einem Kriterium, mit dem Verlauf samt Denkspur.

    ausgabe: dict[str, object] | None = _rolle_fragen(
        evallauf,
        evallauf.katalog.bewerter_vorlage,
        evallauf.bewerter_konfiguration,
        BEWERTER_SCHEMA,
        _Eingabe("kriterium", kriterium.text),
        verlauf_mit_denkspur,
        ausfuehrung,
    )
    if ausgabe is None:
        Urteil.objects.schreiben(gespraech, kriterium, None, BEWERTER_OHNE_AUSGABE)
    else:
        Urteil.objects.schreiben(
            gespraech,
            kriterium,
            bool(ausgabe["erfuellt"]),
            str(ausgabe["begruendung"]),
        )


def _rolle_fragen(
    evallauf: Evallauf,
    vorlage: str,
    konfiguration: ModellKonfiguration,
    schema: Mapping[str, object],
    eingabe: _Eingabe,
    verlauf: str,
    ausfuehrung: Ausfuehrung,
) -> dict[str, object] | None:
    # Belegt Lehrperson und Bewerter gleich: Die gerenderte Vorlage ist der
    # System-Prompt und setzt die Eingabe unter ihrem Platzhalter
    # (`$inputstrategie` oder `$kriterium`) und den Verlauf über `$verlauf`
    # ein; der User-Prompt trägt noch einmal den Verlauf, die Eingabe ihren
    # Text. Eingesetzte Werte werden nicht selbst als Vorlage gerendert.
    # Leer, wenn nach allen Versuchen nichts Auswertbares kam.

    return ausgabe_versuchen(
        system_prompt=vorlage_rendern(
            vorlage,
            {
                **evallauf.platzhalter,
                eingabe.platzhalter: eingabe.text,
                "verlauf": verlauf,
            },
        ),
        user_prompt=verlauf,
        modell_konfiguration=konfiguration,
        verlauf=[],
        eingabe=eingabe.text,
        ausgabe_schema=schema,
        ausfuehrung=ausfuehrung,
    ).ausgabe


def _verlauf_ohne_denkspur(protokoll: Sequence[_Protokollzeile]) -> str:
    # Der Verlauf für die Lehrperson, je Wechsel nur die beiden Äußerungen.

    return "\n".join(
        f"<lehrperson>{zeile.lehrperson}</lehrperson>\n"
        f"<schuelerin>{zeile.aeusserung}</schuelerin>"
        for zeile in protokoll
    )


def _verlauf_mit_denkspur(protokoll: Sequence[_Protokollzeile]) -> str:
    # Der Verlauf für den Bewerter, je Wechsel Äußerung, Denkspur und Antwort.

    return "\n".join(
        f"<lehrperson>{zeile.lehrperson}</lehrperson>\n"
        f"<denkspur>{zeile.denkspur}</denkspur>\n"
        f"<schuelerin>{zeile.aeusserung}</schuelerin>"
        for zeile in protokoll
    )

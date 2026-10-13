"""Die Ausführung eines Evallaufs, die der Hintergrundprozess aufruft (ADR-0059)."""

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from simulation import (
    Antwortversuch,
    Ausgabeversuch,
    Ausfuehrung,
    Fehlversuch,
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
# Die Lehrperson eröffnet das Gespräch; ihr Verlauf beginnt deshalb mit dieser
# technischen user-Nachricht, damit jeder Anbieter eine gültige Anfrage erhält.
EINSTIEGSNACHRICHT: str = "Beginnen Sie das Gespräch."


class _Protokollzeile(NamedTuple):
    # Ein gespielter Wechsel: was die Lehrperson sagte, was die Schüler:in
    # dachte und was sie antwortete.

    lehrperson: str
    denkspur: str
    aeusserung: str


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
        lehrperson_aeusserung: str | None = schritt.text
        if schritt.gelenkt:
            lehrperson: Ausgabeversuch = _lehrperson_fragen(
                evallauf, schritt.text, protokoll, ausfuehrung
            )
            lehrperson_aeusserung = (
                str(lehrperson.ausgabe["aeusserung"]) if lehrperson.ausgabe else None
            )
            if lehrperson.fehlversuche:
                gespraech.lehrperson_fehlversuche.append(
                    {
                        "position": position,
                        "fehlversuche": _fehlversuche(lehrperson.fehlversuche),
                        "gescheitert": lehrperson.ausgabe is None,
                    }
                )
                gespraech.save(update_fields=["lehrperson_fehlversuche"])
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
            fehlversuche=_fehlversuche(versuch.fehlversuche),
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
) -> Ausgabeversuch:
    # Lässt die Lehrperson nach der Strategie formulieren, einschließlich
    # ihrer Fehlversuche. Sie führt das Gespräch nativ (ADR-0052): Auf die
    # Einstiegsnachricht und jede Äußerung der Schüler:in ohne Denkspur folgt
    # ihre eigene, auch die fester Schritte. `$verlauf` bleibt für
    # finalisierte Altvorlagen leer.

    an_lehrperson: list[str] = [
        EINSTIEGSNACHRICHT,
        *(zeile.aeusserung for zeile in protokoll),
    ]
    verlauf: list[tuple[str, str]] = list(
        zip(
            an_lehrperson[:-1],
            (zeile.lehrperson for zeile in protokoll),
            strict=True,
        )
    )
    return _rolle_fragen(
        evallauf,
        evallauf.katalog.lehrperson_vorlage,
        evallauf.lehrperson_konfiguration,
        LEHRPERSON_SCHEMA,
        {"inputstrategie": inputstrategie, "verlauf": ""},
        verlauf,
        an_lehrperson[-1],
        ausfuehrung,
    )


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

    versuch: Ausgabeversuch = _rolle_fragen(
        evallauf,
        evallauf.katalog.bewerter_vorlage,
        evallauf.bewerter_konfiguration,
        BEWERTER_SCHEMA,
        {"kriterium": kriterium.text, "verlauf": verlauf_mit_denkspur},
        [],
        kriterium.text,
        ausfuehrung,
    )
    ausgabe: dict[str, object] | None = versuch.ausgabe
    Urteil.objects.schreiben(
        gespraech,
        kriterium,
        bool(ausgabe["erfuellt"]) if ausgabe else None,
        str(ausgabe["begruendung"]) if ausgabe else BEWERTER_OHNE_AUSGABE,
        fehlversuche=_fehlversuche(versuch.fehlversuche),
    )


def _rolle_fragen(
    evallauf: Evallauf,
    vorlage: str,
    konfiguration: ModellKonfiguration,
    schema: Mapping[str, object],
    evalwerte: Mapping[str, str],
    verlauf: Sequence[tuple[str, str]],
    eingabe: str,
    ausfuehrung: Ausfuehrung,
) -> Ausgabeversuch:
    # Belegt Lehrperson und Bewerter gleich: Der System-Prompt ist die
    # gerenderte Vorlage mit den Evalwerten der Rolle, die letzte
    # `user`-Nachricht die Eingabe (ADR-0052). Eingesetzte Werte werden nicht
    # selbst als Vorlage gerendert. Der Ausgabeversuch erhält auch Fehler vor
    # einer gültigen Ausgabe.

    return ausgabe_versuchen(
        system_prompt=vorlage_rendern(vorlage, {**evallauf.platzhalter, **evalwerte}),
        modell_konfiguration=konfiguration,
        verlauf=verlauf,
        eingabe=eingabe,
        ausgabe_schema=schema,
        ausfuehrung=ausfuehrung,
    )


def _fehlversuche(fehlversuche: Sequence[Fehlversuch]) -> list[dict[str, str]]:
    # Die Fehler aller Rollen nutzen dieselbe gespeicherte Form.

    return [
        {"grund": fehlversuch.grund, "rohantwort": fehlversuch.rohantwort}
        for fehlversuch in fehlversuche
    ]


def _verlauf_mit_denkspur(protokoll: Sequence[_Protokollzeile]) -> str:
    # Der Verlauf für den Bewerter, je Wechsel Äußerung, Denkspur und Antwort.

    return "\n".join(
        f"<lehrperson>{zeile.lehrperson}</lehrperson>\n"
        f"<denkspur>{zeile.denkspur}</denkspur>\n"
        f"<schuelerin>{zeile.aeusserung}</schuelerin>"
        for zeile in protokoll
    )

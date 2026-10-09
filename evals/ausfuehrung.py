"""Die Ausführung eines Evallaufs, die der Hintergrundprozess aufruft (ADR-0047)."""

from collections.abc import Sequence

from simulation import (
    Antwortversuch,
    Ausfuehrung,
    Ausgabeversuch,
    ausgabe_versuchen,
    antwort_versuchen,
    vorlage_rendern,
)
from simulation.models import Evalinput, Evalkriterium, UebergreifendesKriterium
from simulation.sprachmodell import BEWERTER_SCHEMA

from .models import Evalgespraech, Evallauf, Urteil, Wechsel

ANTWORTVERSUCH_GESCHEITERT: str = "Antwortversuch gescheitert"
BEWERTER_OHNE_AUSGABE: str = "Der Bewerter lieferte keine auswertbare Ausgabe."
GELENKT_NOCH_NICHT: str = (
    "Gelenkte Inputschritte werden noch nicht ausgeführt; das Gespräch endet davor."
)

# Ein Kriterium als Feld des Urteils, das es bezeichnet.
type Urteilsziel = dict[str, Evalkriterium | UebergreifendesKriterium]


def evallauf_ausfuehren(evallauf: Evallauf) -> None:
    """Spielt alle Evals des festgehaltenen Katalogs und beurteilt jedes Gespräch.

    Je Evalinput entstehen k Evalgespräche, je Inputschritt ein Wechsel, danach
    je Evalkriterium und übergreifendem Kriterium ein Urteil. Geschrieben wird
    sofort und in kurzen Schritten: Kein Modellaufruf hält eine
    Schreibtransaktion offen, und ein Abbruch lässt das Fertige stehen.
    """

    ausfuehrung: Ausfuehrung = Ausfuehrung()
    katalog = evallauf.katalog
    uebergreifende: list[UebergreifendesKriterium] = list(
        katalog.uebergreifende_kriterien.all()
    )
    for eval_ in katalog.evals.prefetch_related("kriterien", "inputs__schritte"):
        ziele: list[Urteilsziel] = [
            {"evalkriterium": kriterium} for kriterium in eval_.kriterien.all()
        ] + [{"uebergreifendes_kriterium": kriterium} for kriterium in uebergreifende]
        for evalinput in eval_.inputs.all():
            for wiederholung in range(1, katalog.k + 1):
                _gespraech_fuehren(
                    evallauf, evalinput, wiederholung, ziele, ausfuehrung
                )


def _gespraech_fuehren(
    evallauf: Evallauf,
    evalinput: Evalinput,
    wiederholung: int,
    ziele: Sequence[Urteilsziel],
    ausfuehrung: Ausfuehrung,
) -> None:
    # Spielt eine Wiederholung Schritt für Schritt und lässt sie beurteilen.

    gespraech: Evalgespraech = Evalgespraech.objects.create(
        evallauf=evallauf, evalinput=evalinput, wiederholung=wiederholung
    )
    verlauf: list[tuple[str, str]] = []
    protokoll: list[tuple[str, str, str]] = []
    for position, schritt in enumerate(evalinput.schritte.all(), 1):
        if schritt.gelenkt:
            _alle_beurteilen(gespraech, ziele, None, GELENKT_NOCH_NICHT)
            return
        versuch: Antwortversuch = antwort_versuchen(
            evallauf.platzhalter,
            evallauf.kern,
            evallauf.schuelerin_konfiguration,
            verlauf,
            schritt.text,
            ausfuehrung,
        )
        Wechsel.objects.create(
            gespraech=gespraech,
            position=position,
            lehrperson_aeusserung=schritt.text,
            denkspur=versuch.antwort.denkspur if versuch.antwort else "",
            aeusserung=versuch.antwort.aeusserung if versuch.antwort else None,
            fehlversuche=[
                {"grund": fehlversuch.grund, "rohantwort": fehlversuch.rohantwort}
                for fehlversuch in versuch.fehlversuche
            ],
        )
        if versuch.antwort is None:
            _alle_beurteilen(gespraech, ziele, False, ANTWORTVERSUCH_GESCHEITERT)
            return
        verlauf.append((schritt.text, versuch.antwort.aeusserung))
        protokoll.append(
            (schritt.text, versuch.antwort.denkspur, versuch.antwort.aeusserung)
        )
    verlauf_mit_denkspur: str = _verlauf_mit_denkspur(protokoll)
    for ziel in ziele:
        _beurteilen(evallauf, gespraech, ziel, verlauf_mit_denkspur, ausfuehrung)


def _alle_beurteilen(
    gespraech: Evalgespraech,
    ziele: Sequence[Urteilsziel],
    erfuellt: bool | None,
    begruendung: str,
) -> None:
    # Schreibt jedem Kriterium dasselbe Urteil, ohne den Bewerter zu fragen.

    for ziel in ziele:
        Urteil.objects.create(
            gespraech=gespraech, erfuellt=erfuellt, begruendung=begruendung, **ziel
        )


def _beurteilen(
    evallauf: Evallauf,
    gespraech: Evalgespraech,
    ziel: Urteilsziel,
    verlauf_mit_denkspur: str,
    ausfuehrung: Ausfuehrung,
) -> None:
    # Fragt den Bewerter nach einem Kriterium. Die Anweisung steht allein in
    # der Bewerter-Vorlage; der User-Prompt trägt den Verlauf, die Eingabe das
    # Kriterium, beides als Daten.

    kriterium: str = next(iter(ziel.values())).text
    ausgabeversuch: Ausgabeversuch = ausgabe_versuchen(
        vorlage_rendern(
            evallauf.katalog.bewerter_vorlage,
            {
                **evallauf.platzhalter,
                "kriterium": kriterium,
                "verlauf": verlauf_mit_denkspur,
            },
        ),
        verlauf_mit_denkspur,
        evallauf.bewerter_konfiguration,
        [],
        kriterium,
        BEWERTER_SCHEMA,
        ausfuehrung,
    )
    ausgabe: dict[str, object] | None = ausgabeversuch.ausgabe
    Urteil.objects.create(
        gespraech=gespraech,
        erfuellt=None if ausgabe is None else bool(ausgabe["erfuellt"]),
        begruendung=(
            BEWERTER_OHNE_AUSGABE if ausgabe is None else str(ausgabe["begruendung"])
        ),
        **ziel,
    )


def _verlauf_mit_denkspur(protokoll: Sequence[tuple[str, str, str]]) -> str:
    # Der Verlauf für den Bewerter, je Wechsel Äußerung, Denkspur und Antwort.

    return "\n".join(
        f"<lehrperson>{lehrperson}</lehrperson>\n"
        f"<denkspur>{denkspur}</denkspur>\n"
        f"<schuelerin>{aeusserung}</schuelerin>"
        for lehrperson, denkspur, aeusserung in protokoll
    )

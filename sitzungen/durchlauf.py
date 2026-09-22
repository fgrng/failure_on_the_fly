"""Der Lauf einer Sitzung: ihr Ablauf über den Sink und ihre Darstellung."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from simulation import Antwortversuch, antwort_versuchen, vorlage_rendern
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Eingabemodus, Gespraechsschritt, Sitzung
from sitzungen.sink import FehlversuchDaten, GespraechsschrittDaten, SitzungSink
from vignetten.models import Vignette, rahmen_platzhalter


def _jetzt() -> datetime:
    """Liefert die Wanduhr für Übergänge des Budgetstands."""

    return timezone.now()


def sitzung_starten(
    sink: SitzungSink,
    vignette: Vignette,
    simulationskern: Simulationskern,
    modell_konfiguration: ModellKonfiguration,
) -> None:
    """Beginnt die Sitzung bei ihrem übergebenen Ziel."""

    sink.sitzung_starten(vignette, simulationskern, modell_konfiguration)


def modellverlauf(sink: SitzungSink) -> list[tuple[str, str]]:
    """Projiziert die bisherigen Schritte auf die beiden sichtbaren Gesprächsseiten.

    Die Denkspur bleibt draußen (ADR-0005), ebenso ein Schritt ohne Äußerung —
    der dokumentiert im Transkript den Abbruch, nicht den Kontext (ADR-0011).
    """

    verlauf: list[tuple[str, str]] = []
    for schritt in sink.gespraechsschritte:
        eingabe, aeusserung = _gespraechsseiten(schritt)
        if aeusserung is not None:
            verlauf.append((eingabe, aeusserung))
    return verlauf


def _gespraechsseiten(
    schritt: GespraechsschrittDaten | Gespraechsschritt,
) -> tuple[str, str | None]:
    # Liest beide Gesprächsseiten aus der Speicherform, in der ihr Sink sie hält.

    if isinstance(schritt, Mapping):
        return schritt["eingabe"], schritt["aeusserung"]
    return schritt.eingabe, schritt.aeusserung


class Ausgang(Enum):
    """Wie ein Gesprächsschritt endet und woran seine Aufruferin verzweigt."""

    FORTGESETZT = auto()
    GESCHEITERT = auto()
    BUDGET_ERSCHOEPFT = auto()


def gespraechsschritt_ausfuehren(
    sink: SitzungSink,
    vignette: Vignette,
    simulationskern: Simulationskern,
    modell_konfiguration: ModellKonfiguration,
    eingabe: str,
    eingabemodus: str = Eingabemodus.GETIPPT,
) -> Ausgang:
    """Führt den einen Gesprächsschritt aller drei Anlässe aus und meldet seinen Ausgang.

    Die Uhr steht still, solange das Modell antwortet (ADR-0012). Ob ein
    endgültig gescheiterter Schritt neben dem Transkript stehen bleibt
    (ADR-0011) und ob das erschöpfte Budget die Sitzung abschließt, entscheidet
    der Sink hinter der Naht — nicht dieser Ablauf.
    """

    sink.zug_beenden(_jetzt())
    antwortversuch: Antwortversuch = antwort_versuchen(
        vignette,
        simulationskern,
        modell_konfiguration,
        modellverlauf(sink),
        eingabe,
    )
    fehlversuche: list[FehlversuchDaten] = [
        {"grund": fehlversuch.grund, "rohantwort": fehlversuch.rohantwort}
        for fehlversuch in antwortversuch.fehlversuche
    ]
    if antwortversuch.antwort is None:
        sink.gescheiterten_schritt_behandeln(
            eingabe=eingabe,
            eingabemodus=eingabemodus,
            fehlversuche=fehlversuche,
        )
        return Ausgang.GESCHEITERT
    budget_erschoepft: bool = sink.gespraechsschritt_anhaengen(
        eingabe=eingabe,
        eingabemodus=eingabemodus,
        denkspur=antwortversuch.antwort.denkspur,
        aeusserung=antwortversuch.antwort.aeusserung,
        fehlversuche=fehlversuche,
    )
    if budget_erschoepft:
        # Die Uhr bleibt stehen: Nach dem Budget verfasst niemand mehr eine Eingabe.
        return Ausgang.BUDGET_ERSCHOEPFT
    return Ausgang.FORTGESETZT


def sitzung_beenden(sink: SitzungSink) -> None:
    """Hält die Uhr an und bereitet das Erreichen des Debriefs vor."""

    sink.zug_beenden(_jetzt())


def sitzung_abbrechen(sink: SitzungSink) -> None:
    """Hält die Uhr an und markiert die Sitzung als abgebrochen."""

    sink.zug_beenden(_jetzt())
    sink.status_setzen(Sitzung.Status.ABGEBROCHEN)


@dataclass(frozen=True)
class Sitzungsnavigation:
    """Die Routen und Bezeichnung einer angezeigten Sitzung."""

    bezeichnung: str
    gespraech_url: str
    beenden_url: str
    debrief_url: str
    abbrechen_url: str | None
    transkription_url: str


def _rahmen_rendern(vorlage: str, vignette: Vignette) -> str:
    # Füllt einen Abschnitt der Rahmenhandlung mit den Werten seiner Vignette.

    return vorlage_rendern(vorlage, rahmen_platzhalter(vignette))


def _ist_htmx(request: HttpRequest) -> bool:
    """Erkennt einen partiellen Seitenaufbau durch die vorhandene HTMX-Naht."""

    return request.headers.get("HX-Request") == "true"


def sitzung_anzeigen(
    request: HttpRequest,
    *,
    vignette: Vignette,
    kern: Simulationskern,
    gespraechsschritte: list[GespraechsschrittDaten] | QuerySet[Gespraechsschritt],
    ist_probelauf: bool,
    navigation: Sitzungsnavigation,
    erneute_eingabe: str | None = None,
    erneuter_eingabemodus: str = Eingabemodus.GETIPPT,
    ist_gescheitert: bool = False,
    zeigt_debrief: bool = False,
    ist_lesend: bool = False,
    spracheingabe_verfuegbar: bool = False,
    sitzung_pk: int | None = None,
    anhang: str | None = None,
) -> HttpResponse:
    """Rendert die ganze Sitzung oder nur ihre HTMX-Fortsetzung."""

    context: dict[str, object] = {
        "vignette": vignette,
        "einleitung": _rahmen_rendern(kern.rahmenhandlung_einleitung, vignette),
        "gespraechseinleitung": _rahmen_rendern(
            kern.rahmenhandlung_gespraechseinleitung, vignette
        ),
        "gespraechsschritte": gespraechsschritte,
        "ist_probelauf": ist_probelauf,
        "erneute_eingabe": erneute_eingabe,
        "erneuter_eingabemodus": erneuter_eingabemodus,
        "ist_gescheitert": ist_gescheitert,
        "debrief": _rahmen_rendern(kern.rahmenhandlung_debrief, vignette),
        "zeigt_debrief": zeigt_debrief,
        "ist_lesend": ist_lesend,
        "spracheingabe_verfuegbar": spracheingabe_verfuegbar,
        "aufnahme_maximale_bytes": settings.TRANSKRIPTION_MAX_AUFNAHME_BYTES,
        "navigation": navigation,
        "sitzung_pk": sitzung_pk,
        "anhang": anhang,
    }
    template: str = (
        "sitzungen/includes/sitzung_fortsetzung.html"
        if _ist_htmx(request)
        else "sitzungen/sitzung.html"
    )
    return render(request, template, context)

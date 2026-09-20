"""Der Lauf einer Sitzung: ihr Ablauf über den Sink und ihre Darstellung."""

from collections.abc import Mapping
from dataclasses import dataclass

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from simulation import Antwortversuch, antwort_versuchen, vorlage_rendern
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Gespraechsschritt, Sitzung
from sitzungen.sink import FehlversuchDaten, GespraechsschrittDaten, SitzungSink
from vignetten.models import Vignette, rahmen_platzhalter


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


def gespraechsschritt_ausfuehren(
    sink: SitzungSink,
    vignette: Vignette,
    simulationskern: Simulationskern,
    modell_konfiguration: ModellKonfiguration,
    eingabe: str,
) -> Antwortversuch:
    """Versucht eine Antwort und übergibt ihren Schritt ausschließlich dem Sink."""

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


def sitzung_beenden(sink: SitzungSink) -> None:
    """Hält die Uhr an und bereitet das Erreichen des Debriefs vor."""

    sink.zeitbudget_anhalten()


def sitzung_abbrechen(sink: SitzungSink) -> None:
    """Hält die Uhr an und markiert die Sitzung als abgebrochen."""

    sink.zeitbudget_anhalten()
    sink.status_setzen(Sitzung.Status.ABGEBROCHEN)


@dataclass(frozen=True)
class Sitzungsnavigation:
    """Die Routen und Bezeichnung einer angezeigten Sitzung."""

    bezeichnung: str
    gespraech_url: str
    beenden_url: str
    debrief_url: str
    abbrechen_url: str | None


def _sitzungsnavigation(ist_probelauf: bool) -> Sitzungsnavigation:
    # Bündelt die modusspezifischen Routen für die gemeinsame Sitzungsansicht.

    if ist_probelauf:
        return Sitzungsnavigation(
            bezeichnung="Probelauf",
            gespraech_url=reverse("sitzungen:probelauf_gespraech"),
            beenden_url=reverse("sitzungen:probelauf_beenden"),
            debrief_url=reverse("sitzungen:probelauf_debrief"),
            abbrechen_url=None,
        )
    return Sitzungsnavigation(
        bezeichnung="Training",
        gespraech_url=reverse("sitzungen:training_gespraech"),
        beenden_url=reverse("sitzungen:training_beenden"),
        debrief_url=reverse("sitzungen:training_debrief"),
        abbrechen_url=reverse("sitzungen:training_abbrechen"),
    )


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
    erneute_eingabe: str | None = None,
    ist_gescheitert: bool = False,
    zeigt_debrief: bool = False,
    ist_lesend: bool = False,
    spracheingabe_verfuegbar: bool = False,
    navigation: Sitzungsnavigation | None = None,
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
        "ist_gescheitert": ist_gescheitert,
        "debrief": _rahmen_rendern(kern.rahmenhandlung_debrief, vignette),
        "zeigt_debrief": zeigt_debrief,
        "ist_lesend": ist_lesend,
        "spracheingabe_verfuegbar": spracheingabe_verfuegbar,
        "navigation": navigation or _sitzungsnavigation(ist_probelauf),
        "sitzung_pk": sitzung_pk,
        "anhang": anhang,
    }
    template: str = (
        "sitzungen/includes/sitzung_fortsetzung.html"
        if _ist_htmx(request)
        else "sitzungen/sitzung.html"
    )
    return render(request, template, context)

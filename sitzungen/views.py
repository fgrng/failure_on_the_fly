"""Schreibfreie Views für den Probelauf einer Autorin."""

from string import Template
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from simulation import render as simulation_render
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.orchestrierung import gespraechsschritt_ausfuehren, sitzung_starten
from sitzungen.sink import GespraechsschrittDaten, ScratchSink
from vignetten.models import Vignette, Vignettenhistorie, rahmen_platzhalter

if TYPE_CHECKING:
    from konten.models import Konto


def _eigene_entwuerfe(konto: "Konto") -> QuerySet[Vignette]:
    """Liefert die Entwürfe aus dem Eigentümer-Kreis eines Kontos."""

    return Vignette.objects.filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(konto),
        zustand=Vignette.Zustand.ENTWURF,
    )


def _rahmen_rendern(vorlage: str, vignette: Vignette) -> str:
    """Übergibt dem strikten Renderer nur die benutzten Rahmenplatzhalter."""

    platzhalter: dict[str, str] = rahmen_platzhalter(vignette)
    namen: list[str] = Template(vorlage).get_identifiers()
    return simulation_render(vorlage, {name: platzhalter[name] for name in namen})


def _gespraech_anzeigen(
    request: HttpRequest,
    schritte: list[GespraechsschrittDaten],
) -> HttpResponse:
    """Rendert das Diagnosegespräch mit seinem bisherigen Verlauf."""

    return render(
        request,
        "sitzungen/probelauf_gespraech.html",
        {"gespraechsschritte": schritte},
    )


@login_required
def probelauf_auswahl(request: HttpRequest) -> HttpResponse:
    """Zeigt einer Autorin ausschließlich ihre wählbaren Vignettenentwürfe."""

    entwuerfe: QuerySet[Vignette] = _eigene_entwuerfe(request.user).select_related(
        "historie"
    )
    return render(request, "sitzungen/probelauf_auswahl.html", {"entwuerfe": entwuerfe})


@login_required
def probelauf_starten(request: HttpRequest, pk: int) -> HttpResponse:
    """Fixiert das Autorinnen-Tripel in der Session und zeigt die Einleitung."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    vignette: Vignette = get_object_or_404(
        _eigene_entwuerfe(request.user).select_related("gepinnter_kern"),
        pk=pk,
    )
    kern: Simulationskern | None = vignette.gepinnter_kern
    if kern is None:
        raise RuntimeError("Probeläufe brauchen einen gepinnten Simulationskern.")
    modell_konfiguration: ModellKonfiguration = ModellKonfiguration.objects.aktive()
    sitzung_starten(ScratchSink(request.session), vignette, kern, modell_konfiguration)
    return render(
        request,
        "sitzungen/probelauf_einleitung.html",
        {"einleitung": _rahmen_rendern(kern.rahmenhandlung_einleitung, vignette)},
    )


@login_required
def probelauf_gespraech(request: HttpRequest) -> HttpResponse:
    """Führt einen schreibfreien Gesprächsschritt des Probelaufs aus."""

    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    sink: ScratchSink = ScratchSink(request.session)
    schritte: list[GespraechsschrittDaten] = sink.gespraechsschritte
    if request.method == "GET":
        return _gespraech_anzeigen(request, schritte)
    if sink.ist_gescheitert:
        return _gespraech_anzeigen(request, schritte)
    vignette: Vignette = get_object_or_404(
        _eigene_entwuerfe(request.user), pk=sink.vignette_pk
    )
    kern: Simulationskern = get_object_or_404(
        Simulationskern.objects.all(), pk=sink.kern_pk
    )
    modell_konfiguration: ModellKonfiguration = get_object_or_404(
        ModellKonfiguration.objects.all(), pk=sink.modell_konfiguration_pk
    )
    eingabe: str = request.POST["eingabe"]
    gespraechsschritt_ausfuehren(
        sink,
        vignette,
        kern,
        modell_konfiguration,
        [
            schritt["aeusserung"]
            for schritt in schritte
            if schritt["aeusserung"] is not None
        ],
        eingabe,
    )
    return _gespraech_anzeigen(request, schritte)


@login_required
def probelauf_beenden(request: HttpRequest) -> HttpResponse:
    """Zeigt den Debrief des schreibfreien Probelaufs."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sink: ScratchSink = ScratchSink(request.session)
    vignette: Vignette = get_object_or_404(
        _eigene_entwuerfe(request.user), pk=sink.vignette_pk
    )
    kern: Simulationskern = get_object_or_404(
        Simulationskern.objects.all(), pk=sink.kern_pk
    )
    return render(
        request,
        "sitzungen/probelauf_debrief.html",
        {"debrief": _rahmen_rendern(kern.rahmenhandlung_debrief, vignette)},
    )


@login_required
def probelauf_debrief(request: HttpRequest) -> HttpResponse:
    """Verwirft den Probelauf samt eingegebener Diagnose."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    ScratchSink(request.session).verwerfen()
    return redirect("sitzungen:probelauf_auswahl")

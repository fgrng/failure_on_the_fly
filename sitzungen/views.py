"""Schreibfreie Views für den Probelauf einer Autorin."""

from string import Template

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render

from simulation import render as simulation_render
from simulation.models import ModellKonfiguration
from vignetten.models import Vignette, Vignettenhistorie, rahmen_platzhalter


def _rahmen_rendern(vorlage: str, vignette: Vignette) -> str:
    """Übergibt dem strikten Renderer nur die benutzten Rahmenplatzhalter."""

    platzhalter: dict[str, str] = rahmen_platzhalter(vignette)
    namen: list[str] = Template(vorlage).get_identifiers()
    return simulation_render(vorlage, {name: platzhalter[name] for name in namen})


@login_required
def probelauf_auswahl(request: HttpRequest) -> HttpResponse:
    """Zeigt einer Autorin ausschließlich ihre wählbaren Vignettenentwürfe."""

    entwuerfe = Vignette.objects.filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user),
        zustand=Vignette.Zustand.ENTWURF,
    ).select_related("historie")
    return render(request, "sitzungen/probelauf_auswahl.html", {"entwuerfe": entwuerfe})


@login_required
def probelauf_starten(request: HttpRequest, pk: int) -> HttpResponse:
    """Fixiert das Autorinnen-Tripel in der Session und zeigt die Einleitung."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    vignette: Vignette = get_object_or_404(
        Vignette.objects.select_related("gepinnter_kern").filter(
            historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user),
            zustand=Vignette.Zustand.ENTWURF,
        ),
        pk=pk,
    )
    kern = vignette.gepinnter_kern
    if kern is None:
        raise RuntimeError("Probeläufe brauchen einen gepinnten Simulationskern.")
    modell_konfiguration: ModellKonfiguration = ModellKonfiguration.objects.aktive()
    request.session["probelauf"] = {
        "vignette_pk": vignette.pk,
        "kern_pk": kern.pk,
        "modell_konfiguration_pk": modell_konfiguration.pk,
        "gespraechsschritte": [],
    }
    return render(
        request,
        "sitzungen/probelauf_einleitung.html",
        {"einleitung": _rahmen_rendern(kern.rahmenhandlung_einleitung, vignette)},
    )

"""Schreibfreie Views für den Probelauf einer Autorin."""

from string import Template
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render

from simulation import render as simulation_render
from simulation.models import ModellKonfiguration, Simulationskern
from vignetten.models import Vignette, Vignettenhistorie, rahmen_platzhalter

if TYPE_CHECKING:
    from konten.models import Konto


_PROBELAUF_SESSION_SCHLUESSEL: str = "probelauf"


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
    request.session[_PROBELAUF_SESSION_SCHLUESSEL] = {
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

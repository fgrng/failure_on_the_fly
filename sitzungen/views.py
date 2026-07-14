"""Schreibfreie Views für den Probelauf."""

from string import Template
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render

from simulation import antwort_versuchen, render as simulation_render
from simulation.models import ModellKonfiguration, Simulationskern
from vignetten.models import Vignette, Vignettenhistorie, rahmen_platzhalter

if TYPE_CHECKING:
    from konten.models import Konto


_PROBELAUF_SESSION_SCHLUESSEL: str = "probelauf"


class _Gespraechsschritt(TypedDict):
    """Ein erfolgreicher, nur in der Session gehaltener Gesprächsschritt."""

    eingabe: str
    denkspur: str
    aeusserung: str
    native_reasoning_spur: str | None


class _ProbelaufSession(TypedDict):
    """Der schreibfreie Probelaufzustand in der Django-Session."""

    vignette_pk: int
    kern_pk: int
    modell_konfiguration_pk: int
    gespraechsschritte: list[_Gespraechsschritt]
    freie_auswahl: NotRequired[bool]


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


def _probelauf_aus_session(request: HttpRequest) -> _ProbelaufSession:
    """Liest den beim Probelaufstart festgelegten Session-Zustand."""

    return cast(
        _ProbelaufSession,
        request.session[_PROBELAUF_SESSION_SCHLUESSEL],
    )


def _ist_administratorin(konto: "Konto") -> bool:
    """Prüft die administrative Rolle über ihre Django-Group."""

    return konto.groups.filter(name="Administrator:in").exists()


def _admin_erforderlich(request: HttpRequest) -> HttpResponse | None:
    """Schützt den freien Auswähler vor Konten ohne Administratorinnen-Rolle."""

    if not _ist_administratorin(request.user):
        return HttpResponse(status=403)
    return None


def _gespraech_anzeigen(
    request: HttpRequest,
    schritte: list[_Gespraechsschritt],
) -> HttpResponse:
    """Rendert das Diagnosegespräch mit seinem bisherigen Verlauf."""

    return render(
        request,
        "sitzungen/probelauf_gespraech.html",
        {"gespraechsschritte": schritte},
    )


def _probelauf_starten(
    request: HttpRequest,
    vignette: Vignette,
    kern: Simulationskern,
    modell_konfiguration: ModellKonfiguration,
    *,
    freie_auswahl: bool = False,
) -> HttpResponse:
    """Hält das gewählte Tripel schreibfrei fest und zeigt seine Einleitung."""

    probelauf: _ProbelaufSession = {
        "vignette_pk": vignette.pk,
        "kern_pk": kern.pk,
        "modell_konfiguration_pk": modell_konfiguration.pk,
        "gespraechsschritte": [],
    }
    if freie_auswahl:
        probelauf["freie_auswahl"] = True
    request.session[_PROBELAUF_SESSION_SCHLUESSEL] = probelauf
    return render(
        request,
        "sitzungen/probelauf_einleitung.html",
        {"einleitung": _rahmen_rendern(kern.rahmenhandlung_einleitung, vignette)},
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
    return _probelauf_starten(request, vignette, kern, modell_konfiguration)


@login_required
def administratorin_probelauf_auswahl(request: HttpRequest) -> HttpResponse:
    """Zeigt Administrator:innen alle frei kombinierbaren Tripelbestandteile."""

    verweigert: HttpResponse | None = _admin_erforderlich(request)
    if verweigert is not None:
        return verweigert
    return render(
        request,
        "sitzungen/administratorin_probelauf_auswahl.html",
        {
            "kerne": Simulationskern.objects.all(),
            "modell_konfigurationen": ModellKonfiguration.objects.all(),
            "vignetten": Vignette.objects.einbindbar(),
        },
    )


@login_required
def administratorin_probelauf_starten(request: HttpRequest) -> HttpResponse:
    """Fixiert ein administrativ gewähltes Tripel in der Session."""

    verweigert: HttpResponse | None = _admin_erforderlich(request)
    if verweigert is not None:
        return verweigert
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    kern: Simulationskern = get_object_or_404(
        Simulationskern.objects.all(), pk=request.POST["kern_pk"]
    )
    modell_konfiguration: ModellKonfiguration = get_object_or_404(
        ModellKonfiguration.objects.all(), pk=request.POST["modell_konfiguration_pk"]
    )
    vignette: Vignette = get_object_or_404(
        Vignette.objects.einbindbar(), pk=request.POST["vignette_pk"]
    )
    return _probelauf_starten(
        request,
        vignette,
        kern,
        modell_konfiguration,
        freie_auswahl=True,
    )


@login_required
def probelauf_gespraech(request: HttpRequest) -> HttpResponse:
    """Führt einen schreibfreien Gesprächsschritt des Probelaufs aus."""

    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    probelauf: _ProbelaufSession = _probelauf_aus_session(request)
    schritte: list[_Gespraechsschritt] = probelauf["gespraechsschritte"]
    if request.method == "GET":
        return _gespraech_anzeigen(request, schritte)
    vignetten: QuerySet[Vignette] = (
        Vignette.objects.einbindbar()
        if probelauf.get("freie_auswahl")
        else _eigene_entwuerfe(request.user)
    )
    vignette: Vignette = get_object_or_404(vignetten, pk=probelauf["vignette_pk"])
    kern: Simulationskern = get_object_or_404(
        Simulationskern.objects.all(), pk=probelauf["kern_pk"]
    )
    modell_konfiguration: ModellKonfiguration = get_object_or_404(
        ModellKonfiguration.objects.all(), pk=probelauf["modell_konfiguration_pk"]
    )
    eingabe: str = request.POST["eingabe"]
    antwortversuch = antwort_versuchen(
        vignette,
        kern,
        modell_konfiguration,
        [schritt["aeusserung"] for schritt in schritte],
        eingabe,
    )
    if antwortversuch.antwort is not None:
        schritte.append(
            {
                "eingabe": eingabe,
                "denkspur": antwortversuch.antwort.denkspur,
                "aeusserung": antwortversuch.antwort.aeusserung,
                "native_reasoning_spur": antwortversuch.native_reasoning_spur,
            }
        )
        request.session.modified = True
    return _gespraech_anzeigen(request, schritte)

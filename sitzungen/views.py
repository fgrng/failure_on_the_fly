"""Schreibfreie Views für den Probelauf."""

from typing import TYPE_CHECKING
from time import monotonic

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Gespraechsschritt, Sitzung
from sitzungen.orchestrierung import gespraechsschritt_ausfuehren, sitzung_starten
from sitzungen.rahmen import rahmen_rendern
from sitzungen.sink import DBSink, GespraechsschrittDaten, ScratchSink
from vignetten.models import Vignette, Vignettenhistorie

if TYPE_CHECKING:
    from konten.models import Konto


_ADMINISTRATORIN_GRUPPE: str = "Administrator:in"
_TRAINING_VERBRAUCHTE_ZEIT_SCHLUESSEL: str = "training_verbrauchte_zeit"
_TRAINING_ZEIT_LAEUFT_SEIT_SCHLUESSEL: str = "training_zeit_laeuft_seit"


def _eigene_entwuerfe(konto: "Konto") -> QuerySet[Vignette]:
    """Liefert die Entwürfe aus dem Eigentümer-Kreis eines Kontos."""

    return Vignette.objects.filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(konto),
        zustand=Vignette.Zustand.ENTWURF,
    )


def _ist_administratorin(konto: "Konto") -> bool:
    # Prüft die administrative Rolle über ihre Django-Group.

    return konto.groups.filter(name=_ADMINISTRATORIN_GRUPPE).exists()


def _administratorin_erforderlich(request: HttpRequest) -> HttpResponse | None:
    # Schützt den freien Auswähler vor Konten ohne Administratorinnen-Rolle.

    if not _ist_administratorin(request.user):
        return HttpResponse(status=403)
    return None


def _probelauf_vignetten(
    konto: "Konto", sink: ScratchSink
) -> QuerySet[Vignette]:
    """Begrenzt Vignetten passend zum gewählten Probelauf-Einstieg."""

    if sink.freie_auswahl:
        return Vignette.objects.einbindbar()
    return _eigene_entwuerfe(konto)


def _probelauf_vignette_und_kern(
    request: HttpRequest, sink: ScratchSink
) -> tuple[Vignette, Simulationskern]:
    """Lädt die im Probelauf gepinnten und weiterhin zugänglichen Bestandteile."""

    vignette: Vignette = get_object_or_404(
        _probelauf_vignetten(request.user, sink), pk=sink.vignette_pk
    )
    kern: Simulationskern = get_object_or_404(
        Simulationskern.objects.all(), pk=sink.kern_pk
    )
    return vignette, kern


def _gespraech_anzeigen(
    request: HttpRequest,
    schritte: list[GespraechsschrittDaten],
    erneute_eingabe: str | None = None,
) -> HttpResponse:
    """Rendert das Diagnosegespräch mit seinem bisherigen Verlauf."""

    return render(
        request,
        "sitzungen/probelauf_gespraech.html",
        {"gespraechsschritte": schritte, "erneute_eingabe": erneute_eingabe},
    )


def _debrief_anzeigen(
    request: HttpRequest,
    vignette: Vignette,
    kern: Simulationskern,
    schritte: list[GespraechsschrittDaten],
) -> HttpResponse:
    """Rendert den Debrief nach dem Ende des Diagnosegesprächs."""

    return render(
        request,
        "sitzungen/probelauf_debrief.html",
        {
            "debrief": rahmen_rendern(kern.rahmenhandlung_debrief, vignette),
            "gespraechsschritte": schritte,
        },
    )


def _gespeicherten_debrief_anzeigen(
    request: HttpRequest, sink: ScratchSink
) -> HttpResponse:
    """Rendert den Debrief aus dem festgehaltenen Probelaufzustand."""

    vignette, kern = _probelauf_vignette_und_kern(request, sink)
    return _debrief_anzeigen(request, vignette, kern, sink.gespraechsschritte)


def _probelauf_starten(
    request: HttpRequest,
    vignette: Vignette,
    kern: Simulationskern,
    modell_konfiguration: ModellKonfiguration,
    *,
    freie_auswahl: bool = False,
) -> HttpResponse:
    # Hält das gewählte Tripel schreibfrei fest und zeigt seine Einleitung.

    sink: ScratchSink = ScratchSink(request.session)
    sitzung_starten(sink, vignette, kern, modell_konfiguration)
    if freie_auswahl:
        sink.freie_auswahl_setzen()
    return render(
        request,
        "sitzungen/probelauf_einleitung.html",
        {"einleitung": rahmen_rendern(kern.rahmenhandlung_einleitung, vignette)},
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

    verweigert: HttpResponse | None = _administratorin_erforderlich(request)
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

    verweigert: HttpResponse | None = _administratorin_erforderlich(request)
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
    sink: ScratchSink = ScratchSink(request.session)
    schritte: list[GespraechsschrittDaten] = sink.gespraechsschritte
    if sink.ist_beendet:
        return _gespeicherten_debrief_anzeigen(request, sink)
    if request.method == "GET":
        sink.zeitbudget_fortsetzen()
        return _gespraech_anzeigen(request, schritte)
    if sink.ist_gescheitert:
        return _gespraech_anzeigen(request, schritte)
    vignette, kern = _probelauf_vignette_und_kern(request, sink)
    modell_konfiguration: ModellKonfiguration = get_object_or_404(
        ModellKonfiguration.objects.all(), pk=sink.modell_konfiguration_pk
    )
    eingabe: str = request.POST["eingabe"]
    sink.zeitbudget_anhalten()
    antwortversuch = gespraechsschritt_ausfuehren(
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
    if antwortversuch.endgueltig_gescheitert:
        sink.gescheiterten_schritt_verwerfen()
        sink.zeitbudget_fortsetzen()
        return _gespraech_anzeigen(request, schritte, eingabe)
    if sink.budget_erschoepft(vignette):
        sink.status_setzen(Sitzung.Status.ABGESCHLOSSEN)
        return _debrief_anzeigen(request, vignette, kern, schritte)
    sink.zeitbudget_fortsetzen()
    return _gespraech_anzeigen(request, schritte)


@login_required
def probelauf_beenden(request: HttpRequest) -> HttpResponse:
    """Zeigt den Debrief des schreibfreien Probelaufs."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sink: ScratchSink = ScratchSink(request.session)
    sink.status_setzen(Sitzung.Status.ABGESCHLOSSEN)
    return _gespeicherten_debrief_anzeigen(request, sink)


@login_required
def probelauf_debrief(request: HttpRequest) -> HttpResponse:
    """Verwirft den Probelauf samt eingegebener Diagnose."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sink: ScratchSink = ScratchSink(request.session)
    ziel: str = (
        "sitzungen:administratorin_probelauf_auswahl"
        if sink.freie_auswahl
        else "sitzungen:probelauf_auswahl"
    )
    sink.verwerfen()
    return redirect(ziel)


def _training_sitzung(request: HttpRequest) -> Sitzung:
    """Lädt die aktuelle Sitzung nur für das zugehörige Trainingskonto."""

    from training.models import Trainingsbindung

    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme"),
        pk=request.session["training_sitzung_pk"],
    )
    get_object_or_404(
        Trainingsbindung.objects.filter(konto=request.user), teilnahme=sitzung.teilnahme
    )
    return sitzung


def _training_schritte(sitzung: Sitzung) -> QuerySet[Gespraechsschritt]:
    """Liefert den sichtbaren Verlauf in seiner gespeicherten Reihenfolge."""

    return sitzung.gespraechsschritt_set.order_by("reihenfolge")


def _training_zeitbudget_fortsetzen(request: HttpRequest, sitzung: Sitzung) -> None:
    """Startet die unsichtbare Uhr ausschließlich während des Teilnehmer:innenzugs."""

    if (
        sitzung.vignette.budget_typ == Vignette.BudgetTyp.ZEIT
        and _TRAINING_ZEIT_LAEUFT_SEIT_SCHLUESSEL not in request.session
    ):
        request.session[_TRAINING_ZEIT_LAEUFT_SEIT_SCHLUESSEL] = monotonic()


def _training_zeitbudget_anhalten(request: HttpRequest) -> None:
    """Hält die Uhr vor Modellaufruf und schreibt die verbrauchte Zeit fort."""

    startzeit: float | None = request.session.pop(
        _TRAINING_ZEIT_LAEUFT_SEIT_SCHLUESSEL, None
    )
    if startzeit is not None:
        request.session[_TRAINING_VERBRAUCHTE_ZEIT_SCHLUESSEL] = (
            request.session.get(_TRAINING_VERBRAUCHTE_ZEIT_SCHLUESSEL, 0.0)
            + monotonic()
            - startzeit
        )


def _training_budget_erschoepft(request: HttpRequest, sitzung: Sitzung) -> bool:
    """Prüft das unsichtbare Gesprächsbudget nach einem vollständigen Schritt."""

    if sitzung.vignette.budget_wert is None:
        return False
    if sitzung.vignette.budget_typ == Vignette.BudgetTyp.SCHRITTE:
        return _training_schritte(sitzung).count() >= sitzung.vignette.budget_wert
    return (
        request.session.get(_TRAINING_VERBRAUCHTE_ZEIT_SCHLUESSEL, 0.0)
        >= sitzung.vignette.budget_wert
    )


def _training_debrief_anzeigen(request: HttpRequest, sitzung: Sitzung) -> HttpResponse:
    """Rendert den Debrief einer persistierten Trainingssitzung."""

    return render(
        request,
        "sitzungen/training_debrief.html",
        {
            "debrief": rahmen_rendern(
                sitzung.simulationskern.rahmenhandlung_debrief, sitzung.vignette
            ),
            "gespraechsschritte": _training_schritte(sitzung),
        },
    )


@login_required
def training_gespraech(request: HttpRequest) -> HttpResponse:
    """Führt den nächsten persistierten Gesprächsschritt einer Trainingssitzung aus."""

    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    sitzung: Sitzung = _training_sitzung(request)
    if sitzung.status == Sitzung.Status.ABGESCHLOSSEN:
        return _training_debrief_anzeigen(request, sitzung)
    schritte: QuerySet[Gespraechsschritt] = _training_schritte(sitzung)
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return render(
            request,
            "sitzungen/training_gespraech.html",
            {"gespraechsschritte": schritte, "ist_gescheitert": True},
        )
    if request.method == "GET":
        _training_zeitbudget_fortsetzen(request, sitzung)
        return render(
            request,
            "sitzungen/training_gespraech.html",
            {"gespraechsschritte": schritte},
        )
    _training_zeitbudget_anhalten(request)
    sink: DBSink = DBSink.fuer_sitzung(sitzung)
    antwortversuch = gespraechsschritt_ausfuehren(
        sink,
        sitzung.vignette,
        sitzung.simulationskern,
        sitzung.modell_konfiguration,
        list(schritte.exclude(aeusserung__isnull=True).values_list("aeusserung", flat=True)),
        request.POST["eingabe"],
    )
    if antwortversuch.endgueltig_gescheitert:
        return render(
            request,
            "sitzungen/training_gespraech.html",
            {"gespraechsschritte": _training_schritte(sitzung), "ist_gescheitert": True},
        )
    if _training_budget_erschoepft(request, sitzung):
        sink.status_setzen(Sitzung.Status.ABGESCHLOSSEN)
        return _training_debrief_anzeigen(request, sitzung)
    _training_zeitbudget_fortsetzen(request, sitzung)
    return render(
        request,
        "sitzungen/training_gespraech.html",
        {"gespraechsschritte": _training_schritte(sitzung)},
    )


@login_required
def training_beenden(request: HttpRequest) -> HttpResponse:
    """Beendet das Diagnosegespräch vorzeitig und zeigt seinen Debrief."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = _training_sitzung(request)
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return render(
            request,
            "sitzungen/training_gespraech.html",
            {"gespraechsschritte": _training_schritte(sitzung), "ist_gescheitert": True},
        )
    _training_zeitbudget_anhalten(request)
    DBSink.fuer_sitzung(sitzung).status_setzen(Sitzung.Status.ABGESCHLOSSEN)
    return _training_debrief_anzeigen(request, sitzung)


@login_required
def training_debrief(request: HttpRequest) -> HttpResponse:
    """Speichert die Diagnose und kehrt zur freien Trainingswahl zurück."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = _training_sitzung(request)
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return render(
            request,
            "sitzungen/training_gespraech.html",
            {"gespraechsschritte": _training_schritte(sitzung), "ist_gescheitert": True},
        )
    DBSink.fuer_sitzung(sitzung).diagnose_setzen(request.POST["diagnose"])
    from training.models import Trainingsbindung

    training_pk: int = get_object_or_404(
        Trainingsbindung, teilnahme=sitzung.teilnahme
    ).training_id
    request.session.pop("training_sitzung_pk", None)
    return redirect("training:detail", pk=training_pk)

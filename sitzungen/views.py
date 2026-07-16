"""Views für Probeläufe und persistierte Trainingssitzungen."""

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from simulation.models import ModellKonfiguration, Simulationskern
from simulation.transkription import (
    AnbieterNichtErreichbar,
    LeeresTranskript,
    Transkription,
    TranskriptionsAnbieterfehler,
)
from sitzungen.models import Gespraechsschritt, Sitzung
from sitzungen.orchestrierung import gespraechsschritt_ausfuehren, sitzung_starten
from sitzungen.rahmen import rahmen_rendern
from sitzungen.sink import DBSink, GespraechsschrittDaten, ScratchSink
from vignetten.models import Vignette, Vignettenhistorie

if TYPE_CHECKING:
    from konten.models import Konto


_ADMINISTRATORIN_GRUPPE: str = "Administrator:in"


@dataclass(frozen=True)
class Sitzungsnavigation:
    """Die Routen und Bezeichnung einer angezeigten Sitzung."""

    bezeichnung: str
    gespraech_url: str
    beenden_url: str
    debrief_url: str
    abbrechen_url: str | None


def _ist_htmx(request: HttpRequest) -> bool:
    """Erkennt einen partiellen Seitenaufbau durch die vorhandene HTMX-Naht."""

    return request.headers.get("HX-Request") == "true"


def sitzungsnavigation(ist_probelauf: bool) -> Sitzungsnavigation:
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


def _sitzung_anzeigen(
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
) -> HttpResponse:
    """Rendert die ganze Sitzung oder nur ihre HTMX-Fortsetzung."""

    context: dict[str, object] = {
        "vignette": vignette,
        "einleitung": rahmen_rendern(kern.rahmenhandlung_einleitung, vignette),
        "gespraechseinleitung": rahmen_rendern(
            kern.rahmenhandlung_gespraechseinleitung, vignette
        ),
        "gespraechsschritte": gespraechsschritte,
        "ist_probelauf": ist_probelauf,
        "erneute_eingabe": erneute_eingabe,
        "ist_gescheitert": ist_gescheitert,
        "debrief": rahmen_rendern(kern.rahmenhandlung_debrief, vignette),
        "zeigt_debrief": zeigt_debrief,
        "ist_lesend": ist_lesend,
        "spracheingabe_verfuegbar": spracheingabe_verfuegbar,
        "navigation": navigation or sitzungsnavigation(ist_probelauf),
        "sitzung_pk": sitzung_pk,
    }
    template: str = (
        "sitzungen/includes/sitzung_fortsetzung.html"
        if _ist_htmx(request)
        else "sitzungen/sitzung.html"
    )
    return render(request, template, context)


def _eigene_entwuerfe(konto: "Konto") -> QuerySet[Vignette]:
    """Liefert die Entwürfe aus dem Eigentümer-Kreis eines Kontos."""

    return Vignette.objects.filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(konto),
        zustand=Vignette.Zustand.ENTWURF,
    )


def _eigene_vignetten(konto: "Konto") -> QuerySet[Vignette]:
    """Liefert alle Fassungen aus dem Eigentümer-Kreis eines Kontos.

    Ein Probelauf ist schreibfrei; deshalb darf er über jede eigene
    Fassung laufen – Entwurf wie finalisiert oder archiviert.
    """

    return Vignette.objects.filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(konto),
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
    return _eigene_vignetten(konto)


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
    vignette: Vignette,
    kern: Simulationskern,
    schritte: list[GespraechsschrittDaten],
    erneute_eingabe: str | None = None,
) -> HttpResponse:
    """Rendert das Diagnosegespräch mit seinem bisherigen Verlauf."""

    return _sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=schritte,
        ist_probelauf=True,
        erneute_eingabe=erneute_eingabe,
    )


def _debrief_anzeigen(
    request: HttpRequest,
    vignette: Vignette,
    kern: Simulationskern,
    schritte: list[GespraechsschrittDaten],
) -> HttpResponse:
    """Rendert den Debrief nach dem Ende des Diagnosegesprächs."""

    return _sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=schritte,
        ist_probelauf=True,
        zeigt_debrief=True,
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
    return _sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=sink.gespraechsschritte,
        ist_probelauf=True,
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
        _eigene_vignetten(request.user).select_related("gepinnter_kern"),
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
    vignette, kern = _probelauf_vignette_und_kern(request, sink)
    if request.method == "GET":
        sink.zeitbudget_fortsetzen()
        return _gespraech_anzeigen(request, vignette, kern, schritte)
    if sink.ist_gescheitert:
        return _gespraech_anzeigen(request, vignette, kern, schritte)
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
        return _gespraech_anzeigen(request, vignette, kern, schritte, eingabe)
    if sink.budget_erschoepft(vignette):
        sink.status_setzen(Sitzung.Status.ABGESCHLOSSEN)
        return _debrief_anzeigen(request, vignette, kern, schritte)
    sink.zeitbudget_fortsetzen()
    return _gespraech_anzeigen(request, vignette, kern, schritte)


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


def transkriptions_endpunkt(
    anbieter: Transkription,
) -> Callable[[HttpRequest], HttpResponse]:
    """Erzeugt den geschützten Endpunkt für einen Transkriptions-Anbieter."""

    @login_required
    def endpunkt(request: HttpRequest) -> HttpResponse:
        # Prüft die Vorbedingungen, bevor Audio den Anbieter erreichen kann.
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        sitzung: Sitzung = _training_sitzung(request)
        if not sitzung.teilnahme.hat_in_audioverarbeitung_eingewilligt:
            return JsonResponse({"status": "einwilligung_verweigert"}, status=403)
        if not settings.TRANSKRIPTION_ZERO_RETENTION:
            return JsonResponse({"status": "zero_retention_fehlt"}, status=503)
        audio: bytes = request.FILES["audio"].read()
        try:
            text: str = anbieter.transkribieren(audio)
        except LeeresTranskript:
            return JsonResponse({"status": "leeres_transkript"}, status=422)
        except TranskriptionsAnbieterfehler:
            return JsonResponse({"status": "anbieterfehler"}, status=502)
        except AnbieterNichtErreichbar:
            return JsonResponse({"status": "anbieter_nicht_erreichbar"}, status=503)
        return JsonResponse({"text": text})

    return endpunkt


def _persistierte_schritte(sitzung: Sitzung) -> QuerySet[Gespraechsschritt]:
    # Liefert den sichtbaren Verlauf in seiner gespeicherten Reihenfolge.

    return sitzung.gespraechsschritt_set.order_by("reihenfolge")


def _zeitbudget_schluessel(sitzung: Sitzung, name: str) -> str:
    # Isoliert die Uhr jeder persistierten Sitzung von allen anderen Sitzungen.

    return f"sitzung_{sitzung.pk}_{name}"


def _zeitbudget_fortsetzen(request: HttpRequest, sitzung: Sitzung) -> None:
    # Startet die unsichtbare Uhr ausschließlich während des Teilnehmer:innenzugs.

    schluessel: str = _zeitbudget_schluessel(sitzung, "zeit_laeuft_seit")
    if (
        sitzung.vignette.budget_typ == Vignette.BudgetTyp.ZEIT
        and schluessel not in request.session
    ):
        request.session[schluessel] = monotonic()


def zeitbudget_anhalten(request: HttpRequest, sitzung: Sitzung) -> None:
    # Hält die Uhr vor Modellaufruf und schreibt die verbrauchte Zeit fort.

    startzeit: float | None = request.session.pop(
        _zeitbudget_schluessel(sitzung, "zeit_laeuft_seit"), None
    )
    if startzeit is not None:
        verbrauchte_zeit_schluessel: str = _zeitbudget_schluessel(
            sitzung, "verbrauchte_zeit"
        )
        request.session[verbrauchte_zeit_schluessel] = (
            request.session.get(verbrauchte_zeit_schluessel, 0.0)
            + monotonic()
            - startzeit
        )


def _budget_erschoepft(request: HttpRequest, sitzung: Sitzung) -> bool:
    # Prüft das unsichtbare Gesprächsbudget nach einem vollständigen Schritt.

    if sitzung.vignette.budget_wert is None:
        return False
    if sitzung.vignette.budget_typ == Vignette.BudgetTyp.SCHRITTE:
        return _persistierte_schritte(sitzung).count() >= sitzung.vignette.budget_wert
    return request.session.get(
        _zeitbudget_schluessel(sitzung, "verbrauchte_zeit"), 0.0
    ) >= sitzung.vignette.budget_wert


def persistierten_debrief_anzeigen(
    request: HttpRequest,
    sitzung: Sitzung,
    navigation: Sitzungsnavigation | None = None,
) -> HttpResponse:
    # Rendert den Debrief einer persistierten Sitzung.

    return _sitzung_anzeigen(
        request,
        vignette=sitzung.vignette,
        kern=sitzung.simulationskern,
        gespraechsschritte=_persistierte_schritte(sitzung),
        ist_probelauf=False,
        zeigt_debrief=True,
        navigation=navigation,
        spracheingabe_verfuegbar=sitzung.teilnahme.hat_in_audioverarbeitung_eingewilligt,
        sitzung_pk=sitzung.pk,
    )


def _persistierten_fehler_anzeigen(
    request: HttpRequest,
    sitzung: Sitzung,
    navigation: Sitzungsnavigation | None = None,
) -> HttpResponse:
    # Rendert den abgebrochenen Verlauf einer gescheiterten Sitzung.

    return _persistiertes_gespraech_anzeigen(
        request,
        sitzung,
        _persistierte_schritte(sitzung),
        ist_gescheitert=True,
        navigation=navigation,
    )


def _persistiertes_gespraech_anzeigen(
    request: HttpRequest,
    sitzung: Sitzung,
    schritte: QuerySet[Gespraechsschritt],
    *,
    ist_gescheitert: bool = False,
    navigation: Sitzungsnavigation | None = None,
) -> HttpResponse:
    # Rendert eine persistierte Sitzung in der gemeinsamen Sitzungsansicht.

    return _sitzung_anzeigen(
        request,
        vignette=sitzung.vignette,
        kern=sitzung.simulationskern,
        gespraechsschritte=schritte,
        ist_probelauf=False,
        ist_gescheitert=ist_gescheitert,
        navigation=navigation,
        spracheingabe_verfuegbar=sitzung.teilnahme.hat_in_audioverarbeitung_eingewilligt,
    )


def _training_zur_auswahl_zurueckkehren(
    request: HttpRequest, sitzung: Sitzung
) -> HttpResponse:
    """Löst die aktive Sitzung und kehrt zur Auswahl ihres Trainings zurück."""

    from training.models import Trainingsbindung

    training_pk: int = get_object_or_404(
        Trainingsbindung, teilnahme=sitzung.teilnahme
    ).training_id
    request.session.pop("training_sitzung_pk", None)
    return redirect("training:detail", pk=training_pk)


def persistiertes_gespraech(
    request: HttpRequest,
    sitzung: Sitzung,
    navigation: Sitzungsnavigation | None = None,
) -> HttpResponse:
    """Führt einen Gesprächsschritt über die gemeinsame persistierte Darstellung aus."""

    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    if sitzung.status == Sitzung.Status.ABGESCHLOSSEN:
        return persistierten_debrief_anzeigen(request, sitzung, navigation)
    schritte: QuerySet[Gespraechsschritt] = _persistierte_schritte(sitzung)
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return _persistierten_fehler_anzeigen(request, sitzung, navigation)
    if request.method == "GET":
        _zeitbudget_fortsetzen(request, sitzung)
        return _persistiertes_gespraech_anzeigen(
            request, sitzung, schritte, navigation=navigation
        )
    zeitbudget_anhalten(request, sitzung)
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
        return _persistierten_fehler_anzeigen(request, sitzung, navigation)
    if _budget_erschoepft(request, sitzung):
        return persistierten_debrief_anzeigen(request, sitzung, navigation)
    _zeitbudget_fortsetzen(request, sitzung)
    return _persistiertes_gespraech_anzeigen(
        request,
        sitzung,
        _persistierte_schritte(sitzung),
        navigation=navigation,
    )


@login_required
def training_gespraech(request: HttpRequest) -> HttpResponse:
    """Führt den nächsten persistierten Gesprächsschritt einer Trainingssitzung aus."""

    return persistiertes_gespraech(request, _training_sitzung(request))


@login_required
def training_beenden(request: HttpRequest) -> HttpResponse:
    """Beendet das Diagnosegespräch vorzeitig und zeigt seinen Debrief."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = _training_sitzung(request)
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return _persistierten_fehler_anzeigen(request, sitzung)
    zeitbudget_anhalten(request, sitzung)
    return persistierten_debrief_anzeigen(request, sitzung)


@login_required
def training_abbrechen(request: HttpRequest) -> HttpResponse:
    """Bricht eine Trainingssitzung ohne Diagnose gewollt ab."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = _training_sitzung(request)
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return _persistierten_fehler_anzeigen(request, sitzung)
    if sitzung.status == Sitzung.Status.ABGESCHLOSSEN:
        return persistierten_debrief_anzeigen(request, sitzung)
    if sitzung.status == Sitzung.Status.ABGEBROCHEN:
        return _training_zur_auswahl_zurueckkehren(request, sitzung)
    zeitbudget_anhalten(request, sitzung)
    DBSink.fuer_sitzung(sitzung).status_setzen(Sitzung.Status.ABGEBROCHEN)
    return _training_zur_auswahl_zurueckkehren(request, sitzung)


@login_required
def training_debrief(request: HttpRequest) -> HttpResponse:
    """Speichert die Diagnose und kehrt zur freien Trainingswahl zurück."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = _training_sitzung(request)
    with transaction.atomic():
        sitzung = Sitzung.objects.select_for_update().get(pk=sitzung.pk)
        if sitzung.status == Sitzung.Status.GESCHEITERT:
            return _persistierten_fehler_anzeigen(request, sitzung)
        if sitzung.status != Sitzung.Status.LAUFEND:
            return _training_zur_auswahl_zurueckkehren(request, sitzung)
        DBSink.fuer_sitzung(sitzung).diagnose_setzen(request.POST["diagnose"])
    return _training_zur_auswahl_zurueckkehren(request, sitzung)


@login_required
def training_sitzung_ansehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine vergangene Trainingssitzung schreibgeschützt an."""

    from training.models import Trainingsbindung

    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme"),
        pk=pk,
    )
    get_object_or_404(
        Trainingsbindung.objects.filter(konto=request.user), teilnahme=sitzung.teilnahme
    )

    return _sitzung_anzeigen(
        request,
        vignette=sitzung.vignette,
        kern=sitzung.simulationskern,
        gespraechsschritte=_persistierte_schritte(sitzung),
        ist_probelauf=False,
        zeigt_debrief=(sitzung.status == Sitzung.Status.ABGESCHLOSSEN),
        ist_lesend=True,
    )

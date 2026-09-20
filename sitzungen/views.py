"""Views für Probeläufe und persistierte Trainingssitzungen."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from konten.navigation import ist_administratorin
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.transkription import (
    AnbieterNichtErreichbar,
    LeeresTranskript,
    Transkription,
    TranskriptionsAnbieterfehler,
)
from sitzungen.durchlauf import (
    Sitzungsnavigation,
    gespraechsschritt_ausfuehren,
    sitzung_abbrechen,
    sitzung_anzeigen,
    sitzung_beenden,
    sitzung_starten,
)
from sitzungen.models import Gespraechsschritt, Sitzung
from sitzungen.sink import (
    DBSink,
    GespraechsschrittDaten,
    ScratchSink,
    probelauf_laeuft,
)
from vignetten.models import Vignette

if TYPE_CHECKING:
    from konten.models import Konto


def _eigene_entwuerfe(konto: "Konto") -> QuerySet[Vignette]:
    """Liefert die Entwürfe aus dem Eigentümer-Kreis eines Kontos."""

    return Vignette.objects.sichtbar_fuer(konto).filter(
        zustand=Vignette.Zustand.ENTWURF
    )


def _eigene_vignetten(konto: "Konto") -> QuerySet[Vignette]:
    """Liefert alle Fassungen aus dem Eigentümer-Kreis eines Kontos.

    Ein Probelauf ist schreibfrei; deshalb darf er über jede eigene
    Fassung laufen – Entwurf wie finalisiert oder archiviert.
    """

    return Vignette.objects.sichtbar_fuer(konto)


def _administratorin_erforderlich(request: HttpRequest) -> HttpResponse | None:
    # Schützt den freien Auswähler vor Konten ohne Administratorinnen-Rolle.

    if not ist_administratorin(request.user):
        return HttpResponse(status=403)
    return None


def _probelauf_vignetten(konto: "Konto", sink: ScratchSink) -> QuerySet[Vignette]:
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

    return sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=schritte,
        ist_probelauf=True,
        erneute_eingabe=erneute_eingabe,
        spracheingabe_verfuegbar=True,
    )


def _debrief_anzeigen(
    request: HttpRequest,
    vignette: Vignette,
    kern: Simulationskern,
    schritte: list[GespraechsschrittDaten],
) -> HttpResponse:
    """Rendert den Debrief nach dem Ende des Diagnosegesprächs."""

    return sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=schritte,
        ist_probelauf=True,
        zeigt_debrief=True,
        spracheingabe_verfuegbar=True,
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
    return sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=sink.gespraechsschritte,
        ist_probelauf=True,
        spracheingabe_verfuegbar=True,
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
    sitzung_beenden(sink)
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

    sitzung_pk: int | None = request.session.get("training_sitzung_pk")
    if sitzung_pk is None:
        raise PermissionDenied
    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme"),
        pk=sitzung_pk,
    )
    get_object_or_404(
        Trainingsbindung.objects.filter(konto=request.user), teilnahme=sitzung.teilnahme
    )
    return sitzung


def transkriptions_endpunkt(
    anbieter: Transkription,
) -> Callable[[HttpRequest], HttpResponse]:
    """Erzeugt den geschützten Endpunkt für einen Transkriptions-Anbieter."""

    def endpunkt(request: HttpRequest) -> HttpResponse:
        # Prüft die Vorbedingungen, bevor Audio den Anbieter erreichen kann.
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        from erhebungen.views import sitzung_fuer_transkription

        # Im Probelauf spricht die angemeldete Autor:in über eigenes Material;
        # es gibt keine Teilnahme, die einwilligen könnte (ADR-0026).
        if not (request.user.is_authenticated and probelauf_laeuft(request.session)):
            sitzung: Sitzung | None = sitzung_fuer_transkription(request)
            if sitzung is None and request.user.is_authenticated:
                sitzung = _training_sitzung(request)
            if sitzung is None:
                raise PermissionDenied
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


def persistierten_debrief_anzeigen(
    request: HttpRequest,
    sitzung: Sitzung,
    navigation: Sitzungsnavigation | None = None,
    anhang: str | None = None,
) -> HttpResponse:
    # Rendert den Debrief einer persistierten Sitzung.

    return sitzung_anzeigen(
        request,
        vignette=sitzung.vignette,
        kern=sitzung.simulationskern,
        gespraechsschritte=sitzung.gespraechsschritte,
        ist_probelauf=False,
        zeigt_debrief=True,
        navigation=navigation,
        spracheingabe_verfuegbar=sitzung.teilnahme.hat_in_audioverarbeitung_eingewilligt,
        sitzung_pk=sitzung.pk,
        anhang=anhang,
    )


def _persistierten_fehler_anzeigen(
    request: HttpRequest,
    sitzung: Sitzung,
    navigation: Sitzungsnavigation | None = None,
    anhang: str | None = None,
) -> HttpResponse:
    # Rendert den abgebrochenen Verlauf einer gescheiterten Sitzung.

    return _persistiertes_gespraech_anzeigen(
        request,
        sitzung,
        sitzung.gespraechsschritte,
        ist_gescheitert=True,
        navigation=navigation,
        anhang=anhang,
    )


def _persistiertes_gespraech_anzeigen(
    request: HttpRequest,
    sitzung: Sitzung,
    schritte: QuerySet[Gespraechsschritt],
    *,
    ist_gescheitert: bool = False,
    ist_lesend: bool = False,
    navigation: Sitzungsnavigation | None = None,
    anhang: str | None = None,
) -> HttpResponse:
    # Rendert eine persistierte Sitzung in der gemeinsamen Sitzungsansicht.

    return sitzung_anzeigen(
        request,
        vignette=sitzung.vignette,
        kern=sitzung.simulationskern,
        gespraechsschritte=schritte,
        ist_probelauf=False,
        ist_gescheitert=ist_gescheitert,
        ist_lesend=ist_lesend,
        navigation=navigation,
        spracheingabe_verfuegbar=sitzung.teilnahme.hat_in_audioverarbeitung_eingewilligt,
        sitzung_pk=sitzung.pk,
        anhang=anhang,
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
    anhang: str | None = None,
) -> HttpResponse:
    """Führt einen Gesprächsschritt über die gemeinsame persistierte Darstellung aus."""

    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    if sitzung.status == Sitzung.Status.ABGESCHLOSSEN:
        return persistierten_debrief_anzeigen(request, sitzung, navigation, anhang)
    schritte: QuerySet[Gespraechsschritt] = sitzung.gespraechsschritte
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return _persistierten_fehler_anzeigen(request, sitzung, navigation, anhang)
    if sitzung.status == Sitzung.Status.ABGEBROCHEN:
        return _persistiertes_gespraech_anzeigen(
            request,
            sitzung,
            schritte,
            ist_lesend=True,
            navigation=navigation,
            anhang=anhang,
        )
    sink: DBSink = DBSink.fuer_sitzung(sitzung, session=request.session)
    if request.method == "GET":
        sink.zeitbudget_fortsetzen()
        return _persistiertes_gespraech_anzeigen(
            request, sitzung, schritte, navigation=navigation
        )
    sink.zeitbudget_anhalten()
    antwortversuch = gespraechsschritt_ausfuehren(
        sink,
        sitzung.vignette,
        sitzung.simulationskern,
        sitzung.modell_konfiguration,
        request.POST["eingabe"],
    )
    if antwortversuch.endgueltig_gescheitert:
        return _persistierten_fehler_anzeigen(request, sitzung, navigation, anhang)
    if sink.budget_erschoepft(sitzung.vignette):
        return persistierten_debrief_anzeigen(request, sitzung, navigation)
    sink.zeitbudget_fortsetzen()
    return _persistiertes_gespraech_anzeigen(
        request,
        sitzung,
        sitzung.gespraechsschritte,
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
    sink: DBSink = DBSink.fuer_sitzung(sitzung, session=request.session)
    sitzung_beenden(sink)
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
    sink: DBSink = DBSink.fuer_sitzung(sitzung, session=request.session)
    sitzung_abbrechen(sink)
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

    return sitzung_anzeigen(
        request,
        vignette=sitzung.vignette,
        kern=sitzung.simulationskern,
        gespraechsschritte=sitzung.gespraechsschritte,
        ist_probelauf=False,
        zeigt_debrief=(sitzung.status == Sitzung.Status.ABGESCHLOSSEN),
        ist_lesend=True,
    )

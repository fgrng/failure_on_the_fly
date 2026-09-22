"""Views für Probeläufe und die Bausteine persistierter Sitzungen ihrer Aufrufer."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from konten.navigation import ist_administratorin
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.transkription import (
    AnbieterNichtErreichbar,
    LeeresTranskript,
    Transkription,
    TranskriptionsAnbieterfehler,
)
from sitzungen import durchlauf
from sitzungen.durchlauf import (
    Ausgang,
    Sitzungsnavigation,
    gespraechsschritt_ausfuehren,
    sitzung_anzeigen,
    sitzung_beenden,
    sitzung_starten,
)
from sitzungen.models import Diagnose, Eingabemodus, Gespraechsschritt, Sitzung
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


def _sitzungsnavigation() -> Sitzungsnavigation:
    # Bündelt die modusspezifischen Routen für die schreibfreie Probelaufansicht.

    return Sitzungsnavigation(
        bezeichnung="Probelauf",
        gespraech_url=reverse("sitzungen:probelauf_gespraech"),
        beenden_url=reverse("sitzungen:probelauf_beenden"),
        debrief_url=reverse("sitzungen:probelauf_debrief"),
        abbrechen_url=None,
        transkription_url=reverse("sitzungen:transkription"),
    )


def _gespraech_anzeigen(
    request: HttpRequest,
    vignette: Vignette,
    kern: Simulationskern,
    schritte: list[GespraechsschrittDaten],
    erneute_eingabe: str | None = None,
    erneuter_eingabemodus: str = Eingabemodus.GETIPPT,
) -> HttpResponse:
    """Rendert das Diagnosegespräch mit seinem bisherigen Verlauf."""

    return sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=schritte,
        ist_probelauf=True,
        navigation=_sitzungsnavigation(),
        erneute_eingabe=erneute_eingabe,
        erneuter_eingabemodus=erneuter_eingabemodus,
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
        navigation=_sitzungsnavigation(),
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
    if freie_auswahl:
        sitzung_starten(sink, vignette, modell_konfiguration, simulationskern=kern)
    else:
        sitzung_starten(sink, vignette, modell_konfiguration)
    if freie_auswahl:
        sink.freie_auswahl_setzen()
    return sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=sink.gespraechsschritte,
        ist_probelauf=True,
        navigation=_sitzungsnavigation(),
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
    kern: Simulationskern = vignette.gepinnter_kern
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
        sink.zug_beginnen(durchlauf.jetzt())
        return _gespraech_anzeigen(request, vignette, kern, schritte)
    modell_konfiguration: ModellKonfiguration = get_object_or_404(
        ModellKonfiguration.objects.all(), pk=sink.modell_konfiguration_pk
    )
    eingabe: str = request.POST["eingabe"]
    eingabemodus: Eingabemodus = Eingabemodus.aus_formular(
        request.POST.get("eingabemodus")
    )
    ausgang: Ausgang = gespraechsschritt_ausfuehren(
        sink,
        vignette,
        kern,
        modell_konfiguration,
        eingabe,
        eingabemodus,
    )
    if ausgang is Ausgang.GESCHEITERT:
        sink.zug_beginnen(durchlauf.jetzt())
        return _gespraech_anzeigen(
            request, vignette, kern, schritte, eingabe, eingabemodus
        )
    if ausgang is Ausgang.BUDGET_ERSCHOEPFT:
        return _debrief_anzeigen(request, vignette, kern, schritte)
    sink.zug_beginnen(durchlauf.jetzt())
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
    """Verwirft den Probelauf samt eingegebener Diagnose.

    Danach steht die Autor:in wieder bei ihrer Vignette: Von dort hat sie den
    Probelauf gestartet, und dort ändert sie, was ihr aufgefallen ist. Nur der
    freie Auswähler der Administration führt zu sich selbst zurück — er ist
    kein Editor, sondern die Werkbank für beliebige Tripel.
    """

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sink: ScratchSink = ScratchSink(request.session)
    freie_auswahl: bool = sink.freie_auswahl
    vignette_pk: int = sink.vignette_pk
    sink.verwerfen()
    if freie_auswahl:
        return redirect("sitzungen:administratorin_probelauf_auswahl")
    return redirect("vignetten:detail", pk=vignette_pk)


def probelauf_sitzung_fuer_transkription(request: HttpRequest) -> Sitzung | None:
    """Gibt den laufenden Probelauf frei, dem jedes Einwilligungsobjekt fehlt.

    Hier spricht die angemeldete Autor:in über eigenes Material; es gibt keine
    Teilnahme, die einwilligen könnte (ADR-0026).
    """

    if not (request.user.is_authenticated and probelauf_laeuft(request.session)):
        raise PermissionDenied
    return None


def transkriptions_endpunkt(
    anbieter_bilden: Callable[[], Transkription],
    sitzung_aufloesen: Callable[[HttpRequest], Sitzung | None],
) -> Callable[[HttpRequest], HttpResponse]:
    """Erzeugt den geschützten Endpunkt eines Prinzipals für seinen Anbieter.

    `anbieter_bilden` wird je Anfrage gerufen: Die Anbieterkonfiguration liegt
    in der Datenbank, und ein gehaltener Adapter überlebte ihre Änderung.

    `sitzung_aufloesen` trägt die Autorisierung des jeweiligen Prinzipals und
    hat drei erlaubte Ausgänge:

    - eine Sitzung: Ihre Teilnahme muss in die Audioverarbeitung eingewilligt
      haben, sonst endet die Anfrage hier.
    - `None`: Es gibt keine Teilnahme, die einwilligen könnte, etwa im
      Probelauf (ADR-0026).
    - `PermissionDenied`: Die Auflösung verweigert den Zugriff selbst.

    Das Zero-Retention-Tor aus ADR-0026 liegt dahinter und gilt für alle.
    """

    def endpunkt(request: HttpRequest) -> HttpResponse:
        # Prüft die Vorbedingungen, bevor Audio den Anbieter erreichen kann.
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        sitzung: Sitzung | None = sitzung_aufloesen(request)
        if (
            sitzung is not None
            and not sitzung.teilnahme.hat_in_audioverarbeitung_eingewilligt
        ):
            return JsonResponse({"status": "einwilligung_verweigert"}, status=403)
        if not settings.TRANSKRIPTION_ZERO_RETENTION:
            return JsonResponse({"status": "zero_retention_fehlt"}, status=503)
        aufnahme: UploadedFile = request.FILES["audio"]
        # Die Größe steht vor dem Einlesen fest: Eine zu große Aufnahme wird
        # abgewiesen, ohne sie je in den Speicher zu holen.
        if aufnahme.size > settings.TRANSKRIPTION_MAX_AUFNAHME_BYTES:
            return JsonResponse({"status": "aufnahme_zu_gross"}, status=413)
        audio: bytes = aufnahme.read()
        try:
            text: str = anbieter_bilden().transkribieren(audio)
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
    navigation: Sitzungsnavigation,
    anhang: str | None = None,
) -> HttpResponse:
    # Rendert den Debrief einer persistierten Sitzung.

    # Liegt die Diagnose bereits vor, zeigt das Formular sie nur noch an:
    # Sie ist je Sitzung einmalig und darf sich nicht nachträglich ändern.
    abgegebene_diagnose: str | None = (
        Diagnose.objects.filter(sitzung=sitzung).values_list("text", flat=True).first()
    )
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
        abgegebene_diagnose=abgegebene_diagnose,
    )


def persistierten_fehler_anzeigen(
    request: HttpRequest,
    sitzung: Sitzung,
    navigation: Sitzungsnavigation,
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
    navigation: Sitzungsnavigation,
    ist_gescheitert: bool = False,
    ist_lesend: bool = False,
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


def _kein_sitzungsblock() -> str | None:
    # Steht für eine Aufruferin, die unter die Sitzung nichts hängt.

    return None


def persistiertes_gespraech(
    request: HttpRequest,
    sitzung: Sitzung,
    navigation: Sitzungsnavigation,
    sitzungsblock: Callable[[], str | None] = _kein_sitzungsblock,
) -> HttpResponse:
    """Führt einen Gesprächsschritt über die gemeinsame persistierte Darstellung aus.

    `sitzungsblock` rendert den Anhang, den die Aufruferin unter eine beendete
    Sitzung hängt. Er wird erst gerufen, wenn die gewählte Darstellung ihn
    wirklich trägt, weil sein Anlegen zur Datenspur gehört (ADR-0029).
    """

    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    if sitzung.status == Sitzung.Status.ABGESCHLOSSEN:
        return persistierten_debrief_anzeigen(
            request, sitzung, navigation, sitzungsblock()
        )
    schritte: QuerySet[Gespraechsschritt] = sitzung.gespraechsschritte
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return persistierten_fehler_anzeigen(
            request, sitzung, navigation, sitzungsblock()
        )
    if sitzung.status == Sitzung.Status.ABGEBROCHEN:
        return _persistiertes_gespraech_anzeigen(
            request,
            sitzung,
            schritte,
            ist_lesend=True,
            navigation=navigation,
            anhang=sitzungsblock(),
        )
    sink: DBSink = DBSink.fuer_sitzung(sitzung)
    if request.method == "GET":
        sink.zug_beginnen(durchlauf.jetzt())
        return _persistiertes_gespraech_anzeigen(
            request, sitzung, schritte, navigation=navigation
        )
    ausgang: Ausgang = gespraechsschritt_ausfuehren(
        sink,
        sitzung.vignette,
        sitzung.simulationskern,
        sitzung.modell_konfiguration,
        request.POST["eingabe"],
        Eingabemodus.aus_formular(request.POST.get("eingabemodus")),
    )
    if ausgang is Ausgang.GESCHEITERT:
        return persistierten_fehler_anzeigen(
            request, sitzung, navigation, sitzungsblock()
        )
    if ausgang is Ausgang.BUDGET_ERSCHOEPFT:
        return persistierten_debrief_anzeigen(request, sitzung, navigation)
    sink.zug_beginnen(durchlauf.jetzt())
    return _persistiertes_gespraech_anzeigen(
        request,
        sitzung,
        sitzung.gespraechsschritte,
        navigation=navigation,
    )

"""Öffentlicher Einstieg in pseudonyme Erhebungen."""

from datetime import datetime
from functools import wraps
from typing import Callable, Concatenate, Iterable, ParamSpec
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .ablauf import naechster_schritt
from .models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsvignette,
    Stichprobe,
    Vignettenposition,
)
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Sitzung
from sitzungen.orchestrierung import sitzung_starten
from sitzungen.sink import DBSink
from sitzungen.views import (
    Sitzungsnavigation,
    persistiertes_gespraech,
    persistierten_debrief_anzeigen,
    zeitbudget_anhalten,
)
from vignetten.models import Vignette, Vignettenhistorie

_TEILNAHME_TOKENS_SESSION_KEY: str = "erhebung_teilnahme_tokens"
_FORSCHENDE_GRUPPE: str = "Forschende:r"
P = ParamSpec("P")


def _forschende_erforderlich(
    view: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """Schützt eine View der Forschenden-UI mit der Rollenprüfung."""

    @wraps(view)
    def geschuetzte_view(
        request: HttpRequest,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> HttpResponse:
        if not request.user.groups.filter(name=_FORSCHENDE_GRUPPE).exists():
            return HttpResponse(status=403)
        return view(request, *args, **kwargs)

    return geschuetzte_view


def _sichtbare_erhebung(request: HttpRequest, pk: int) -> Erhebung:
    """Lädt eine für die eingeloggte Forschende sichtbare Erhebung."""

    return get_object_or_404(Erhebung.objects.sichtbar_fuer(request.user), pk=pk)


def _eigene_finalen_vignetten(request: HttpRequest) -> QuerySet[Vignette]:
    """Liefert einbindbare Fassungen aus dem Eigentümer-Kreis der Forschenden."""

    return Vignette.objects.einbindbar().filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user)
    )


def _status_badge(erhebung: Erhebung) -> str:
    """Ordnet Erhebungsstatus den gemeinsamen Badge-Klassen zu."""

    return {
        Erhebung.Status.ENTWURF: "draft",
        Erhebung.Status.FINAL: "final",
        Erhebung.Status.ARCHIVIERT: "archived",
    }[erhebung.status]


def _vignettenzeilen(
    vignetten: Iterable[Vignette], erhebung: Erhebung, aktion: str
) -> list[dict[str, object]]:
    """Baut die Tabellenzeilen einer Zuordnungsspalte samt ihrer Aktions-URL."""

    return [
        {
            "pk": vignette.pk,
            "label": vignette.historie.name or vignette.fach,
            "fach": vignette.fach,
            "thema": vignette.thema,
            "aktion_url": reverse(aktion, args=[erhebung.pk, vignette.pk]),
        }
        for vignette in vignetten
    ]


def _validierte_aktion_ausfuehren(
    request: HttpRequest, aktion: Callable[[], None]
) -> None:
    """Führt eine Domänenaktion aus und zeigt ihren Validierungsfehler an."""

    try:
        aktion()
    except ValidationError as error:
        messages.error(request, error.message)


@login_required
@_forschende_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Listet die eigenen Erhebungen einer Forschenden."""

    erhebungen: QuerySet[Erhebung] = Erhebung.objects.sichtbar_fuer(request.user)
    for erhebung in erhebungen:
        erhebung.status_badge = _status_badge(erhebung)
    return render(request, "erhebungen/liste.html", {"erhebungen": erhebungen})


@login_required
@_forschende_erforderlich
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt eine neue Erhebung als Entwurf an."""

    if request.method == "POST":
        erhebung: Erhebung = Erhebung.objects.create(
            name=request.POST.get("name", "Neue Erhebung"),
            eigentuemerin=request.user,
        )
        return redirect("erhebungen:detail", pk=erhebung.pk)
    return render(request, "erhebungen/anlegen.html")


@login_required
@_forschende_erforderlich
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine eigene Erhebung zur weiteren Bearbeitung."""

    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    stichproben: QuerySet[Stichprobe] = erhebung.stichprobe_set.annotate(
        teilnahmezahl=Count("erhebungsbindung")
    )
    for stichprobe in stichproben:
        stichprobe.teilnahme_url = request.build_absolute_uri(
            reverse("erhebungen:teilnehmen", args=[stichprobe.teilnahme_link])
        )

    vignettenzugehoerigkeiten: QuerySet[Erhebungsvignette] = (
        erhebung.vignettenzugehoerigkeiten.select_related("vignette", "vignette__historie")
    )
    verfuegbare_vignetten: QuerySet[Vignette] = _eigene_finalen_vignetten(request).exclude(
        pk__in=erhebung.vignetten.values("pk")
    )

    return render(
        request,
        "erhebungen/detail.html",
        {
            "erhebung": erhebung,
            "status_badge": _status_badge(erhebung),
            "vignettenzugehoerigkeiten": vignettenzugehoerigkeiten,
            "aufgenommene_daten": _vignettenzeilen(
                [zugehoerigkeit.vignette for zugehoerigkeit in vignettenzugehoerigkeiten],
                erhebung,
                "erhebungen:vignette_entfernen",
            ),
            "verfuegbare_daten": _vignettenzeilen(
                verfuegbare_vignetten, erhebung, "erhebungen:vignette_hinzufuegen"
            ),
            "kann_zurueckziehen": erhebung.kann_zurueckgezogen_werden,
            "kann_archivieren": erhebung.kann_archiviert_werden,
            "kann_entarchivieren": erhebung.kann_entarchiviert_werden,
            "stichproben": stichproben,
        },
    )


@login_required
@_forschende_erforderlich
def stichprobe_anlegen(request: HttpRequest, pk: int) -> HttpResponse:
    """Legt unter einer finalen eigenen Erhebung eine Stichprobe an."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.FINAL:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    beginn: datetime | None = parse_datetime(request.POST.get("beginn", ""))
    ende: datetime | None = parse_datetime(request.POST.get("ende", ""))
    if beginn is None or ende is None:
        return HttpResponseBadRequest("Beginn und Ende müssen gültige Zeitpunkte sein.")
    if timezone.is_naive(beginn):
        beginn = timezone.make_aware(beginn)
    if timezone.is_naive(ende):
        ende = timezone.make_aware(ende)
    if ende < beginn:
        return HttpResponseBadRequest("Das Ende darf nicht vor dem Beginn liegen.")
    Stichprobe.objects.create(erhebung=erhebung, beginn=beginn, ende=ende)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def stichprobe_archivieren(request: HttpRequest, pk: int, stichprobe_pk: int) -> HttpResponse:
    """Archiviert eine datenfreie Stichprobe über ihre Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    stichprobe: Stichprobe = get_object_or_404(
        erhebung.stichprobe_set, pk=stichprobe_pk
    )
    _validierte_aktion_ausfuehren(request, stichprobe.archivieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def vignette_hinzufuegen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Nimmt eine eigene finale Fassung in einen eigenen Entwurf auf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    vignette: Vignette = get_object_or_404(_eigene_finalen_vignetten(request), pk=vignette_pk)
    position: int | None = None
    if erhebung.randomisierung == Erhebung.Randomisierung.FEST:
        position = erhebung.vignettenzugehoerigkeiten.count() + 1
    Erhebungsvignette.objects.get_or_create(
        erhebung=erhebung, vignette=vignette, defaults={"position": position}
    )
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def vignette_entfernen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Entfernt eine finale Fassung aus einem eigenen Entwurf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status == Erhebung.Status.ENTWURF:
        get_object_or_404(erhebung.vignettenzugehoerigkeiten, vignette_id=vignette_pk).delete()
    return redirect("erhebungen:detail", pk=erhebung.pk)


def _feste_reihenfolge_setzen(erhebung: Erhebung, zugehoerigkeit_ids: list[str]) -> None:
    """Schreibt eine vollständige Reihenfolge ohne die eindeutigen Positionen zu kreuzen."""

    zugehoerigkeiten: QuerySet[Erhebungsvignette] = (
        erhebung.vignettenzugehoerigkeiten.select_for_update()
    )
    vorhandene_ids: list[int] = list(zugehoerigkeiten.values_list("pk", flat=True))
    try:
        neue_ids: list[int] = [int(pk) for pk in zugehoerigkeit_ids]
    except ValueError:
        return
    if len(neue_ids) != len(set(neue_ids)) or set(neue_ids) != set(vorhandene_ids):
        return
    bisherige_positionen: list[int] = list(
        zugehoerigkeiten.values_list("position", flat=True)
    )
    zugehoerigkeiten.update(position=F("position") + max(bisherige_positionen, default=0))
    for position, zugehoerigkeit_id in enumerate(neue_ids, start=1):
        zugehoerigkeiten.filter(pk=zugehoerigkeit_id).update(position=position)


@login_required
@_forschende_erforderlich
@transaction.atomic
def konfiguration_speichern(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert die konfigurierbaren Texte, Regel und feste Reihenfolge eines Entwurfs."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    randomisierung: str = request.POST.get("randomisierung", erhebung.randomisierung)
    if randomisierung not in Erhebung.Randomisierung.values:
        return HttpResponseBadRequest("Unbekannte Randomisierungsregel.")
    erhebung.instruktionstext = request.POST.get(
        "instruktionstext", erhebung.instruktionstext
    )
    erhebung.einwilligungstext = request.POST.get(
        "einwilligungstext", erhebung.einwilligungstext
    )
    erhebung.abschlusstext = request.POST.get("abschlusstext", erhebung.abschlusstext)
    erhebung.randomisierung = randomisierung
    erhebung.save(
        update_fields=[
            "instruktionstext",
            "einwilligungstext",
            "abschlusstext",
            "randomisierung",
        ]
    )
    if (
        randomisierung == Erhebung.Randomisierung.FEST
        and "vignetten" in request.POST
    ):
        _feste_reihenfolge_setzen(erhebung, request.POST.getlist("vignetten"))
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def loeschen(request: HttpRequest, pk: int) -> HttpResponse:
    """Löscht einen eigenen Entwurf physisch."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status == Erhebung.Status.ENTWURF:
        erhebung.delete()
    return redirect("erhebungen:liste")


@login_required
@_forschende_erforderlich
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen eigenen Entwurf über dessen Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.finalisieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def zurueckziehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht eine eigene finale Erhebung zurück, wenn ihr Guard es erlaubt."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.zurueckziehen)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def archivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Archiviert eine eigene finale Erhebung über deren Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.archivieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def entarchivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Macht eine eigene archivierte Erhebung wieder final."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.entarchivieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


def teilnehmen(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Legt beim ersten Link-Aufruf eine pseudonyme Teilnahme an oder setzt sie fort."""
    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None:
        bindung = _bindung_anlegen_fuer_laufende_stichprobe(stichprobe)
        tokens: dict[str, str] = request.session.get(
            _TEILNAHME_TOKENS_SESSION_KEY, {}
        )
        tokens[str(teilnahme_link)] = bindung.token
        request.session[_TEILNAHME_TOKENS_SESSION_KEY] = tokens
    if bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:instruktion", teilnahme_link=teilnahme_link)
    return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)


def einwilligung(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Zeigt das Einwilligungstor der Erhebung."""

    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None:
        return redirect("erhebungen:teilnehmen", teilnahme_link=teilnahme_link)
    if request.method == "POST":
        if request.POST.get("einwilligung") != "ja":
            return HttpResponseBadRequest("Bitte willigen Sie in die Teilnahme ein.")
        bindung.teilnahme.einwilligung_erteilt = True
        bindung.teilnahme.save(update_fields=["einwilligung_erteilt"])
        return redirect("erhebungen:instruktion", teilnahme_link=teilnahme_link)
    return render(request, "erhebungen/einwilligung.html", {"erhebung": stichprobe.erhebung})


def instruktion(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Zeigt die Instruktion erst nach erteilter Einwilligung."""

    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None or not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    return render(
        request,
        "erhebungen/instruktion.html",
        {"erhebung": stichprobe.erhebung, "stichprobe": stichprobe},
    )


def spielen(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Startet die nächste gezogene Vignette über den persistenten DB-Sink."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None or not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    if Sitzung.objects.filter(
        teilnahme=bindung.teilnahme, status=Sitzung.Status.LAUFEND
    ).exists():
        return redirect("erhebungen:gespraech", token=bindung.token)
    if not _naechste_sitzung_starten(bindung, stichprobe.erhebung):
        return redirect("erhebungen:abschluss", teilnahme_link=teilnahme_link)
    return redirect("erhebungen:gespraech", token=bindung.token)


def _naechste_sitzung_starten(bindung: Erhebungsbindung, erhebung: Erhebung) -> bool:
    vignette: Vignette | None = naechster_schritt(bindung.teilnahme)
    if vignette is None:
        return False
    kern: Simulationskern | None = vignette.gepinnter_kern
    modell_konfiguration: ModellKonfiguration | None = erhebung.modell_konfiguration
    if kern is None or modell_konfiguration is None:
        raise RuntimeError("Erhebungsvignetten brauchen Kern und Modell-Konfiguration.")
    with transaction.atomic():
        sink: DBSink = DBSink(bindung.teilnahme)
        sitzung_starten(sink, vignette, kern, modell_konfiguration)
        position: int = bindung.vignettenziehungen.get(vignette=vignette).position
        Vignettenposition.objects.create(
            erhebungsbindung=bindung,
            sitzung=sink.sitzung,
            vignette=vignette,
            position=position,
        )
    return True


def _sitzungsnavigation(token: str) -> Sitzungsnavigation:
    # Hält die Erhebungsrouten in der App, der die Erhebungsbindung gehört.

    return Sitzungsnavigation(
        bezeichnung="Erhebung",
        gespraech_url=reverse("erhebungen:gespraech", args=[token]),
        beenden_url=reverse("erhebungen:gespraech_beenden", args=[token]),
        debrief_url=reverse("erhebungen:debrief", args=[token]),
        abbrechen_url=reverse("erhebungen:abbrechen", args=[token]),
    )


def _erhebungssitzung(token: str) -> tuple[Sitzung, Erhebungsbindung]:
    # Löst die laufende Sitzung in ihrer besitzenden Erhebungs-App auf.

    bindung: Erhebungsbindung = get_object_or_404(
        Erhebungsbindung.objects.select_related("stichprobe", "teilnahme"), token=token
    )
    if bindung.stichprobe.phase != Stichprobe.Phase.LAUFEND:
        raise PermissionDenied
    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme"),
        teilnahme=bindung.teilnahme,
        status=Sitzung.Status.LAUFEND,
    )
    return sitzung, bindung


def gespraech(request: HttpRequest, token: str) -> HttpResponse:
    """Führt einen persistierten Gesprächsschritt anonym über das Token aus."""

    sitzung, _bindung = _erhebungssitzung(token)
    return persistiertes_gespraech(request, sitzung, _sitzungsnavigation(token))


def gespraech_beenden(request: HttpRequest, token: str) -> HttpResponse:
    """Zeigt für die tokenaufgelöste Sitzung den Debrief."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, _bindung = _erhebungssitzung(token)
    zeitbudget_anhalten(request, sitzung)
    return persistierten_debrief_anzeigen(
        request, sitzung, _sitzungsnavigation(token)
    )


def abbrechen(request: HttpRequest, token: str) -> HttpResponse:
    """Bricht eine Erhebungssitzung ohne Diagnose ab."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, bindung = _erhebungssitzung(token)
    zeitbudget_anhalten(request, sitzung)
    DBSink.fuer_sitzung(sitzung).status_setzen(Sitzung.Status.ABGEBROCHEN)
    return redirect(
        "erhebungen:instruktion", teilnahme_link=bindung.stichprobe.teilnahme_link
    )


def debrief(request: HttpRequest, token: str) -> HttpResponse:
    """Schließt die Sitzung mit Diagnose und setzt die Erhebung fort."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, bindung = _erhebungssitzung(token)
    uebermittelte_sitzung_pk: str | None = request.POST.get("sitzung_pk")
    if uebermittelte_sitzung_pk != str(sitzung.pk):
        return HttpResponseBadRequest("Der Debrief gehört nicht zu dieser Sitzung.")
    with transaction.atomic():
        sitzung = Sitzung.objects.select_for_update().get(pk=sitzung.pk)
        if sitzung.status != Sitzung.Status.LAUFEND:
            return HttpResponseBadRequest("Der Debrief gehört nicht zu dieser Sitzung.")
        DBSink.fuer_sitzung(sitzung).diagnose_setzen(request.POST["diagnose"])
    if _naechste_sitzung_starten(bindung, bindung.stichprobe.erhebung):
        return redirect("erhebungen:gespraech", token=bindung.token)
    return redirect(
        "erhebungen:abschluss", teilnahme_link=bindung.stichprobe.teilnahme_link
    )


def abschluss(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Zeigt nach allen Vignetten das definierte Ende der Erhebung."""

    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None or not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    return render(request, "erhebungen/abschluss.html", {"erhebung": stichprobe.erhebung})


def _bindung_aus_session(
    request: HttpRequest, stichprobe: Stichprobe
) -> Erhebungsbindung | None:
    """Lädt die zur Stichprobe passende Bindung des aktuellen Browsers."""

    tokens: dict[str, str] = request.session.get(_TEILNAHME_TOKENS_SESSION_KEY, {})
    token: str | None = tokens.get(str(stichprobe.teilnahme_link))
    if token is None:
        return None
    return Erhebungsbindung.objects.select_related("teilnahme").filter(
        stichprobe=stichprobe,
        token=token,
    ).first()


def _bindung_anlegen_fuer_laufende_stichprobe(
    stichprobe: Stichprobe,
) -> Erhebungsbindung:
    """Prüft das Teilnahmefenster und legt die Bindung unter derselben Sperre an."""

    with transaction.atomic():
        stichprobe = get_object_or_404(
            Stichprobe.objects.select_for_update(),
            pk=stichprobe.pk,
        )
        if stichprobe.archiviert or stichprobe.phase != Stichprobe.Phase.LAUFEND:
            raise PermissionDenied
        return Erhebungsbindung.objects.anlegen(stichprobe)


def _laufende_stichprobe(teilnahme_link: UUID) -> Stichprobe:
    """Lädt ausschließlich Stichproben, deren Teilnahmefenster gerade läuft."""

    stichprobe: Stichprobe = get_object_or_404(
        Stichprobe,
        teilnahme_link=teilnahme_link,
    )
    if stichprobe.archiviert or stichprobe.phase != Stichprobe.Phase.LAUFEND:
        raise PermissionDenied
    return stichprobe

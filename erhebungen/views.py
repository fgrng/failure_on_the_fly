"""Öffentlicher Einstieg in pseudonyme Erhebungen."""

from functools import wraps
from typing import Callable, Concatenate, ParamSpec
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render

from .ablauf import naechster_schritt
from .models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsvignette,
    Stichprobe,
    Vignettenposition,
)
from simulation.models import Simulationskern
from sitzungen.models import Sitzung
from sitzungen.orchestrierung import sitzung_starten
from sitzungen.sink import DBSink
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


@login_required
@_forschende_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Listet die eigenen Erhebungen einer Forschenden."""

    return render(
        request,
        "erhebungen/liste.html",
        {"erhebungen": Erhebung.objects.sichtbar_fuer(request.user)},
    )


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
    return render(
        request,
        "erhebungen/detail.html",
        {
            "erhebung": erhebung,
            "vignettenzugehoerigkeiten": erhebung.vignettenzugehoerigkeiten.select_related(
                "vignette", "vignette__historie"
            ),
            "verfuegbare_vignetten": _eigene_finalen_vignetten(request).exclude(
                pk__in=erhebung.vignetten.values("pk")
            ),
            "kann_zurueckziehen": erhebung.kann_zurueckgezogen_werden,
        },
    )


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
    """Finalisiert einen eigenen Entwurf über dessen Modell-Schreibnaht."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    try:
        erhebung.finalisieren()
    except ValidationError as error:
        messages.error(request, error.message)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def zurueckziehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht eine eigene finale Erhebung zurück, wenn ihr Guard es erlaubt."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    try:
        erhebung.zurueckziehen()
    except ValidationError as error:
        messages.error(request, error.message)
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
        return redirect("sitzungen:erhebung_gespraech", token=bindung.token)
    vignette: Vignette | None = naechster_schritt(bindung.teilnahme)
    if vignette is None:
        return redirect("erhebungen:abschluss", teilnahme_link=teilnahme_link)
    kern: Simulationskern | None = vignette.gepinnter_kern
    if kern is None or stichprobe.erhebung.modell_konfiguration is None:
        raise RuntimeError("Erhebungsvignetten brauchen Kern und Modell-Konfiguration.")
    with transaction.atomic():
        sink: DBSink = DBSink(bindung.teilnahme)
        sitzung_starten(sink, vignette, kern, stichprobe.erhebung.modell_konfiguration)
        position: int = bindung.vignettenziehungen.get(vignette=vignette).position
        Vignettenposition.objects.create(
            erhebungsbindung=bindung,
            sitzung=sink.sitzung,
            vignette=vignette,
            position=position,
        )
    return redirect("sitzungen:erhebung_gespraech", token=bindung.token)


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
        if stichprobe.phase != Stichprobe.Phase.LAUFEND:
            raise PermissionDenied
        return Erhebungsbindung.objects.anlegen(stichprobe)


def _laufende_stichprobe(teilnahme_link: UUID) -> Stichprobe:
    """Lädt ausschließlich Stichproben, deren Teilnahmefenster gerade läuft."""

    stichprobe: Stichprobe = get_object_or_404(
        Stichprobe,
        teilnahme_link=teilnahme_link,
    )
    if stichprobe.phase != Stichprobe.Phase.LAUFEND:
        raise PermissionDenied
    return stichprobe

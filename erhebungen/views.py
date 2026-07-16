"""Öffentlicher Einstieg in pseudonyme Erhebungen."""

from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from .models import Erhebungsbindung, Stichprobe

_TEILNAHME_TOKENS_SESSION_KEY = "erhebung_teilnahme_tokens"


def teilnehmen(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Legt beim ersten Link-Aufruf eine pseudonyme Teilnahme an oder setzt sie fort."""
    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    tokens: dict[str, str] = request.session.get(_TEILNAHME_TOKENS_SESSION_KEY, {})
    token: str | None = tokens.get(str(teilnahme_link))
    bindung: Erhebungsbindung | None = None
    if token is not None:
        bindung = Erhebungsbindung.objects.filter(
            stichprobe=stichprobe,
            token=token,
        ).first()
    if bindung is None:
        bindung = Erhebungsbindung.objects.anlegen(stichprobe)
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
    return render(request, "erhebungen/instruktion.html", {"erhebung": stichprobe.erhebung})


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


def _laufende_stichprobe(teilnahme_link: UUID) -> Stichprobe:
    """Lädt ausschließlich Stichproben, deren Teilnahmefenster gerade läuft."""

    stichprobe: Stichprobe = get_object_or_404(
        Stichprobe,
        teilnahme_link=teilnahme_link,
    )
    if stichprobe.phase != Stichprobe.Phase.LAUFEND:
        raise PermissionDenied
    return stichprobe

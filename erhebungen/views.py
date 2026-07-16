"""Öffentlicher Einstieg in pseudonyme Erhebungen."""

from functools import wraps
from typing import Callable, Concatenate, ParamSpec
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .models import Erhebung, Erhebungsbindung, Stichprobe

_TEILNAHME_TOKENS_SESSION_KEY = "erhebung_teilnahme_tokens"
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

    return render(request, "erhebungen/detail.html", {"erhebung": _sichtbare_erhebung(request, pk)})


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


def teilnehmen(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Legt beim ersten Link-Aufruf eine pseudonyme Teilnahme an oder setzt sie fort."""
    stichprobe: Stichprobe = get_object_or_404(
        Stichprobe,
        teilnahme_link=teilnahme_link,
    )
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
    return HttpResponse(status=204)

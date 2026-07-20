"""Views für den privaten Fragebogen-Item-Editor."""

from functools import wraps
from typing import Callable, Concatenate, ParamSpec

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FragebogenItemForm
from .models import FragebogenItem, FragebogenItemHistorie, LikertSkalenpol

_FORSCHUNGS_GRUPPEN: frozenset[str] = frozenset({"Forschende:r", "Administrator:in"})
P = ParamSpec("P")


def _forschende_erforderlich(
    view: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """Schützt eine View des Fragebogen-Editors mit der Forschungsrolle."""

    @wraps(view)
    def geschuetzte_view(
        request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
    ) -> HttpResponse:
        if not request.user.groups.filter(name__in=_FORSCHUNGS_GRUPPEN).exists():
            return HttpResponse(status=403)
        return view(request, *args, **kwargs)

    return geschuetzte_view


def _sichtbares_item(request: HttpRequest, pk: int) -> FragebogenItem:
    """Lädt eine Item-Fassung aus dem Eigentümer-Kreis der eingeloggten Person."""
    return get_object_or_404(
        FragebogenItem.objects.filter(
            historie__in=FragebogenItemHistorie.objects.sichtbar_fuer(request.user)
        ),
        pk=pk,
    )


def _zustand_badge(item: FragebogenItem) -> str:
    """Ordnet Item-Zustände den gemeinsamen Badge-Klassen zu."""
    return {
        FragebogenItem.Zustand.ENTWURF: "draft",
        FragebogenItem.Zustand.FINAL: "final",
        FragebogenItem.Zustand.ARCHIVIERT: "archived",
    }[item.zustand]


@login_required
@_forschende_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Zeigt pro sichtbarer Historie ihre neueste Fassung."""
    historien = FragebogenItemHistorie.objects.sichtbar_fuer(request.user)
    items = []
    for historie in historien:
        item = historie.fragebogenitem_set.latest("pk")
        items.append(
            {
                "item": item,
                "name": historie.name or item.wortlaut or "Unbenannter Entwurf",
                "zustand_badge": _zustand_badge(item),
            }
        )
    return render(request, "fragebogen_items/liste.html", {"items": items})


@login_required
@_forschende_erforderlich
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt eine erste Entwurfsfassung über die Manager-Naht an."""
    form = FragebogenItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = FragebogenItem.objects.anlegen(request.user, **form.cleaned_data)
        return redirect("fragebogen_items:detail", pk=item.pk)
    return render(request, "fragebogen_items/anlegen.html", {"form": form})


@login_required
@_forschende_erforderlich
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine sichtbare Fragebogen-Item-Fassung."""
    return render(
        request,
        "fragebogen_items/detail.html",
        {
            "item": _sichtbares_item(request, pk),
            "likert_skalenpole": LikertSkalenpol.choices,
        },
    )

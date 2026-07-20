"""Views für den privaten Fragebogen-Item-Editor."""

from functools import wraps
from typing import Callable, Concatenate, ParamSpec, TypedDict

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FragebogenItemForm
from .models import FragebogenItem, FragebogenItemHistorie, LikertSkalenpol

_BERECHTIGTE_GRUPPEN: frozenset[str] = frozenset(
    {
        "Forschende:r",
        "Administrator:in",
    }
)
P: ParamSpec = ParamSpec("P")


class ItemZeile(TypedDict):
    """Die für eine Zeile der Item-Bibliothek benötigten Werte."""

    item: FragebogenItem
    bezeichnung: str
    zustand_badge: str


def _forschende_erforderlich(
    view: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    # Schützt eine View des Fragebogen-Editors mit einer berechtigten Rolle.

    @wraps(view)
    def geschuetzte_view(
        request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
    ) -> HttpResponse:
        # Prüft die Gruppenrolle vor dem Aufruf der geschützten View.
        if not request.user.groups.filter(name__in=_BERECHTIGTE_GRUPPEN).exists():
            return HttpResponse(status=403)
        return view(request, *args, **kwargs)

    return geschuetzte_view


def _sichtbares_item(
    request: HttpRequest, pk: int, zustand: str | None = None
) -> FragebogenItem:
    # Lädt eine Item-Fassung aus dem Eigentümer-Kreis der eingeloggten Person.
    items = FragebogenItem.objects.filter(
        historie__in=FragebogenItemHistorie.objects.sichtbar_fuer(request.user)
    )
    if zustand is not None:
        items = items.filter(zustand=zustand)
    return get_object_or_404(items, pk=pk)


def _zustand_badge(item: FragebogenItem) -> str:
    # Ordnet Item-Zustände den gemeinsamen Badge-Klassen zu.
    return {
        FragebogenItem.Zustand.ENTWURF: "draft",
        FragebogenItem.Zustand.FINAL: "final",
        FragebogenItem.Zustand.ARCHIVIERT: "archived",
    }[item.zustand]


@login_required
@_forschende_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Zeigt pro sichtbarer Historie ihre neueste Fassung."""
    sichtbare_historien = FragebogenItemHistorie.objects.sichtbar_fuer(request.user)
    item_zeilen: list[ItemZeile] = []
    for historie in sichtbare_historien:
        item: FragebogenItem = historie.fragebogenitem_set.latest("pk")
        item_zeilen.append(
            {
                "item": item,
                "bezeichnung": historie.name or item.wortlaut or "Unbenannter Entwurf",
                "zustand_badge": _zustand_badge(item),
            }
        )
    return render(request, "fragebogen_items/liste.html", {"item_zeilen": item_zeilen})


@login_required
@_forschende_erforderlich
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt eine erste Entwurfsfassung über die Manager-Naht an."""
    form: FragebogenItemForm = FragebogenItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item: FragebogenItem = FragebogenItem.objects.anlegen(
            request.user, **form.cleaned_data
        )
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


@login_required
@_forschende_erforderlich
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen sichtbaren Entwurf über die Modell-Naht."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item = _sichtbares_item(request, pk, FragebogenItem.Zustand.ENTWURF)
    item.finalisieren()
    return redirect("fragebogen_items:detail", pk=item.pk)

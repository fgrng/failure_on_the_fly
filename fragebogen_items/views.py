"""Views für den privaten Fragebogen-Item-Editor."""

from collections.abc import Callable
from typing import TypedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from konten.navigation import (
    ist_forschende,
    rolle_erforderlich,
)
from konten.eigentuemer_views import eigentuemer_views

from .forms import FragebogenItemForm
from .models import FragebogenItem, FragebogenItemHistorie, LikertSkalenpol


class ItemZeile(TypedDict):
    """Die für eine Zeile der Item-Bibliothek benötigten Werte."""

    item: FragebogenItem
    bezeichnung: str
    zustand_badge: str


_forschende_oder_administratorin_erforderlich = rolle_erforderlich(ist_forschende)


def _sichtbares_item(
    request: HttpRequest,
    pk: int,
    *,
    zustand: FragebogenItem.Zustand | None = None,
) -> FragebogenItem:
    # Lädt eine Item-Fassung aus dem Eigentümer-Kreis der eingeloggten Person.
    items = FragebogenItem.objects.sichtbar_fuer(request.user)
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


def _bezeichnung(item: FragebogenItem) -> str:
    # Benennt eine Fassung über ihre Historie, hilfsweise über den Wortlaut.
    return item.historie.name or item.wortlaut or "Unbenannter Entwurf"


def _lebenszyklus_aktion_ausfuehren(
    request: HttpRequest,
    pk: int,
    zustand: FragebogenItem.Zustand,
    aktion: Callable[[FragebogenItem], None],
) -> HttpResponse:
    # Führt eine zustandsgebundene Aktion aus und zeigt Modellfehler an.
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item: FragebogenItem = _sichtbares_item(request, pk, zustand=zustand)
    try:
        aktion(item)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect("fragebogen_items:detail", pk=item.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Zeigt pro sichtbarer Historie ihre neueste Fassung."""
    sichtbare_historien = (
        FragebogenItemHistorie.objects.sichtbar_fuer(request.user)
        .filter(fragebogenitem__isnull=False)
        .distinct()
    )
    item_zeilen: list[ItemZeile] = []
    for historie in sichtbare_historien:
        item: FragebogenItem = historie.fragebogenitem_set.latest("pk")
        item_zeilen.append(
            {
                "item": item,
                "bezeichnung": _bezeichnung(item),
                "zustand_badge": _zustand_badge(item),
            }
        )
    return render(request, "fragebogen_items/liste.html", {"item_zeilen": item_zeilen})


@login_required
@_forschende_oder_administratorin_erforderlich
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
@_forschende_oder_administratorin_erforderlich
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine sichtbare Fragebogen-Item-Fassung."""
    item: FragebogenItem = _sichtbares_item(request, pk)
    return render(
        request,
        "fragebogen_items/detail.html",
        {
            "item": item,
            "bezeichnung": _bezeichnung(item),
            "zustand_badge": _zustand_badge(item),
            "likert_skalenpole": LikertSkalenpol.choices,
            "kann_entarchiviert_werden": item.kann_entarchiviert_werden(),
        },
    )


@login_required
@_forschende_oder_administratorin_erforderlich
def bearbeiten(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert Typ und Wortlaut eines sichtbaren Entwurfs."""
    item: FragebogenItem = _sichtbares_item(
        request, pk, zustand=FragebogenItem.Zustand.ENTWURF
    )
    form: FragebogenItemForm = FragebogenItemForm(
        request.POST or None,
        initial={
            "typ": item.typ,
            "wortlaut": item.wortlaut,
        },
    )
    if request.method == "POST" and form.is_valid():
        item.typ = form.cleaned_data["typ"]
        item.wortlaut = form.cleaned_data["wortlaut"]
        item.save()
        return redirect("fragebogen_items:detail", pk=item.pk)
    return render(
        request,
        "fragebogen_items/bearbeiten.html",
        {"form": form, "item": item},
    )


@login_required
@_forschende_oder_administratorin_erforderlich
def neue_fassung(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht aus einer finalen Fassung einen bearbeitbaren Folgeentwurf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    finale: FragebogenItem = _sichtbares_item(
        request, pk, zustand=FragebogenItem.Zustand.FINAL
    )
    entwurf: FragebogenItem | None = FragebogenItem.objects.filter(
        historie=finale.historie,
        zustand=FragebogenItem.Zustand.ENTWURF,
    ).first()
    if entwurf is None:
        try:
            entwurf = finale.bearbeiten()
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
            return redirect("fragebogen_items:detail", pk=finale.pk)
    return redirect("fragebogen_items:detail", pk=entwurf.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen sichtbaren Entwurf über die Modell-Naht."""
    return _lebenszyklus_aktion_ausfuehren(
        request, pk, FragebogenItem.Zustand.ENTWURF, FragebogenItem.finalisieren
    )


@login_required
@_forschende_oder_administratorin_erforderlich
def archivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Archiviert eine sichtbare finale Fassung über die Modell-Naht."""
    return _lebenszyklus_aktion_ausfuehren(
        request, pk, FragebogenItem.Zustand.FINAL, FragebogenItem.archivieren
    )


def _kreis_des_items(
    request: HttpRequest, pk: int
) -> tuple[FragebogenItemHistorie, str]:
    # Liefert den Kreis der Item-Historie und die Detailseite der Fassung.
    item: FragebogenItem = _sichtbares_item(request, pk)
    return item.historie, reverse("fragebogen_items:detail", args=[item.pk])


eigentuemerin_hinzufuegen, eigentuemerin_entfernen = eigentuemer_views(
    rolle_erforderlich=_forschende_oder_administratorin_erforderlich,
    aufloesen=_kreis_des_items,
    liste="fragebogen_items:liste",
)


@login_required
@_forschende_oder_administratorin_erforderlich
def entarchivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Macht eine sichtbare archivierte Fassung wieder final."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item = _sichtbares_item(request, pk, zustand=FragebogenItem.Zustand.ARCHIVIERT)
    if not item.kann_entarchiviert_werden():
        raise Http404
    item.entarchivieren()
    return redirect("fragebogen_items:detail", pk=item.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def loeschen(request: HttpRequest, pk: int) -> HttpResponse:
    """Löscht einen sichtbaren Entwurf physisch über die Modell-Naht."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item = _sichtbares_item(request, pk, zustand=FragebogenItem.Zustand.ENTWURF)
    item.delete()
    return redirect("fragebogen_items:liste")

"""Views für den privaten Fragebogen-Item-Editor."""

from functools import wraps
from typing import Callable, Concatenate, ParamSpec, TypedDict

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from konten.models import Konto

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
    request: HttpRequest,
    pk: int,
    *,
    zustand: FragebogenItem.Zustand | None = None,
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


def _ist_neueste_nichtarchivierte_fassung(item: FragebogenItem) -> bool:
    # Prüft, ob eine Fassung die aktuelle Spitze ihrer Historie ist.
    return item.zustand != FragebogenItem.Zustand.ARCHIVIERT and not (
        FragebogenItem.objects.filter(historie=item.historie, pk__gt=item.pk)
        .exclude(zustand=FragebogenItem.Zustand.ARCHIVIERT)
        .exists()
    )


@login_required
@_forschende_erforderlich
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
    item: FragebogenItem = _sichtbares_item(request, pk)
    eigentuemerinnen: list[Konto] = list(item.historie.eigentuemerinnen.all())
    return render(
        request,
        "fragebogen_items/detail.html",
        {
            "item": item,
            "likert_skalenpole": LikertSkalenpol.choices,
            "ist_neueste_nichtarchivierte_fassung": (
                _ist_neueste_nichtarchivierte_fassung(item)
            ),
            "eigentuemerinnen": eigentuemerinnen,
            "hat_mehrere_eigentuemerinnen": len(eigentuemerinnen) > 1,
            "moegliche_koautorinnen": Konto.objects.filter(
                groups__name__in=_BERECHTIGTE_GRUPPEN
            )
            .exclude(fragebogenitemhistorie=item.historie)
            .distinct(),
        },
    )


@login_required
@_forschende_erforderlich
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
@_forschende_erforderlich
def neue_fassung(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht aus einer finalen Fassung einen bearbeitbaren Folgeentwurf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    finale: FragebogenItem = _sichtbares_item(
        request, pk, zustand=FragebogenItem.Zustand.FINAL
    )
    if not _ist_neueste_nichtarchivierte_fassung(finale):
        raise Http404
    entwurf: FragebogenItem | None = FragebogenItem.objects.filter(
        historie=finale.historie,
        zustand=FragebogenItem.Zustand.ENTWURF,
    ).first()
    if entwurf is None:
        entwurf = finale.bearbeiten()
    return redirect("fragebogen_items:detail", pk=entwurf.pk)


@login_required
@_forschende_erforderlich
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen sichtbaren Entwurf über die Modell-Naht."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item = _sichtbares_item(
        request,
        pk,
        zustand=FragebogenItem.Zustand.ENTWURF,
    )
    item.finalisieren()
    return redirect("fragebogen_items:detail", pk=item.pk)


@login_required
@_forschende_erforderlich
def archivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Archiviert eine sichtbare finale Fassung über die Modell-Naht."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item = _sichtbares_item(request, pk, zustand=FragebogenItem.Zustand.FINAL)
    item.archivieren()
    return redirect("fragebogen_items:detail", pk=item.pk)


@login_required
@_forschende_erforderlich
def koautorin_hinzufuegen(request: HttpRequest, pk: int) -> HttpResponse:
    """Teilt eine sichtbare Item-Historie mit einer weiteren Forschenden."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item: FragebogenItem = _sichtbares_item(request, pk)
    konto: Konto = get_object_or_404(
        Konto.objects.filter(groups__name__in=_BERECHTIGTE_GRUPPEN).distinct(),
        pk=request.POST.get("konto"),
    )
    item.historie.eigentuemerinnen.add(konto)
    return redirect("fragebogen_items:detail", pk=item.pk)


@login_required
@_forschende_erforderlich
def entarchivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Macht eine sichtbare archivierte Fassung wieder final."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item = _sichtbares_item(request, pk, zustand=FragebogenItem.Zustand.ARCHIVIERT)
    item.entarchivieren()
    return redirect("fragebogen_items:detail", pk=item.pk)


@login_required
@_forschende_erforderlich
def loeschen(request: HttpRequest, pk: int) -> HttpResponse:
    """Löscht einen sichtbaren Entwurf physisch über die Modell-Naht."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item = _sichtbares_item(request, pk, zustand=FragebogenItem.Zustand.ENTWURF)
    item.delete()
    return redirect("fragebogen_items:liste")


@login_required
@_forschende_erforderlich
def koautorin_entfernen(request: HttpRequest, pk: int, konto_pk: int) -> HttpResponse:
    """Entzieht einer Ko-Autorin den Zugang zu einer sichtbaren Item-Historie."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    item: FragebogenItem = _sichtbares_item(request, pk)
    if item.historie.eigentuemerinnen.count() > 1:
        item.historie.eigentuemerinnen.remove(konto_pk)
    return redirect("fragebogen_items:detail", pk=item.pk)

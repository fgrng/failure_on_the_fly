"""Views für den privaten Vignetten-Editor."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VignetteForm, zufaellige_akteure
from .models import Vignette, Vignettenhistorie


def _fallback_label(vignette: Vignette) -> str:
    """Leitet ein lesbares Label aus dem Unterrichtskontext ab."""
    return f"{vignette.fach}: {vignette.thema} (Klasse {vignette.klassenstufe})"


def _zustand_badge(vignette: Vignette) -> str:
    """Ordnet Modellzustände den gemeinsamen Badge-Klassen zu."""
    return {
        Vignette.Zustand.ENTWURF: "draft",
        Vignette.Zustand.FINAL: "final",
        Vignette.Zustand.ARCHIVIERT: "archived",
    }[vignette.zustand]


def _sichtbare_fassung_laden(
    request: HttpRequest, pk: int, zustand: Vignette.Zustand
) -> Vignette:
    """Lädt eine Fassung im erwarteten Zustand aus dem Eigentümer-Kreis."""
    return get_object_or_404(
        Vignette.objects.filter(
            historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user),
            zustand=zustand,
        ),
        pk=pk,
    )


@login_required
def liste(request: HttpRequest) -> HttpResponse:
    """Zeigt die privaten Vignettenhistorien der eingeloggten Person."""
    historien: list[dict[str, object]] = []
    for historie in Vignettenhistorie.objects.sichtbar_fuer(request.user):
        neueste_fassung: Vignette = historie.vignette_set.latest("pk")
        historien.append(
            {
                "label": historie.name or _fallback_label(neueste_fassung),
                "fassung_pk": neueste_fassung.pk,
                "zustand": neueste_fassung.get_zustand_display(),
                "zustand_badge": _zustand_badge(neueste_fassung),
            }
        )
    return render(request, "vignetten/liste.html", {"historien": historien})


@login_required
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt eine Vignette mit dem vom Manager gewählten Kern an."""
    if request.method == "POST":
        form: VignetteForm = VignetteForm(request.POST, request.FILES)
        if form.is_valid():
            vignette: Vignette = Vignette.objects.anlegen(request.user)
            for feldname, wert in form.cleaned_data.items():
                setattr(vignette, feldname, wert)
            vignette.save()
            return redirect("vignetten:detail", pk=vignette.pk)
    else:
        form = VignetteForm(initial=zufaellige_akteure())
    return render(request, "vignetten/anlegen.html", {"form": form})


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt die Rohfelder einer für die Person sichtbaren Vignettenfassung."""
    vignette: Vignette = get_object_or_404(
        Vignette.objects.filter(
            historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user)
        ),
        pk=pk,
    )
    return render(
        request,
        "vignetten/detail.html",
        {"vignette": vignette, "zustand_badge": _zustand_badge(vignette)},
    )


@login_required
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen eigenen Entwurf über dessen Modell-Schreibnaht."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    vignette: Vignette = _sichtbare_fassung_laden(
        request, pk, Vignette.Zustand.ENTWURF
    )
    try:
        vignette.finalisieren()
    except ValidationError as error:
        messages.error(request, error.message)
    return redirect("vignetten:detail", pk=vignette.pk)


@login_required
def archivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Archiviert eine eigene finale Fassung."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    vignette: Vignette = _sichtbare_fassung_laden(
        request, pk, Vignette.Zustand.FINAL
    )
    try:
        vignette.archivieren()
    except ValidationError as error:
        messages.error(request, error.message)
    return redirect("vignetten:detail", pk=vignette.pk)


@login_required
def entarchivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Macht eine eigene archivierte Fassung wieder final."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    vignette: Vignette = _sichtbare_fassung_laden(
        request, pk, Vignette.Zustand.ARCHIVIERT
    )
    try:
        vignette.entarchivieren()
    except ValidationError as error:
        messages.error(request, error.message)
    return redirect("vignetten:detail", pk=vignette.pk)


@login_required
def vorspulen(request: HttpRequest, pk: int) -> HttpResponse:
    """Pinnt einen eigenen Entwurf auf den aktuellen finalen Kern."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    vignette: Vignette = _sichtbare_fassung_laden(
        request, pk, Vignette.Zustand.ENTWURF
    )
    try:
        vignette.vorspulen()
    except ValidationError as error:
        messages.error(request, error.message)
    return redirect("vignetten:detail", pk=vignette.pk)


@login_required
def neue_fassung(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht aus einer finalen Fassung einen bearbeitbaren Folgeentwurf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    finale: Vignette = _sichtbare_fassung_laden(
        request, pk, Vignette.Zustand.FINAL
    )
    entwurf: Vignette | None = Vignette.objects.filter(
        historie=finale.historie,
        zustand=Vignette.Zustand.ENTWURF,
    ).first()
    if entwurf is None:
        try:
            entwurf = finale.bearbeiten()
        except ValidationError as error:
            messages.error(request, error.message)
            return redirect("vignetten:detail", pk=finale.pk)
    return redirect("vignetten:detail", pk=entwurf.pk)


reversionieren = neue_fassung


@login_required
def bearbeiten(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert die Inhaltsfelder eines eigenen Entwurfs."""
    vignette: Vignette = _sichtbare_fassung_laden(
        request, pk, Vignette.Zustand.ENTWURF
    )
    if request.method == "POST":
        form: VignetteForm = VignetteForm(
            request.POST, request.FILES, instance=vignette
        )
        if form.is_valid():
            form.save()
            return redirect("vignetten:detail", pk=vignette.pk)
    else:
        form = VignetteForm(instance=vignette)
    return render(request, "vignetten/bearbeiten.html", {"form": form})

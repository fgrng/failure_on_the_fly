"""Views für den privaten Vignetten-Editor."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FinalisierenForm, VignetteForm, zufaellige_akteure
from .models import Vignette, Vignettenhistorie


def _fallback_label(vignette: Vignette) -> str:
    """Leitet ein lesbares Label aus dem Unterrichtskontext ab."""
    return f"{vignette.fach}: {vignette.thema} (Klasse {vignette.klassenstufe})"


def _sichtbaren_entwurf_laden(request: HttpRequest, pk: int) -> Vignette:
    """Lädt einen bearbeitbaren Entwurf aus dem Eigentümer-Kreis."""
    return get_object_or_404(
        Vignette.objects.filter(
            historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user),
            zustand=Vignette.Zustand.ENTWURF,
        ),
        pk=pk,
    )


def _sichtbare_finale_fassung_laden(request: HttpRequest, pk: int) -> Vignette:
    """Lädt eine finale Fassung aus dem Eigentümer-Kreis."""
    return get_object_or_404(
        Vignette.objects.filter(
            historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user),
            zustand=Vignette.Zustand.FINAL,
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
        {"vignette": vignette, "finalisieren_form": FinalisierenForm()},
    )


@login_required
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen eigenen Entwurf über dessen Modell-Schreibnaht."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    vignette: Vignette = _sichtbaren_entwurf_laden(request, pk)
    form: FinalisierenForm = FinalisierenForm(request.POST)
    try:
        vignette.finalisieren()
    except ValidationError as error:
        form.add_error(None, error)
        return render(
            request,
            "vignetten/detail.html",
            {"vignette": vignette, "finalisieren_form": form},
        )
    return redirect("vignetten:detail", pk=vignette.pk)


@login_required
def reversionieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht aus einer finalen Fassung einen bearbeitbaren Folgeentwurf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    finale: Vignette = _sichtbare_finale_fassung_laden(request, pk)
    entwurf: Vignette | None = Vignette.objects.filter(
        historie=finale.historie,
        zustand=Vignette.Zustand.ENTWURF,
    ).first()
    if entwurf is None:
        entwurf = finale.bearbeiten()
    return redirect("vignetten:bearbeiten", pk=entwurf.pk)


@login_required
def bearbeiten(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert die Inhaltsfelder eines eigenen Entwurfs."""
    vignette: Vignette = _sichtbaren_entwurf_laden(request, pk)
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

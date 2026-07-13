"""Views für den privaten Vignetten-Editor."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VignetteForm, zufaellige_akteure
from .models import Vignette, Vignettenhistorie


def _fallback_label(vignette: Vignette) -> str:
    """Leitet ein lesbares Label aus dem Unterrichtskontext ab."""
    return f"{vignette.fach}: {vignette.thema} (Klasse {vignette.klassenstufe})"


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
    return render(request, "vignetten/detail.html", {"vignette": vignette})


@login_required
def bearbeiten(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert die Inhaltsfelder eines eigenen Entwurfs."""
    vignette: Vignette = get_object_or_404(
        Vignette.objects.filter(
            historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user),
            zustand=Vignette.Zustand.ENTWURF,
        ),
        pk=pk,
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

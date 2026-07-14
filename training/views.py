"""Views für die Ausbilder-UI der Trainings."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TrainingForm
from .models import Training
from vignetten.models import Vignette, Vignettenhistorie


def _eigene_finalen_vignetten(request: HttpRequest):
    """Liefert einbindbare Fassungen aus dem Eigentümer-Kreis."""
    return Vignette.objects.einbindbar().filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user)
    )


@login_required
def liste(request: HttpRequest) -> HttpResponse:
    """Listet die für die eingeloggte Person sichtbaren Trainings."""
    return render(
        request,
        "training/liste.html",
        {"trainings": Training.objects.sichtbar_fuer(request.user)},
    )


@login_required
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt ein Training für die eingeloggte Person an."""
    form: TrainingForm = TrainingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        training: Training = form.save(commit=False)
        training.eigentuemerin = request.user
        training.save()
        return redirect("training:detail", pk=training.pk)
    return render(request, "training/anlegen.html", {"form": form})


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt ein sichtbares Training."""
    training: Training = get_object_or_404(
        Training.objects.sichtbar_fuer(request.user), pk=pk
    )
    return render(
        request,
        "training/detail.html",
        {
            "training": training,
            "vignetten": _eigene_finalen_vignetten(request),
        },
    )


@login_required
def vignette_hinzufuegen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Nimmt eine eigene finale Vignette in ein sichtbares Training auf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = get_object_or_404(
        Training.objects.sichtbar_fuer(request.user), pk=pk
    )
    vignette: Vignette = get_object_or_404(
        _eigene_finalen_vignetten(request), pk=vignette_pk
    )
    training.vignetten.add(vignette)
    return redirect("training:detail", pk=training.pk)


@login_required
def vignette_entfernen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Entfernt eine gebundene Vignette aus einem sichtbaren Training."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = get_object_or_404(
        Training.objects.sichtbar_fuer(request.user), pk=pk
    )
    vignette: Vignette = get_object_or_404(training.vignetten, pk=vignette_pk)
    training.vignetten.remove(vignette)
    return redirect("training:detail", pk=training.pk)


@login_required
def veroeffentlichen(request: HttpRequest, pk: int) -> HttpResponse:
    """Veröffentlicht einen sichtbaren Trainingsentwurf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = get_object_or_404(
        Training.objects.sichtbar_fuer(request.user), pk=pk
    )
    training.veroeffentlichen()
    return redirect("training:detail", pk=training.pk)

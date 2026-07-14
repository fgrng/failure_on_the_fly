"""Views für Trainingskatalog und Ausbilder-UI."""

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TrainingForm
from .models import Training
from vignetten.models import Vignette, Vignettenhistorie


def _eigene_finalen_vignetten(request: HttpRequest) -> QuerySet[Vignette]:
    """Liefert einbindbare Fassungen aus dem Eigentümer-Kreis."""

    return Vignette.objects.einbindbar().filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user)
    )


def _sichtbares_training(request: HttpRequest, pk: int) -> Training:
    """Lädt ein für die eingeloggte Person sichtbares Training."""

    return get_object_or_404(Training.objects.sichtbar_fuer(request.user), pk=pk)


def _veroeffentlichtes_training(pk: int) -> Training:
    """Lädt ein Training, das im offenen Katalog sichtbar ist."""
    return get_object_or_404(Training.objects.veroeffentlicht(), pk=pk)


@login_required
def katalog(request: HttpRequest) -> HttpResponse:
    """Zeigt allen eingeloggten Konten veröffentlichte Trainings."""
    return render(
        request,
        "training/katalog.html",
        {"trainings": Training.objects.veroeffentlicht()},
    )


@login_required
def liste(request: HttpRequest) -> HttpResponse:
    """Listet die für die eingeloggte Person sichtbaren eigenen Trainings."""
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
        return redirect("training:kuratieren", pk=training.pk)
    return render(request, "training/anlegen.html", {"form": form})


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt die frei wählbaren Vignetten eines veröffentlichten Trainings."""
    training: Training = _veroeffentlichtes_training(pk)
    vignetten: QuerySet[Vignette] = training.vignetten.filter(
        zustand=Vignette.Zustand.FINAL
    )
    return render(
        request,
        "training/detail.html",
        {"training": training, "vignetten": vignetten},
    )


@login_required
def kuratieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt ein eigenes Training zur Kuratierung."""
    training: Training = _sichtbares_training(request, pk)
    return render(
        request,
        "training/kuratieren.html",
        {
            "training": training,
            "verfuegbare_vignetten": _eigene_finalen_vignetten(request).exclude(
                pk__in=training.vignetten.values("pk")
            ),
        },
    )


@login_required
def vignette_hinzufuegen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Nimmt eine eigene finale Vignette in ein sichtbares Training auf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    vignette: Vignette = get_object_or_404(
        _eigene_finalen_vignetten(request), pk=vignette_pk
    )
    training.vignetten.add(vignette)
    return redirect("training:kuratieren", pk=training.pk)


@login_required
def vignette_entfernen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Entfernt eine gebundene Vignette aus einem sichtbaren Training."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    vignette: Vignette = get_object_or_404(training.vignetten, pk=vignette_pk)
    training.vignetten.remove(vignette)
    return redirect("training:kuratieren", pk=training.pk)


@login_required
def veroeffentlichen(request: HttpRequest, pk: int) -> HttpResponse:
    """Veröffentlicht einen sichtbaren Trainingsentwurf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    training.veroeffentlichen()
    return redirect("training:kuratieren", pk=training.pk)


@login_required
def wahl(request: HttpRequest, training_pk: int, vignette_pk: int) -> HttpResponse:
    """Bestätigt die Wahl einer Vignette aus einem Training."""
    training: Training = _veroeffentlichtes_training(training_pk)
    vignette: Vignette = get_object_or_404(
        training.vignetten.filter(zustand=Vignette.Zustand.FINAL), pk=vignette_pk
    )
    return render(
        request,
        "training/wahl.html",
        {"training": training, "vignette": vignette},
    )

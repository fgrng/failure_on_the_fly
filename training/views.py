"""Lesender Katalog für veröffentlichte Trainings."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Training


@login_required
def katalog(request: HttpRequest) -> HttpResponse:
    """Zeigt allen eingeloggten Konten veröffentlichte Trainings."""
    trainings = Training.objects.filter(zustand=Training.Zustand.VEROEFFENTLICHT)
    return render(request, "training/katalog.html", {"trainings": trainings})


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt die frei wählbaren Vignetten eines veröffentlichten Trainings."""
    training = get_object_or_404(
        Training.objects.filter(zustand=Training.Zustand.VEROEFFENTLICHT), pk=pk
    )
    return render(request, "training/detail.html", {"training": training})


@login_required
def wahl(request: HttpRequest, training_pk: int, vignette_pk: int) -> HttpResponse:
    """Bestätigt die Wahl; die persistierte Sitzung folgt mit T4."""
    training = get_object_or_404(
        Training.objects.filter(zustand=Training.Zustand.VEROEFFENTLICHT),
        pk=training_pk,
    )
    vignette = get_object_or_404(training.vignetten, pk=vignette_pk)
    return render(request, "training/wahl.html", {"training": training, "vignette": vignette})

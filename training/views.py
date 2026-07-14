"""Views für Trainingskatalog und Ausbilder-UI."""

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TrainingForm
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.orchestrierung import sitzung_starten
from sitzungen.rahmen import rahmen_rendern
from sitzungen.sink import DBSink

from .models import Training, Trainingsbindung
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
    """Bestätigt oder startet die Wahl einer Vignette aus einem Training."""
    training: Training = _veroeffentlichtes_training(training_pk)
    vignette: Vignette = get_object_or_404(
        training.vignetten.filter(zustand=Vignette.Zustand.FINAL), pk=vignette_pk
    )
    if request.method == "POST":
        return _sitzung_starten(request, training, vignette)
    return render(
        request,
        "training/wahl.html",
        {"training": training, "vignette": vignette},
    )


def _sitzung_starten(
    request: HttpRequest, training: Training, vignette: Vignette
) -> HttpResponse:
    """Bindet das Konto atomar und startet die Sitzung über den DB-Sink."""

    with transaction.atomic():
        bindung: Trainingsbindung | None = Trainingsbindung.objects.filter(
            training=training, konto=request.user
        ).select_related("teilnahme").first()
        if bindung is None:
            from sitzungen.models import Teilnahme

            try:
                with transaction.atomic():
                    bindung = Trainingsbindung.objects.create(
                        teilnahme=Teilnahme.objects.create(),
                        training=training,
                        konto=request.user,
                    )
            except IntegrityError:
                bindung = Trainingsbindung.objects.select_related("teilnahme").get(
                    training=training, konto=request.user
                )
        kern: Simulationskern | None = vignette.gepinnter_kern
        if kern is None:
            raise RuntimeError("Trainingsvignetten brauchen einen gepinnten Simulationskern.")
        sink: DBSink = DBSink(bindung.teilnahme)
        sitzung_starten(
            sink,
            vignette,
            kern,
            ModellKonfiguration.objects.aktive(),
        )
    request.session["training_sitzung_pk"] = sink.sitzung.pk
    if vignette.budget_typ == Vignette.BudgetTyp.ZEIT:
        request.session["training_verbrauchte_zeit"] = 0.0
    return render(
        request,
        "sitzungen/training_einleitung.html",
        {"einleitung": rahmen_rendern(kern.rahmenhandlung_einleitung, vignette)},
    )

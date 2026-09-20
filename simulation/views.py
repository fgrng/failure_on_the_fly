"""Ansichten für den Simulationskern."""

from collections.abc import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from konten.navigation import administratorin_erforderlich, autorin_erforderlich


from .forms import SimulationskernForm
from .models import (
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_RAHMEN,
    AktiveModellKonfiguration,
    ModellKonfiguration,
    Simulationskern,
)


def _finale_fassung() -> Simulationskern | None:
    # Liefert die eine finale Fassung, die der Kern trägt, sobald es sie gibt.

    return Simulationskern.objects.filter(zustand=Simulationskern.Zustand.FINAL).first()


def _archivierte_fassungen() -> QuerySet[Simulationskern]:
    # Liefert die überholten Fassungen, die zuletzt überholte zuerst.

    return Simulationskern.objects.filter(
        zustand=Simulationskern.Zustand.ARCHIVIERT
    ).order_by("-finalisiert_am", "-pk")


def _kern_kontext() -> dict[str, object]:
    """Liefert die gemeinsame Anzeige-Referenz für Kern-Ansichten."""
    try:
        modell_konfiguration: ModellKonfiguration | None = (
            ModellKonfiguration.objects.aktive()
        )
    except AktiveModellKonfiguration.DoesNotExist:
        modell_konfiguration = None
    return {
        "modell_konfiguration": modell_konfiguration,
        "prompt_platzhalter": sorted(VERTRAG_PROMPT),
        "prompt_platzhalter_mit_umgebung": PROMPT_PLATZHALTER_MIT_UMGEBUNG,
        "rahmen_platzhalter": sorted(VERTRAG_RAHMEN),
    }


def _fassung_im_zustand_laden(
    request: HttpRequest,
    pk: int,
    zustand: Simulationskern.Zustand,
) -> Simulationskern | None:
    # Lädt eine Fassung im erwarteten Zustand oder erklärt die Ablehnung.

    simulationskern: Simulationskern = get_object_or_404(Simulationskern, pk=pk)
    if simulationskern.zustand != zustand:
        messages.error(request, "Diese Kern-Fassung hat nicht den erwarteten Zustand.")
        return None
    return simulationskern


def _lebenszyklus_aktion_ausfuehren(
    request: HttpRequest,
    pk: int,
    zustand: Simulationskern.Zustand,
    aktion: Callable[[Simulationskern], object],
) -> HttpResponse:
    # Führt eine zustandsgebundene Aktion aus und zeigt Modellfehler an.

    simulationskern: Simulationskern | None = _fassung_im_zustand_laden(
        request, pk, zustand
    )
    if simulationskern is None:
        return redirect("simulation:kern_verwalten")
    try:
        aktion(simulationskern)
    except (RuntimeError, ValueError, ValidationError) as error:
        if isinstance(error, ValidationError):
            messages.error(request, "; ".join(error.messages))
        else:
            messages.error(request, str(error))
    return redirect("simulation:kern_verwalten")


@login_required
@autorin_erforderlich
def kern(request: HttpRequest) -> HttpResponse:
    """Zeigt die finale Kern-Fassung und die aktive Modell-Konfiguration."""
    simulationskern: Simulationskern | None = _finale_fassung()
    return render(
        request,
        "simulation/kern.html",
        {
            "simulationskern": simulationskern,
            **_kern_kontext(),
        },
    )


@administratorin_erforderlich
def kern_verwalten(request: HttpRequest) -> HttpResponse:
    """Zeigt alle Kern-Fassungen für die Administration."""
    return render(
        request,
        "simulation/kern_verwalten.html",
        {
            "entwurf": Simulationskern.objects.filter(
                zustand=Simulationskern.Zustand.ENTWURF
            ).first(),
            "finale_fassung": _finale_fassung(),
            "archivierte_fassungen": _archivierte_fassungen(),
            **_kern_kontext(),
        },
    )


@administratorin_erforderlich
def kern_bearbeiten(request: HttpRequest, pk: int) -> HttpResponse:
    """Bearbeitet die Inhaltsfelder eines Kern-Entwurfs."""
    simulationskern: Simulationskern = get_object_or_404(
        Simulationskern.objects.filter(zustand=Simulationskern.Zustand.ENTWURF),
        pk=pk,
    )
    form: SimulationskernForm
    if request.method == "POST":
        form = SimulationskernForm(request.POST, instance=simulationskern)
        if form.is_valid():
            form.save()
            return redirect("simulation:kern_verwalten")
    else:
        form = SimulationskernForm(instance=simulationskern)
    return render(
        request,
        "simulation/kern_bearbeiten.html",
        {"form": form, "simulationskern": simulationskern, **_kern_kontext()},
    )


@administratorin_erforderlich
@require_POST
def neue_fassung(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht aus einer finalen Kern-Fassung einen Entwurf."""
    return _lebenszyklus_aktion_ausfuehren(
        request,
        pk,
        Simulationskern.Zustand.FINAL,
        Simulationskern.bearbeiten,
    )


@administratorin_erforderlich
@require_POST
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen Kern-Entwurf."""
    return _lebenszyklus_aktion_ausfuehren(
        request,
        pk,
        Simulationskern.Zustand.ENTWURF,
        Simulationskern.finalisieren,
    )


@administratorin_erforderlich
@require_POST
def verwerfen(request: HttpRequest, pk: int) -> HttpResponse:
    """Verwirft einen Kern-Entwurf."""
    return _lebenszyklus_aktion_ausfuehren(
        request,
        pk,
        Simulationskern.Zustand.ENTWURF,
        Simulationskern.delete,
    )

"""Ansichten für den Simulationskern."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from konten.navigation import administratorin_erforderlich, autorin_erforderlich

from .models import (
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_RAHMEN,
    AktiveModellKonfiguration,
    ModellKonfiguration,
    Simulationskern,
)


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
    """Lädt eine Fassung im erwarteten Zustand oder erklärt die Ablehnung."""
    simulationskern: Simulationskern = get_object_or_404(Simulationskern, pk=pk)
    if simulationskern.zustand != zustand:
        messages.error(request, "Diese Kern-Fassung hat nicht den erwarteten Zustand.")
        return None
    return simulationskern


def _modellfehler_als_meldung(
    request: HttpRequest, error: ValueError | ValidationError
) -> None:
    """Übersetzt Modellfehler der Lebenszyklusgesten in Übersichtsmeldungen."""
    if isinstance(error, ValidationError):
        messages.error(request, "; ".join(error.messages))
    else:
        messages.error(request, str(error))


@login_required
@autorin_erforderlich
def kern(request: HttpRequest) -> HttpResponse:
    """Zeigt die jüngste finale Kern-Fassung und aktive Modell-Konfiguration."""
    simulationskern: Simulationskern | None = (
        Simulationskern.objects.filter(zustand=Simulationskern.Zustand.FINAL)
        .order_by("-finalisiert_am", "-pk")
        .first()
    )
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
            "kann_verwalten": True,
            "finale_fassungen": Simulationskern.objects.filter(
                zustand=Simulationskern.Zustand.FINAL
            ).order_by("-finalisiert_am", "-pk"),
            "archivierte_fassungen": Simulationskern.objects.filter(
                zustand=Simulationskern.Zustand.ARCHIVIERT
            ).order_by("-finalisiert_am", "-pk"),
            **_kern_kontext(),
        },
    )


@administratorin_erforderlich
@require_POST
def neue_fassung(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht aus einer finalen Kern-Fassung einen Entwurf."""
    simulationskern: Simulationskern | None = _fassung_im_zustand_laden(
        request, pk, Simulationskern.Zustand.FINAL
    )
    if simulationskern is not None:
        try:
            simulationskern.bearbeiten()
        except (ValueError, ValidationError) as error:
            _modellfehler_als_meldung(request, error)
    return redirect("simulation:kern_verwalten")


@administratorin_erforderlich
@require_POST
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen Kern-Entwurf."""
    simulationskern: Simulationskern | None = _fassung_im_zustand_laden(
        request, pk, Simulationskern.Zustand.ENTWURF
    )
    if simulationskern is not None:
        try:
            simulationskern.finalisieren()
        except (ValueError, ValidationError) as error:
            _modellfehler_als_meldung(request, error)
    return redirect("simulation:kern_verwalten")


@administratorin_erforderlich
@require_POST
def verwerfen(request: HttpRequest, pk: int) -> HttpResponse:
    """Verwirft einen Kern-Entwurf."""
    simulationskern: Simulationskern | None = _fassung_im_zustand_laden(
        request, pk, Simulationskern.Zustand.ENTWURF
    )
    if simulationskern is not None:
        simulationskern.delete()
    return redirect("simulation:kern_verwalten")

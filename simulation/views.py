"""Schreibgeschützte Views für den Simulationskern."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

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
            "finale_fassungen": Simulationskern.objects.filter(
                zustand=Simulationskern.Zustand.FINAL
            ).order_by("-finalisiert_am", "-pk"),
            "archivierte_fassungen": Simulationskern.objects.filter(
                zustand=Simulationskern.Zustand.ARCHIVIERT
            ).order_by("-finalisiert_am", "-pk"),
            **_kern_kontext(),
        },
    )

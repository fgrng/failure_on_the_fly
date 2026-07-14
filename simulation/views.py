"""Schreibgeschützte Views für den Simulationskern."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import AktiveModellKonfiguration, ModellKonfiguration, Simulationskern


@login_required
def kern(request: HttpRequest) -> HttpResponse:
    """Zeigt die jüngste finale Kern-Fassung und aktive Modell-Konfiguration."""
    simulationskern: Simulationskern | None = (
        Simulationskern.objects.filter(zustand=Simulationskern.Zustand.FINAL)
        .order_by("-finalisiert_am", "-pk")
        .first()
    )
    try:
        modell_konfiguration: ModellKonfiguration | None = (
            ModellKonfiguration.objects.aktive()
        )
    except AktiveModellKonfiguration.DoesNotExist:
        modell_konfiguration = None
    return render(
        request,
        "simulation/kern.html",
        {
            "simulationskern": simulationskern,
            "modell_konfiguration": modell_konfiguration,
        },
    )

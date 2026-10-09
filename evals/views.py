"""Auslösen und Ansicht des Evallaufs einer Vignettenfassung."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from konten.navigation import autorin_erforderlich
from simulation.models import evals_verfuegbar
from vignetten.models import Vignette

from .models import Evallauf


def _zahl(wert: str | None) -> int | None:
    # Eine Auswahl aus der Adresse; Unlesbares gilt als nicht gewählt.

    try:
        return int(wert or "")
    except ValueError:
        return None


def _fassung_laden(request: HttpRequest, pk: int) -> Vignette:
    # Ohne verfügbare Evals gibt es die Route nicht; fremde Fassungen auch nicht.

    if not evals_verfuegbar():
        raise Http404
    return get_object_or_404(Vignette.objects.sichtbar_fuer(request.user), pk=pk)


@login_required
@autorin_erforderlich
def evallauf(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt Zustand, Übersicht und ein gewähltes Evalgespräch des Evallaufs.

    `input` und `wiederholung` wählen das Gespräch; neu laden aktualisiert den Stand.
    """

    vignette: Vignette = _fassung_laden(request, pk)
    lauf: Evallauf | None = (
        Evallauf.objects.filter(vignette=vignette)
        .select_related(
            "katalog",
            "schuelerin_konfiguration",
            "lehrperson_konfiguration",
            "bewerter_konfiguration",
        )
        .first()
    )
    return render(
        request,
        "evals/evallauf.html",
        {
            "vignette": vignette,
            "lauf": lauf,
            "uebersicht": lauf.uebersicht() if lauf else [],
            "einsicht": lauf.einsicht(
                _zahl(request.GET.get("input")), _zahl(request.GET.get("wiederholung"))
            )
            if lauf
            else None,
            "startbar": vignette.zustand != Vignette.Zustand.ARCHIVIERT
            and (lauf is None or not lauf.ist_offen),
        },
    )


@login_required
@autorin_erforderlich
@require_POST
def starten(request: HttpRequest, pk: int) -> HttpResponse:
    """Löst einen Evallauf aus; eine abgewiesene Prüfung kommt als Meldung zurück."""

    vignette: Vignette = _fassung_laden(request, pk)
    try:
        Evallauf.objects.ausloesen(vignette)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect("evals:evallauf", pk=vignette.pk)

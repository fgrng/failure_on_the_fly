"""Vorschau der Markdown-Texte für die Editoren."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST

from konten.models import Konto
from konten.navigation import ist_autorin, ist_forschende, rolle_erforderlich

from . import markdown


def _schreibt_texte(konto: Konto) -> bool:
    # Wer Erhebungstexte oder Vignetten und Kern schreibt, darf vorschauen.

    return ist_autorin(konto) or ist_forschende(konto)


@login_required
@rolle_erforderlich(_schreibt_texte)
@require_POST
def vorschau(request: HttpRequest) -> HttpResponse:
    """Rendert eine Quelle im gewählten Profil, wie die Anzeigeseite es tut.

    Der Endpunkt schreibt nichts; er ersetzt ein Rendering in JavaScript,
    damit Vorschau und Teilnahmeseite dieselbe Funktion nutzen.
    """

    profil: markdown.Profil | None = markdown.PROFILE.get(
        request.POST.get("profil", "")
    )
    if profil is None:
        return HttpResponseBadRequest("Unbekanntes Profil.")
    return render(
        request,
        "texte/vorschau.html",
        {"html": profil.rendern(request.POST.get("quelle", ""))},
    )

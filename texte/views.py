"""Vorschau der Markdown-Texte für die Editoren."""

from typing import Callable

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils.safestring import SafeString
from django.views.decorators.http import require_POST

from konten.models import Konto
from konten.navigation import (
    AUTORIN_GRUPPE,
    FORSCHENDE_GRUPPE,
    rolle_erforderlich,
    rolle_oder_administration,
)

from . import markdown

_PROFILE: dict[str, Callable[[str], SafeString]] = {
    "informationstext": markdown.informationstext,
    "szenentext": markdown.szenentext,
}


def _schreibt_texte(konto: Konto) -> bool:
    # Wer Erhebungstexte oder Vignetten und Kern schreibt, darf vorschauen.

    return rolle_oder_administration(AUTORIN_GRUPPE)(
        konto
    ) or rolle_oder_administration(FORSCHENDE_GRUPPE)(konto)


@login_required
@rolle_erforderlich(_schreibt_texte)
@require_POST
def vorschau(request: HttpRequest) -> HttpResponse:
    """Rendert eine Quelle im gewählten Profil, wie die Anzeigeseite es tut.

    Der Endpunkt schreibt nichts; er ersetzt ein Rendering in JavaScript,
    damit Vorschau und Teilnahmeseite dieselbe Funktion nutzen.
    """

    rendern: Callable[[str], SafeString] | None = _PROFILE.get(
        request.POST.get("profil", "")
    )
    if rendern is None:
        return HttpResponseBadRequest("Unbekanntes Profil.")
    return render(
        request,
        "texte/vorschau.html",
        {"html": rendern(request.POST.get("quelle", ""))},
    )

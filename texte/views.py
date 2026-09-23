"""Vorschau der Markdown-Texte für die Editoren."""

from typing import Callable

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils.safestring import SafeString
from django.views.decorators.http import require_POST

from konten.models import Konto
from konten.navigation import (
    FORSCHENDE_GRUPPE,
    ist_autorin,
    rolle_erforderlich,
    rolle_oder_administration,
)

from . import markdown

_PROFILE: dict[str, Callable[[str], SafeString]] = {
    "informationstext": markdown.informationstext,
    "szenentext": markdown.szenentext,
}
_ist_forschende: Callable[[Konto], bool] = rolle_oder_administration(FORSCHENDE_GRUPPE)


def _schreibt_texte(konto: Konto) -> bool:
    # Wer Erhebungstexte oder Vignetten und Kern schreibt, darf vorschauen.

    return ist_autorin(konto) or _ist_forschende(konto)


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

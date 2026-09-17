"""Wegwerf-View für den Startseiten-Prototyp (siehe PROTOTYPE_STARTSEITE.md).

Diese Datei wird zusammen mit Template, CSS und Route gelöscht, sobald eine
Variante gewählt ist.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

# Variante -> (Bezeichnung, vorherige, nächste)
_VARIANTEN: dict[str, tuple[str, str, str]] = {
    "a": ("A · Ablaufband", "c", "b"),
    "b": ("B · Rolleneinstieg", "a", "c"),
    "c": ("C · Texttafel", "b", "a"),
}


def startseite_prototype(request: HttpRequest) -> HttpResponse:
    """Zeigt drei rein statische Varianten der Willkommensseite."""

    variante: str = request.GET.get("variant", "a")
    if variante not in _VARIANTEN:
        variante = "a"
    bezeichnung, vorherige_variante, naechste_variante = _VARIANTEN[variante]

    return render(
        request,
        "prototype_start.html",
        {
            "variante": variante,
            "variantenbezeichnung": bezeichnung,
            "vorherige_variante": vorherige_variante,
            "naechste_variante": naechste_variante,
        },
    )

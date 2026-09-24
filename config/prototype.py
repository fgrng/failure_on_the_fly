"""PROTOTYPE #287, #290 – gemeinsame Variantenwahl. Mit den Prototypen löschen."""

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def variantenkontext(request: HttpRequest, varianten: dict[str, str]) -> dict[str, object]:
    """Liest ?variant= und liefert den Kontext für includes/prototype_switcher.html."""
    if not settings.DEBUG:
        raise Http404
    schluessel = list(varianten)
    variante = request.GET.get("variant", schluessel[0])
    if variante not in varianten:
        variante = schluessel[0]
    i = schluessel.index(variante)
    return {
        "variante": variante,
        "variantenbezeichnung": varianten[variante],
        "vorherige_variante": schluessel[i - 1],
        "naechste_variante": schluessel[(i + 1) % len(schluessel)],
    }


# PROTOTYPE #287 – Bereichsmarkierung der Sidebar.
_NAV_VARIANTEN: dict[str, str] = {
    "a": "A · Heute: alles Grün",
    "b": "B · Balken in Bereichsfarbe",
    "c": "C · Balken und Fläche im Bereichston",
    "d": "D · Gruppe als getönte Fläche",
}


def bereichsmarkierung(request: HttpRequest) -> HttpResponse:
    """PROTOTYPE #287: Sidebar-Varianten; das Cookie trägt die Wahl auf alle Seiten."""
    kontext = variantenkontext(request, _NAV_VARIANTEN)
    if "aus" in request.GET:
        antwort = redirect("start")
        antwort.delete_cookie("prototype_nav")
        return antwort
    # Die Sidebar dieser Antwort soll schon die neue Wahl zeigen, nicht die alte.
    request.COOKIES["prototype_nav"] = str(kontext["variante"])
    antwort = render(request, "prototype_bereichsmarkierung.html", kontext)
    # Sitzungscookie: verschwindet mit dem Schließen des Browsers.
    antwort.set_cookie("prototype_nav", str(kontext["variante"]), samesite="Lax")
    return antwort

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


# PROTOTYPE #289 – Eigentümer:innen-Abschnitt. Mit dem Prototyp löschen.
_EIGENTUEMERINNEN_VARIANTEN: dict[str, str] = {
    "a": "A · Heute: Chips, Auswahl direkt darunter",
    "b": "B · Tabelle, Hinzufügen mit Unterüberschrift",
    "c": "C · Liste mit aufklappbarer Hinzufügen-Zeile",
    "d": "D · Zwei Spalten, »Kreis verlassen« getrennt",
}

_ICH = {"name": "fabian.gruenig", "rolle": "Autorin", "ich": True}
_ANNA = {"name": "anna.meier", "rolle": "Administratorin", "ich": False}
_JONAS = {"name": "jonas.keller", "rolle": "Autor", "ich": False}

# Drei Zustände, die jede Variante untereinander zeigt.
_EIGENTUEMERINNEN_ZUSTAENDE: list[dict[str, object]] = [
    {
        "titel": "Mehrere Eigentümer:innen, Auswahl vorhanden",
        "kreis": [_ICH, _ANNA, _JONAS],
        "moegliche": ["lea.brunner", "tim.huber"],
    },
    {
        "titel": "Nur noch die eigene Person im Kreis (Entfernen gesperrt)",
        "kreis": [_ICH],
        "moegliche": ["anna.meier", "jonas.keller", "lea.brunner"],
    },
    {
        "titel": "Niemand mehr hinzuzufügen (leere Auswahl)",
        "kreis": [_ICH, _ANNA],
        "moegliche": [],
    },
]


def eigentuemerinnen(request: HttpRequest) -> HttpResponse:
    """PROTOTYPE #289: Varianten des Eigentümer:innen-Abschnitts, ohne Datenbank."""
    kontext = variantenkontext(request, _EIGENTUEMERINNEN_VARIANTEN)
    kontext["zustaende"] = _EIGENTUEMERINNEN_ZUSTAENDE
    return render(request, "prototype_eigentuemerinnen.html", kontext)

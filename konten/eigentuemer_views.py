"""Die Views zum Eigentümer-Kreis, die alle bestandstragenden Apps teilen."""

from collections.abc import Callable

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect

from konten.eigentuemerschaft import EigentuemerKreis

type View = Callable[..., HttpResponse]

# Lädt das sichtbare Objekt zu `pk` und liefert seinen Eigentümer-Kreis samt
# Rückweg auf die Seite, von der die Aktion kam. Kreis und Objekt sind nicht
# immer dasselbe: Bei Vignette und Fragebogen-Item trägt die Historie den Kreis.
type Aufloesung = Callable[[HttpRequest, int], tuple[EigentuemerKreis, str]]


def eigentuemer_views(
    *,
    rolle_erforderlich: Callable[[View], View],
    aufloesen: Aufloesung,
    liste: str,
) -> tuple[View, View]:
    """Baut das View-Paar Hinzufügen/Entfernen für eine Bestands-App.

    Die App reicht herein, was sich unterscheidet: ihre Rollenprüfung, wie sie
    das sichtbare Objekt lädt, und ihre Liste als Rückweg nach dem
    Selbstaustritt. So zeigt die Kante weiter von der App auf `konten`
    (ADR-0016, ADR-0037).
    """

    @login_required
    @rolle_erforderlich
    def eigentuemerin_hinzufuegen(request: HttpRequest, pk: int) -> HttpResponse:
        """Nimmt ein Konto der Rollengruppe in den Eigentümer-Kreis auf."""
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        kreis, rueckweg = aufloesen(request, pk)
        konto = get_object_or_404(
            kreis.moegliche_ergaenzungen(), pk=request.POST.get("konto")
        )
        kreis.eigentuemerinnen.add(konto)
        return redirect(rueckweg)

    @login_required
    @rolle_erforderlich
    def eigentuemerin_entfernen(
        request: HttpRequest, pk: int, konto_pk: int
    ) -> HttpResponse:
        """Trägt eine Eigentümerin aus dem Kreis aus.

        Wer sich selbst austrägt, sieht das Objekt danach nicht mehr und
        landet auf der Liste; scheitert der Austritt an der Invariante, bleibt
        es beim Rückweg.
        """
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        kreis, rueckweg = aufloesen(request, pk)
        if kreis.austreten(konto_pk) and konto_pk == request.user.pk:
            return redirect(liste)
        return redirect(rueckweg)

    return eigentuemerin_hinzufuegen, eigentuemerin_entfernen

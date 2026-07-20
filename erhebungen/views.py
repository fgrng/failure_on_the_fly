"""Öffentlicher Einstieg in pseudonyme Erhebungen."""

from datetime import datetime
from functools import wraps
from typing import Callable, Concatenate, Iterable, ParamSpec
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, F, Max, QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from .ablauf import naechster_schritt
from .export import datenspur_zip
from .models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsitem,
    Erhebungsvignette,
    Stichprobe,
    Vignettenposition,
)
from simulation.models import ModellKonfiguration, Simulationskern
from fragebogen_items.models import FragebogenItem, FragebogenItemHistorie
from sitzungen.models import Sitzung
from sitzungen.orchestrierung import sitzung_starten
from sitzungen.sink import DBSink
from sitzungen.views import (
    Sitzungsnavigation,
    persistiertes_gespraech,
    persistierten_debrief_anzeigen,
    zeitbudget_anhalten,
)
from vignetten.models import Vignette, Vignettenhistorie

_TEILNAHME_TOKENS_SESSION_KEY: str = "erhebung_teilnahme_tokens"
_FORSCHENDE_GRUPPE: str = "Forschende:r"
_VIGNETTEN_SPALTEN: list[dict[str, str]] = [
    {"schluessel": "label", "beschriftung": "Name"},
]
_VIGNETTEN_SUCHSCHLUESSEL: tuple[str, ...] = ("label", "fach", "thema")
_ITEM_SPALTEN: list[dict[str, str]] = [
    {"schluessel": "label", "beschriftung": "Wortlaut"}
]
_ITEM_SUCHSCHLUESSEL: tuple[str, ...] = ("label",)
_ANDERE_ANDOCKPUNKTE: dict[str, str] = {
    Erhebungsitem.Andockpunkt.NACH_SITZUNG: Erhebungsitem.Andockpunkt.AM_ENDE,
    Erhebungsitem.Andockpunkt.AM_ENDE: Erhebungsitem.Andockpunkt.NACH_SITZUNG,
}
_BADGE_BESCHRIFTUNGEN: dict[str, str] = {
    Erhebungsitem.Andockpunkt.NACH_SITZUNG: "schon nach jeder Sitzung",
    Erhebungsitem.Andockpunkt.AM_ENDE: "schon am Ende",
}
P = ParamSpec("P")


def _forschende_erforderlich(
    view: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """Schützt eine View der Forschenden-UI mit der Rollenprüfung."""

    @wraps(view)
    def geschuetzte_view(
        request: HttpRequest,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> HttpResponse:
        if not request.user.groups.filter(name=_FORSCHENDE_GRUPPE).exists():
            return HttpResponse(status=403)
        return view(request, *args, **kwargs)

    return geschuetzte_view


def _sichtbare_erhebung(request: HttpRequest, pk: int) -> Erhebung:
    """Lädt eine für die eingeloggte Forschende sichtbare Erhebung."""

    return get_object_or_404(Erhebung.objects.sichtbar_fuer(request.user), pk=pk)


def _eigene_finalen_vignetten(request: HttpRequest) -> QuerySet[Vignette]:
    """Liefert einbindbare Fassungen aus dem Eigentümer-Kreis der Forschenden."""

    return Vignette.objects.einbindbar().filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user)
    )


def _eigene_finalen_items(request: HttpRequest) -> QuerySet[FragebogenItem]:
    """Liefert einbindbare Item-Fassungen aus dem Eigentümer-Kreis der Forschenden."""

    return FragebogenItem.objects.einbindbar().filter(
        historie__in=FragebogenItemHistorie.objects.sichtbar_fuer(request.user)
    )


def _status_badge(erhebung: Erhebung) -> str:
    """Ordnet Erhebungsstatus den gemeinsamen Badge-Klassen zu."""

    return {
        Erhebung.Status.ENTWURF: "draft",
        Erhebung.Status.FINAL: "final",
        Erhebung.Status.ARCHIVIERT: "archived",
    }[erhebung.status]


def _vignettenzeilen(
    vignetten: Iterable[Vignette], erhebung: Erhebung, aktion: str
) -> list[dict[str, object]]:
    """Baut die Tabellenzeilen einer Zuordnungsspalte samt ihrer Aktions-URL."""

    return [
        {
            "pk": vignette.pk,
            "label": vignette.historie.name or vignette.fach,
            "fach": vignette.fach,
            "thema": vignette.thema,
            "aktion_url": reverse(aktion, args=[erhebung.pk, vignette.pk]),
        }
        for vignette in vignetten
    ]


def _itemzeilen(
    items: Iterable[FragebogenItem],
    erhebung: Erhebung,
    andockpunkt: str,
    aktion: str,
    zugehoerigkeiten: dict[int, Erhebungsitem] | None = None,
    badge_beschriftungen: dict[int, str] | None = None,
) -> list[dict[str, object]]:
    """Baut die Tabellenzeilen einer Item-Spalte samt ihrer Aktions-URL."""

    if zugehoerigkeiten is None:
        badge_beschriftungen = badge_beschriftungen or {}
        return [
            {
                "pk": item.pk,
                "label": item.wortlaut,
                "aktion_url": reverse(aktion, args=[erhebung.pk, item.pk, andockpunkt]),
                "badge": badge_beschriftungen.get(item.pk),
            }
            for item in items
        ]

    zeilen: list[dict[str, object]] = []
    item_liste: list[FragebogenItem] = list(items)
    for index, item in enumerate(item_liste):
        zugehoerigkeit: Erhebungsitem = zugehoerigkeiten[item.pk]
        aktionen: list[dict[str, str]] = []
        if index:
            aktionen.append(
                {
                    "beschriftung": "Hoch",
                    "aktion_url": reverse(
                        "erhebungen:item_hoch", args=[erhebung.pk, zugehoerigkeit.pk]
                    ),
                }
            )
        if index < len(item_liste) - 1:
            aktionen.append(
                {
                    "beschriftung": "Runter",
                    "aktion_url": reverse(
                        "erhebungen:item_runter", args=[erhebung.pk, zugehoerigkeit.pk]
                    ),
                }
            )
        aktionen.append(
            {
                "beschriftung": "Entfernen",
                "aktion_url": reverse(aktion, args=[erhebung.pk, zugehoerigkeit.pk]),
            }
        )
        zeilen.append(
            {
                "pk": item.pk,
                "label": item.wortlaut,
                "position": zugehoerigkeit.position,
                "aktionen": aktionen,
            }
        )
    return zeilen


def _validierte_aktion_ausfuehren(
    request: HttpRequest, aktion: Callable[[], None]
) -> None:
    """Führt eine Domänenaktion aus und zeigt ihren Validierungsfehler an."""

    try:
        aktion()
    except ValidationError as error:
        messages.error(request, error.message)


@login_required
@_forschende_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Listet die eigenen Erhebungen einer Forschenden."""

    erhebungen: QuerySet[Erhebung] = Erhebung.objects.sichtbar_fuer(request.user)
    for erhebung in erhebungen:
        erhebung.status_badge = _status_badge(erhebung)
    return render(request, "erhebungen/liste.html", {"erhebungen": erhebungen})


@login_required
@_forschende_erforderlich
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt eine neue Erhebung als Entwurf an."""

    if request.method == "POST":
        erhebung: Erhebung = Erhebung.objects.create(
            name=request.POST.get("name", "Neue Erhebung"),
            eigentuemerin=request.user,
        )
        return redirect("erhebungen:detail", pk=erhebung.pk)
    return render(request, "erhebungen/anlegen.html")


@login_required
@_forschende_erforderlich
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine eigene Erhebung zur weiteren Bearbeitung."""

    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    stichproben: QuerySet[Stichprobe] = erhebung.stichprobe_set.annotate(
        teilnahmezahl=Count("erhebungsbindung")
    )

    for stichprobe in stichproben:
        stichprobe.teilnahme_url = request.build_absolute_uri(
            reverse("erhebungen:teilnehmen", args=[stichprobe.teilnahme_link])
        )

    vignettenzugehoerigkeiten: QuerySet[Erhebungsvignette] = (
        erhebung.vignettenzugehoerigkeiten.select_related(
            "vignette", "vignette__historie"
        )
    )
    verfuegbare_vignetten: QuerySet[Vignette] = _eigene_finalen_vignetten(
        request
    ).exclude(pk__in=erhebung.vignetten.values("pk"))
    itemzugehoerigkeiten: QuerySet[Erhebungsitem] = (
        erhebung.itemzugehoerigkeiten.select_related("item")
    )
    itemdaten: dict[str, dict[str, object]] = {}
    for andockpunkt in Erhebungsitem.Andockpunkt.values:
        zugehoerigkeiten_am_andockpunkt: list[Erhebungsitem] = [
            zugehoerigkeit
            for zugehoerigkeit in itemzugehoerigkeiten
            if zugehoerigkeit.andockpunkt == andockpunkt
        ]
        aufgenommene_items: list[FragebogenItem] = [
            zugehoerigkeit.item for zugehoerigkeit in zugehoerigkeiten_am_andockpunkt
        ]
        anderer_andockpunkt: str = _ANDERE_ANDOCKPUNKTE[andockpunkt]
        badge_beschriftung: str = _BADGE_BESCHRIFTUNGEN[anderer_andockpunkt]
        itemdaten[andockpunkt] = {
            "aufgenommene": _itemzeilen(
                aufgenommene_items,
                erhebung,
                andockpunkt,
                "erhebungen:item_entfernen",
                {
                    zugehoerigkeit.item_id: zugehoerigkeit
                    for zugehoerigkeit in zugehoerigkeiten_am_andockpunkt
                },
            ),
            "verfuegbare": _itemzeilen(
                _eigene_finalen_items(request).exclude(
                    pk__in=[item.pk for item in aufgenommene_items]
                ),
                erhebung,
                andockpunkt,
                "erhebungen:item_hinzufuegen",
                badge_beschriftungen={
                    zugehoerigkeit.item_id: badge_beschriftung
                    for zugehoerigkeit in itemzugehoerigkeiten
                    if zugehoerigkeit.andockpunkt == anderer_andockpunkt
                },
            ),
        }

    return render(
        request,
        "erhebungen/detail.html",
        {
            "erhebung": erhebung,
            "status_badge": _status_badge(erhebung),
            "vignettenzugehoerigkeiten": vignettenzugehoerigkeiten,
            "aufgenommene_daten": _vignettenzeilen(
                [
                    zugehoerigkeit.vignette
                    for zugehoerigkeit in vignettenzugehoerigkeiten
                ],
                erhebung,
                "erhebungen:vignette_entfernen",
            ),
            "verfuegbare_daten": _vignettenzeilen(
                verfuegbare_vignetten, erhebung, "erhebungen:vignette_hinzufuegen"
            ),
            "vignetten_spalten": _VIGNETTEN_SPALTEN,
            "vignetten_suchschluessel": _VIGNETTEN_SUCHSCHLUESSEL,
            "item_spalten": _ITEM_SPALTEN,
            "item_suchschluessel": _ITEM_SUCHSCHLUESSEL,
            "nach_sitzung_aufgenommene_daten": itemdaten[
                Erhebungsitem.Andockpunkt.NACH_SITZUNG
            ]["aufgenommene"],
            "nach_sitzung_verfuegbare_daten": itemdaten[
                Erhebungsitem.Andockpunkt.NACH_SITZUNG
            ]["verfuegbare"],
            "am_ende_aufgenommene_daten": itemdaten[Erhebungsitem.Andockpunkt.AM_ENDE][
                "aufgenommene"
            ],
            "am_ende_verfuegbare_daten": itemdaten[Erhebungsitem.Andockpunkt.AM_ENDE][
                "verfuegbare"
            ],
            "kann_zurueckziehen": erhebung.kann_zurueckgezogen_werden,
            "kann_archivieren": erhebung.kann_archiviert_werden,
            "kann_entarchivieren": erhebung.kann_entarchiviert_werden,
            "stichproben": stichproben,
        },
    )


@login_required
@_forschende_erforderlich
def export(request: HttpRequest, pk: int) -> HttpResponse:
    """Lädt den Datenexport einer sichtbaren Erhebung synchron herunter."""

    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    zeitstempel: str = (
        timezone.now().astimezone(timezone.UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    dateiname: str = (
        f"erhebung-{erhebung.pk}-{slugify(erhebung.name)}-{zeitstempel}.zip"
    )
    response: HttpResponse = HttpResponse(
        datenspur_zip(erhebung), content_type="application/zip"
    )
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response


@login_required
@_forschende_erforderlich
def stichprobe_anlegen(request: HttpRequest, pk: int) -> HttpResponse:
    """Legt unter einer finalen eigenen Erhebung eine Stichprobe an."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.FINAL:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    beginn: datetime | None = parse_datetime(request.POST.get("beginn", ""))
    ende: datetime | None = parse_datetime(request.POST.get("ende", ""))
    if beginn is None or ende is None:
        return HttpResponseBadRequest("Beginn und Ende müssen gültige Zeitpunkte sein.")
    if timezone.is_naive(beginn):
        beginn = timezone.make_aware(beginn)
    if timezone.is_naive(ende):
        ende = timezone.make_aware(ende)
    if ende < beginn:
        return HttpResponseBadRequest("Das Ende darf nicht vor dem Beginn liegen.")
    Stichprobe.objects.create(erhebung=erhebung, beginn=beginn, ende=ende)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def stichprobe_archivieren(
    request: HttpRequest, pk: int, stichprobe_pk: int
) -> HttpResponse:
    """Archiviert eine datenfreie Stichprobe über ihre Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    stichprobe: Stichprobe = get_object_or_404(
        erhebung.stichprobe_set, pk=stichprobe_pk
    )
    _validierte_aktion_ausfuehren(request, stichprobe.archivieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def vignette_hinzufuegen(
    request: HttpRequest, pk: int, vignette_pk: int
) -> HttpResponse:
    """Nimmt eine eigene finale Fassung in einen eigenen Entwurf auf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    vignette: Vignette = get_object_or_404(
        _eigene_finalen_vignetten(request), pk=vignette_pk
    )
    position: int | None = None
    if erhebung.randomisierung == Erhebung.Randomisierung.FEST:
        position = erhebung.vignettenzugehoerigkeiten.count() + 1
    Erhebungsvignette.objects.get_or_create(
        erhebung=erhebung, vignette=vignette, defaults={"position": position}
    )
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def vignette_entfernen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Entfernt eine finale Fassung aus einem eigenen Entwurf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status == Erhebung.Status.ENTWURF:
        get_object_or_404(
            erhebung.vignettenzugehoerigkeiten, vignette_id=vignette_pk
        ).delete()
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def item_hinzufuegen(
    request: HttpRequest, pk: int, item_pk: int, andockpunkt: str
) -> HttpResponse:
    """Nimmt eine eigene finale Item-Fassung an einem Andockpunkt auf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        raise PermissionDenied
    if andockpunkt not in Erhebungsitem.Andockpunkt.values:
        raise PermissionDenied
    item: FragebogenItem = get_object_or_404(_eigene_finalen_items(request), pk=item_pk)
    zugehoerigkeiten: QuerySet[Erhebungsitem] = erhebung.itemzugehoerigkeiten.filter(
        andockpunkt=andockpunkt
    )
    if zugehoerigkeiten.filter(item=item).exists():
        return HttpResponse(status=409)
    position: int = (
        zugehoerigkeiten.aggregate(Max("position"))["position__max"] or 0
    ) + 1
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=andockpunkt,
        position=position,
    )
    return detail(request, pk)


@login_required
@_forschende_erforderlich
def item_entfernen(
    request: HttpRequest, pk: int, zugehoerigkeit_pk: int
) -> HttpResponse:
    """Entfernt eine Item-Zuordnung aus einem eigenen Entwurf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        raise PermissionDenied
    zugehoerigkeit: Erhebungsitem = get_object_or_404(
        erhebung.itemzugehoerigkeiten, pk=zugehoerigkeit_pk
    )
    andockpunkt: str = zugehoerigkeit.andockpunkt
    position: int = zugehoerigkeit.position
    zugehoerigkeit.delete()
    erhebung.itemzugehoerigkeiten.filter(
        andockpunkt=andockpunkt, position__gt=position
    ).update(position=F("position") - 1)
    return detail(request, pk)


def _item_verschieben(
    erhebung: Erhebung, zugehoerigkeit_pk: int, richtung: int
) -> None:
    """Vertauscht eine Item-Zuordnung mit ihrer Nachbarin am selben Andockpunkt."""

    zugehoerigkeit: Erhebungsitem = get_object_or_404(
        erhebung.itemzugehoerigkeiten.select_for_update(), pk=zugehoerigkeit_pk
    )
    nachbarin: Erhebungsitem | None = (
        erhebung.itemzugehoerigkeiten.select_for_update()
        .filter(
            andockpunkt=zugehoerigkeit.andockpunkt,
            position=zugehoerigkeit.position + richtung,
        )
        .first()
    )
    if nachbarin is None:
        return
    hoechste_position: int = (
        erhebung.itemzugehoerigkeiten.filter(
            andockpunkt=zugehoerigkeit.andockpunkt
        ).aggregate(Max("position"))["position__max"]
        or 0
    )
    bisherige_position: int = zugehoerigkeit.position
    zugehoerigkeit.position = hoechste_position + 1
    zugehoerigkeit.save(update_fields=["position"])
    nachbarin.position = bisherige_position
    nachbarin.save(update_fields=["position"])
    zugehoerigkeit.position = bisherige_position + richtung
    zugehoerigkeit.save(update_fields=["position"])


def _itemreihenfolge_aendern(
    request: HttpRequest, pk: int, zugehoerigkeit_pk: int, richtung: int
) -> HttpResponse:
    """Verschiebt eine Item-Zuordnung und aktualisiert die Detailansicht."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        raise PermissionDenied
    _item_verschieben(erhebung, zugehoerigkeit_pk, richtung)
    return detail(request, pk)


@login_required
@_forschende_erforderlich
@transaction.atomic
def item_hoch(request: HttpRequest, pk: int, zugehoerigkeit_pk: int) -> HttpResponse:
    """Verschiebt eine Item-Zuordnung im Andockpunkt um eine Position nach oben."""

    return _itemreihenfolge_aendern(request, pk, zugehoerigkeit_pk, -1)


@login_required
@_forschende_erforderlich
@transaction.atomic
def item_runter(request: HttpRequest, pk: int, zugehoerigkeit_pk: int) -> HttpResponse:
    """Verschiebt eine Item-Zuordnung im Andockpunkt um eine Position nach unten."""

    return _itemreihenfolge_aendern(request, pk, zugehoerigkeit_pk, 1)


def _feste_reihenfolge_setzen(
    erhebung: Erhebung, zugehoerigkeit_ids: list[str]
) -> None:
    """Schreibt eine vollständige Reihenfolge ohne die eindeutigen Positionen zu kreuzen."""

    zugehoerigkeiten: QuerySet[Erhebungsvignette] = (
        erhebung.vignettenzugehoerigkeiten.select_for_update()
    )
    vorhandene_ids: list[int] = list(zugehoerigkeiten.values_list("pk", flat=True))
    try:
        neue_ids: list[int] = [int(pk) for pk in zugehoerigkeit_ids]
    except ValueError:
        return
    if len(neue_ids) != len(set(neue_ids)) or set(neue_ids) != set(vorhandene_ids):
        return
    bisherige_positionen: list[int] = list(
        zugehoerigkeiten.values_list("position", flat=True)
    )
    zugehoerigkeiten.update(
        position=F("position") + max(bisherige_positionen, default=0)
    )
    for position, zugehoerigkeit_id in enumerate(neue_ids, start=1):
        zugehoerigkeiten.filter(pk=zugehoerigkeit_id).update(position=position)


@login_required
@_forschende_erforderlich
@transaction.atomic
def konfiguration_speichern(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert die konfigurierbaren Texte, Regel und feste Reihenfolge eines Entwurfs."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    randomisierung: str = request.POST.get("randomisierung", erhebung.randomisierung)
    if randomisierung not in Erhebung.Randomisierung.values:
        return HttpResponseBadRequest("Unbekannte Randomisierungsregel.")
    erhebung.instruktionstext = request.POST.get(
        "instruktionstext", erhebung.instruktionstext
    )
    erhebung.einwilligungstext = request.POST.get(
        "einwilligungstext", erhebung.einwilligungstext
    )
    erhebung.abschlusstext = request.POST.get("abschlusstext", erhebung.abschlusstext)
    erhebung.randomisierung = randomisierung
    erhebung.save(
        update_fields=[
            "instruktionstext",
            "einwilligungstext",
            "abschlusstext",
            "randomisierung",
        ]
    )
    if randomisierung == Erhebung.Randomisierung.FEST and "vignetten" in request.POST:
        _feste_reihenfolge_setzen(erhebung, request.POST.getlist("vignetten"))
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def loeschen(request: HttpRequest, pk: int) -> HttpResponse:
    """Löscht einen eigenen Entwurf physisch."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status == Erhebung.Status.ENTWURF:
        erhebung.delete()
    return redirect("erhebungen:liste")


@login_required
@_forschende_erforderlich
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen eigenen Entwurf über dessen Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.finalisieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def zurueckziehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht eine eigene finale Erhebung zurück, wenn ihr Guard es erlaubt."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.zurueckziehen)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def archivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Archiviert eine eigene finale Erhebung über deren Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.archivieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_erforderlich
def entarchivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Macht eine eigene archivierte Erhebung wieder final."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.entarchivieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


def teilnehmen(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Legt beim ersten Link-Aufruf eine pseudonyme Teilnahme an oder setzt sie fort."""
    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None:
        bindung = _bindung_anlegen_fuer_laufende_stichprobe(stichprobe)
        tokens: dict[str, str] = request.session.get(_TEILNAHME_TOKENS_SESSION_KEY, {})
        tokens[str(teilnahme_link)] = bindung.token
        request.session[_TEILNAHME_TOKENS_SESSION_KEY] = tokens
    if bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:instruktion", teilnahme_link=teilnahme_link)
    return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)


def einwilligung(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Zeigt das Einwilligungstor der Erhebung."""

    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None:
        return redirect("erhebungen:teilnehmen", teilnahme_link=teilnahme_link)
    if request.method == "POST":
        if request.POST.get("einwilligung") != "ja":
            return HttpResponseBadRequest("Bitte willigen Sie in die Teilnahme ein.")
        audioentscheidung: str | None = request.POST.get(
            "audioverarbeitung_eingewilligt"
        )
        if audioentscheidung not in {"ja", "nein"}:
            return HttpResponseBadRequest(
                "Bitte stimmen Sie der Audioverarbeitung zu oder lehnen Sie sie ab."
            )
        if bindung.teilnahme.audioverarbeitung_eingewilligt is not None:
            return HttpResponseBadRequest(
                "Die Einwilligung zur Audioverarbeitung wurde bereits festgehalten."
            )
        bindung.teilnahme.einwilligung_erteilt = True
        bindung.teilnahme.audioverarbeitung_eingewilligt = audioentscheidung == "ja"
        bindung.teilnahme.save(
            update_fields=["einwilligung_erteilt", "audioverarbeitung_eingewilligt"]
        )
        return redirect("erhebungen:instruktion", teilnahme_link=teilnahme_link)
    return render(
        request, "erhebungen/einwilligung.html", {"erhebung": stichprobe.erhebung}
    )


def instruktion(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Zeigt die Instruktion erst nach erteilter Einwilligung."""

    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None or not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    return render(
        request,
        "erhebungen/instruktion.html",
        {"erhebung": stichprobe.erhebung, "stichprobe": stichprobe},
    )


def spielen(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Startet die nächste gezogene Vignette über den persistenten DB-Sink."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None or not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    if Sitzung.objects.filter(
        teilnahme=bindung.teilnahme, status=Sitzung.Status.LAUFEND
    ).exists():
        return redirect("erhebungen:gespraech", token=bindung.token)
    if not _naechste_sitzung_starten(bindung, stichprobe.erhebung):
        return redirect("erhebungen:abschluss", teilnahme_link=teilnahme_link)
    return redirect("erhebungen:gespraech", token=bindung.token)


def _naechste_sitzung_starten(bindung: Erhebungsbindung, erhebung: Erhebung) -> bool:
    vignette: Vignette | None = naechster_schritt(bindung.teilnahme)
    if vignette is None:
        return False
    kern: Simulationskern | None = vignette.gepinnter_kern
    modell_konfiguration: ModellKonfiguration | None = erhebung.modell_konfiguration
    if kern is None or modell_konfiguration is None:
        raise RuntimeError("Erhebungsvignetten brauchen Kern und Modell-Konfiguration.")
    with transaction.atomic():
        sink: DBSink = DBSink(bindung.teilnahme)
        sitzung_starten(sink, vignette, kern, modell_konfiguration)
        position: int = bindung.vignettenziehungen.get(vignette=vignette).position
        Vignettenposition.objects.create(
            erhebungsbindung=bindung,
            sitzung=sink.sitzung,
            vignette=vignette,
            position=position,
        )
    return True


def _sitzungsnavigation(token: str) -> Sitzungsnavigation:
    # Hält die Erhebungsrouten in der App, der die Erhebungsbindung gehört.

    return Sitzungsnavigation(
        bezeichnung="Erhebung",
        gespraech_url=reverse("erhebungen:gespraech", args=[token]),
        beenden_url=reverse("erhebungen:gespraech_beenden", args=[token]),
        debrief_url=reverse("erhebungen:debrief", args=[token]),
        abbrechen_url=reverse("erhebungen:abbrechen", args=[token]),
    )


def _erhebungssitzung(token: str) -> tuple[Sitzung, Erhebungsbindung]:
    # Löst die laufende Sitzung in ihrer besitzenden Erhebungs-App auf.

    bindung: Erhebungsbindung = get_object_or_404(
        Erhebungsbindung.objects.select_related("stichprobe", "teilnahme"), token=token
    )
    if bindung.stichprobe.phase != Stichprobe.Phase.LAUFEND:
        raise PermissionDenied
    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme"),
        teilnahme=bindung.teilnahme,
        status=Sitzung.Status.LAUFEND,
    )
    return sitzung, bindung


def sitzung_fuer_transkription(request: HttpRequest) -> Sitzung | None:
    """Löst eine laufende Erhebungssitzung ausschließlich aus Browser-Tokens auf."""

    sitzung_pk: str | None = request.POST.get("sitzung_pk")
    if sitzung_pk is None:
        return None
    tokens: dict[str, str] = request.session.get(_TEILNAHME_TOKENS_SESSION_KEY, {})
    jetzt: datetime = timezone.now()
    return (
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme")
        .filter(
            pk=sitzung_pk,
            status=Sitzung.Status.LAUFEND,
            teilnahme__erhebungsbindung__token__in=tokens.values(),
            teilnahme__erhebungsbindung__stichprobe__beginn__lte=jetzt,
            teilnahme__erhebungsbindung__stichprobe__ende__gte=jetzt,
        )
        .first()
    )


def gespraech(request: HttpRequest, token: str) -> HttpResponse:
    """Führt einen persistierten Gesprächsschritt anonym über das Token aus."""

    sitzung, _bindung = _erhebungssitzung(token)
    return persistiertes_gespraech(request, sitzung, _sitzungsnavigation(token))


def gespraech_beenden(request: HttpRequest, token: str) -> HttpResponse:
    """Zeigt für die tokenaufgelöste Sitzung den Debrief."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, _bindung = _erhebungssitzung(token)
    zeitbudget_anhalten(request, sitzung)
    return persistierten_debrief_anzeigen(request, sitzung, _sitzungsnavigation(token))


def abbrechen(request: HttpRequest, token: str) -> HttpResponse:
    """Bricht eine Erhebungssitzung ohne Diagnose ab."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, bindung = _erhebungssitzung(token)
    zeitbudget_anhalten(request, sitzung)
    DBSink.fuer_sitzung(sitzung).status_setzen(Sitzung.Status.ABGEBROCHEN)
    return redirect(
        "erhebungen:instruktion", teilnahme_link=bindung.stichprobe.teilnahme_link
    )


def debrief(request: HttpRequest, token: str) -> HttpResponse:
    """Schließt die Sitzung mit Diagnose und setzt die Erhebung fort."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, bindung = _erhebungssitzung(token)
    uebermittelte_sitzung_pk: str | None = request.POST.get("sitzung_pk")
    if uebermittelte_sitzung_pk != str(sitzung.pk):
        return HttpResponseBadRequest("Der Debrief gehört nicht zu dieser Sitzung.")
    with transaction.atomic():
        sitzung = Sitzung.objects.select_for_update().get(pk=sitzung.pk)
        if sitzung.status != Sitzung.Status.LAUFEND:
            return HttpResponseBadRequest("Der Debrief gehört nicht zu dieser Sitzung.")
        DBSink.fuer_sitzung(sitzung).diagnose_setzen(request.POST["diagnose"])
    if _naechste_sitzung_starten(bindung, bindung.stichprobe.erhebung):
        return redirect("erhebungen:gespraech", token=bindung.token)
    return redirect(
        "erhebungen:abschluss", teilnahme_link=bindung.stichprobe.teilnahme_link
    )


def abschluss(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Zeigt nach allen Vignetten das definierte Ende der Erhebung."""

    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None or not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    return render(
        request, "erhebungen/abschluss.html", {"erhebung": stichprobe.erhebung}
    )


def _bindung_aus_session(
    request: HttpRequest, stichprobe: Stichprobe
) -> Erhebungsbindung | None:
    """Lädt die zur Stichprobe passende Bindung des aktuellen Browsers."""

    tokens: dict[str, str] = request.session.get(_TEILNAHME_TOKENS_SESSION_KEY, {})
    token: str | None = tokens.get(str(stichprobe.teilnahme_link))
    if token is None:
        return None
    return (
        Erhebungsbindung.objects.select_related("teilnahme")
        .filter(
            stichprobe=stichprobe,
            token=token,
        )
        .first()
    )


def _bindung_anlegen_fuer_laufende_stichprobe(
    stichprobe: Stichprobe,
) -> Erhebungsbindung:
    """Prüft das Teilnahmefenster und legt die Bindung unter derselben Sperre an."""

    with transaction.atomic():
        stichprobe = get_object_or_404(
            Stichprobe.objects.select_for_update(),
            pk=stichprobe.pk,
        )
        if stichprobe.archiviert or stichprobe.phase != Stichprobe.Phase.LAUFEND:
            raise PermissionDenied
        return Erhebungsbindung.objects.anlegen(stichprobe)


def _laufende_stichprobe(teilnahme_link: UUID) -> Stichprobe:
    """Lädt ausschließlich Stichproben, deren Teilnahmefenster gerade läuft."""

    stichprobe: Stichprobe = get_object_or_404(
        Stichprobe,
        teilnahme_link=teilnahme_link,
    )
    if stichprobe.archiviert or stichprobe.phase != Stichprobe.Phase.LAUFEND:
        raise PermissionDenied
    return stichprobe

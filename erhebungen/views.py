"""Öffentlicher Einstieg in pseudonyme Erhebungen."""

from datetime import datetime
from typing import Callable, Iterable
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, F, Max, QuerySet
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from konten.models import Konto
from konten.navigation import (
    FORSCHENDE_GRUPPE,
    rolle_erforderlich,
    rolle_oder_administration,
)

from .ablauf import (
    Ende,
    LaufendeSitzung,
    NaechsteVignette,
    NochNichtBegonnen,
    OffenerAbschlussblock,
    OffenerSitzungsblock,
    bindung_abschliessen,
    block_erledigen,
    block_vorlegen,
    laufende_sitzung,
    naechster_schritt,
    sitzung_am_zug,
    sitzung_mit_offenem_block,
    vignette_beginnen,
)
from .export import datenspur_zip
from .forms import ItemblockFormular
from .models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsitem,
    Erhebungsvignette,
    Itemblock,
    Stichprobe,
)
from .teilnahme_session import (
    token_aus_session,
    token_in_session_speichern,
    tokens_im_browser,
)
from fragebogen_items.models import FragebogenItem
from sitzungen.durchlauf import (
    Sitzungsnavigation,
    sitzung_abbrechen,
    sitzung_beenden,
)
from sitzungen.models import Eingabemodus, Sitzung
from sitzungen.sink import DBSink
from sitzungen.views import (
    persistiertes_gespraech,
    persistierten_debrief_anzeigen,
)
from vignetten.models import Vignette

_ANDERE_ANDOCKPUNKTE: dict[str, str] = {
    Erhebungsitem.Andockpunkt.NACH_SITZUNG: Erhebungsitem.Andockpunkt.AM_ENDE,
    Erhebungsitem.Andockpunkt.AM_ENDE: Erhebungsitem.Andockpunkt.NACH_SITZUNG,
}
_BADGE_BESCHRIFTUNGEN: dict[str, str] = {
    Erhebungsitem.Andockpunkt.NACH_SITZUNG: "schon nach jeder Sitzung",
    Erhebungsitem.Andockpunkt.AM_ENDE: "schon am Ende",
}
_ITEMSEITEN_PROTOTYP_VARIANTEN: dict[str, tuple[str, str, str]] = {
    "a": ("A · Skalenband", "c", "b"),
    "b": ("B · Entscheidungsleiter", "a", "c"),
    "c": ("C · Antwortkarten", "b", "a"),
    "vergleich": ("Vergleich · alle Varianten", "c", "a"),
}


_forschende_oder_administratorin = rolle_oder_administration(FORSCHENDE_GRUPPE)


# Eine einzige Tür für den gesamten Forschungsbereich, wie in fragebogen_items
# und vignetten: Die Administration sieht eine Erhebung nicht nur, sie kann sie
# auch anlegen und bearbeiten (ADR-0033).
_forschende_oder_administratorin_erforderlich = rolle_erforderlich(
    _forschende_oder_administratorin
)


def itemseite_prototype(request: HttpRequest) -> HttpResponse:
    """Zeigt drei rein statische Varianten der Teilnehmer:innen-Itemseite."""

    variante: str = request.GET.get("variant", "a")
    if variante not in _ITEMSEITEN_PROTOTYP_VARIANTEN:
        variante = "a"
    bezeichnung, vorherige_variante, naechste_variante = _ITEMSEITEN_PROTOTYP_VARIANTEN[
        variante
    ]

    return render(
        request,
        "erhebungen/prototype_itemseite.html",
        {
            "variante": variante,
            "variantenbezeichnung": bezeichnung,
            "vorherige_variante": vorherige_variante,
            "naechste_variante": naechste_variante,
        },
    )


def _sichtbare_erhebung(request: HttpRequest, pk: int) -> Erhebung:
    """Lädt eine für die eingeloggte Forschende sichtbare Erhebung."""

    return get_object_or_404(Erhebung.objects.sichtbar_fuer(request.user), pk=pk)


def _eigene_finalen_vignetten(request: HttpRequest) -> QuerySet[Vignette]:
    """Liefert einbindbare Fassungen aus dem Eigentümer-Kreis der Forschenden."""

    return Vignette.objects.einbindbar().sichtbar_fuer(request.user)


def _eigene_finalen_items(request: HttpRequest) -> QuerySet[FragebogenItem]:
    """Liefert einbindbare Item-Fassungen aus dem Eigentümer-Kreis der Forschenden."""

    return FragebogenItem.objects.einbindbar().sichtbar_fuer(request.user)


def _status_badge(erhebung: Erhebung) -> str:
    """Ordnet Erhebungsstatus den gemeinsamen Badge-Klassen zu."""

    return {
        Erhebung.Status.ENTWURF: "draft",
        Erhebung.Status.FINAL: "final",
        Erhebung.Status.ARCHIVIERT: "archived",
    }[erhebung.status]


def _vignettenzeilen(
    vignetten: Iterable[Vignette], erhebung: Erhebung, aktionen: dict[str, str]
) -> list[dict[str, object]]:
    """Baut die Zeilen einer Vignettenliste samt ihrer Aktions-URLs."""

    return [
        {
            "pk": vignette.pk,
            "label": vignette.anzeigename,
            "fach": vignette.fach,
            "thema": vignette.thema,
            **{
                schluessel: reverse(aktion, args=[erhebung.pk, vignette.pk])
                for schluessel, aktion in aktionen.items()
            },
        }
        for vignette in vignetten
    ]


def _verfuegbare_itemzeilen(
    items: Iterable[FragebogenItem],
    erhebung: Erhebung,
    andockpunkt: str,
    badge_beschriftungen: dict[int, str],
) -> list[dict[str, object]]:
    """Baut die Auswahl einer Itemliste samt Einfüge-URL und Hinweis."""

    return [
        {
            "pk": item.pk,
            "label": item.wortlaut,
            "einfuegen_url": reverse(
                "erhebungen:item_hinzufuegen", args=[erhebung.pk, item.pk, andockpunkt]
            ),
            "badge": badge_beschriftungen.get(item.pk),
        }
        for item in items
    ]


def _aufgenommene_itemzeilen(
    zugehoerigkeiten: Iterable[Erhebungsitem],
    erhebung: Erhebung,
    am_anderen_andockpunkt: set[int],
    bearbeitbar: bool,
) -> list[dict[str, object]]:
    """Baut die Zeilen einer Itemliste samt ihrer Aktions-URLs."""

    zeilen: list[dict[str, object]] = []
    for zugehoerigkeit in zugehoerigkeiten:
        zeile: dict[str, object] = {
            "pk": zugehoerigkeit.item_id,
            "label": zugehoerigkeit.item.wortlaut,
            "position": zugehoerigkeit.position,
        }
        if bearbeitbar:
            argumente: list[int] = [erhebung.pk, zugehoerigkeit.pk]
            zeile["verschieben_url"] = reverse(
                "erhebungen:item_verschieben", args=argumente
            )
            zeile["entfernen_url"] = reverse(
                "erhebungen:item_entfernen", args=argumente
            )
            # Hängt die Fassung schon am anderen Andockpunkt, gibt es nichts umzuhängen.
            if zugehoerigkeit.item_id not in am_anderen_andockpunkt:
                zeile["umhaengen_url"] = reverse(
                    "erhebungen:item_umhaengen", args=argumente
                )
        zeilen.append(zeile)
    return zeilen


def _position(request: HttpRequest) -> int | None:
    """Liest die gewünschte, 1-basierte Listenposition aus dem Formular."""

    try:
        return int(request.POST["position"])
    except KeyError, ValueError:
        return None


def _reihenfolge_schreiben(
    zugehoerigkeiten: QuerySet[Erhebungsvignette] | QuerySet[Erhebungsitem],
    ids: list[int],
) -> None:
    """Schreibt die Positionen 1..n, ohne die eindeutigen Positionen zu kreuzen."""

    versatz: int = max(
        zugehoerigkeiten.aggregate(Max("position"))["position__max"] or 0,
        len(ids),
    )
    zugehoerigkeiten.update(position=F("position") + versatz)
    for position, zugehoerigkeit_id in enumerate(ids, start=1):
        zugehoerigkeiten.filter(pk=zugehoerigkeit_id).update(position=position)


def _luecke_schliessen(
    zugehoerigkeiten: QuerySet[Erhebungsvignette] | QuerySet[Erhebungsitem],
) -> None:
    """Nummeriert eine Liste nach dem Entfernen lückenlos in ihrer Reihenfolge."""

    _reihenfolge_schreiben(
        zugehoerigkeiten,
        list(zugehoerigkeiten.order_by("position", "pk").values_list("pk", flat=True)),
    )


def _einreihen(
    zugehoerigkeiten: QuerySet[Erhebungsvignette] | QuerySet[Erhebungsitem],
    zugehoerigkeit_pk: int,
    position: int | None,
) -> None:
    """Setzt eine Zuordnung an eine Listenposition; ohne Position ans Ende."""

    ids: list[int] = [
        pk
        for pk in zugehoerigkeiten.order_by("position", "pk").values_list(
            "pk", flat=True
        )
        if pk != zugehoerigkeit_pk
    ]
    index: int = len(ids) if position is None else min(max(position - 1, 0), len(ids))
    ids.insert(index, zugehoerigkeit_pk)
    _reihenfolge_schreiben(zugehoerigkeiten, ids)


def _validierte_aktion_ausfuehren(
    request: HttpRequest, aktion: Callable[[], None]
) -> None:
    """Führt eine Domänenaktion aus und zeigt ihren Validierungsfehler an."""

    try:
        aktion()
    except ValidationError as error:
        messages.error(request, error.message)


@login_required
@_forschende_oder_administratorin_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Listet die eigenen Erhebungen einer Forschenden."""

    erhebungen: QuerySet[Erhebung] = Erhebung.objects.sichtbar_fuer(request.user)
    for erhebung in erhebungen:
        erhebung.status_badge = _status_badge(erhebung)
    return render(request, "erhebungen/liste.html", {"erhebungen": erhebungen})


@login_required
@_forschende_oder_administratorin_erforderlich
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt eine neue Erhebung als Entwurf an."""

    if request.method == "POST":
        erhebung: Erhebung = Erhebung.objects.anlegen(
            request.user,
            name=request.POST.get("name", "Neue Erhebung"),
        )
        return redirect("erhebungen:detail", pk=erhebung.pk)
    return render(request, "erhebungen/anlegen.html")


@login_required
@_forschende_oder_administratorin_erforderlich
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine sichtbare Erhebung zur weiteren Bearbeitung."""

    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    stichproben: QuerySet[Stichprobe] = erhebung.stichprobe_set.annotate(
        teilnahmezahl=Count("erhebungsbindung")
    )

    for stichprobe in stichproben:
        stichprobe.teilnahme_url = request.build_absolute_uri(
            reverse("erhebungen:teilnehmen", args=[stichprobe.teilnahme_link])
        )

    bearbeitbar: bool = erhebung.status == Erhebung.Status.ENTWURF
    vignettenzugehoerigkeiten: QuerySet[Erhebungsvignette] = (
        erhebung.vignettenzugehoerigkeiten.select_related(
            "vignette", "vignette__historie"
        )
    )
    verfuegbare_vignetten: QuerySet[Vignette] = _eigene_finalen_vignetten(
        request
    ).exclude(pk__in=erhebung.vignetten.values("pk"))
    itemzugehoerigkeiten: list[Erhebungsitem] = list(
        erhebung.itemzugehoerigkeiten.select_related("item")
    )
    item_ids: dict[str, set[int]] = {
        andockpunkt: {
            zugehoerigkeit.item_id
            for zugehoerigkeit in itemzugehoerigkeiten
            if zugehoerigkeit.andockpunkt == andockpunkt
        }
        for andockpunkt in Erhebungsitem.Andockpunkt.values
    }
    itemdaten: dict[str, dict[str, object]] = {}
    for andockpunkt in Erhebungsitem.Andockpunkt.values:
        anderer_andockpunkt: str = _ANDERE_ANDOCKPUNKTE[andockpunkt]
        itemdaten[andockpunkt] = {
            "aufgenommene": _aufgenommene_itemzeilen(
                [
                    zugehoerigkeit
                    for zugehoerigkeit in itemzugehoerigkeiten
                    if zugehoerigkeit.andockpunkt == andockpunkt
                ],
                erhebung,
                item_ids[anderer_andockpunkt],
                bearbeitbar,
            ),
            "verfuegbare": _verfuegbare_itemzeilen(
                _eigene_finalen_items(request).exclude(pk__in=item_ids[andockpunkt]),
                erhebung,
                andockpunkt,
                {
                    item_id: _BADGE_BESCHRIFTUNGEN[anderer_andockpunkt]
                    for item_id in item_ids[anderer_andockpunkt]
                },
            ),
        }

    return render(
        request,
        "erhebungen/detail.html",
        {
            "erhebung": erhebung,
            "status_badge": _status_badge(erhebung),
            "aufgenommene_daten": _vignettenzeilen(
                [
                    zugehoerigkeit.vignette
                    for zugehoerigkeit in vignettenzugehoerigkeiten
                ],
                erhebung,
                {
                    "verschieben_url": "erhebungen:vignette_verschieben",
                    "entfernen_url": "erhebungen:vignette_entfernen",
                }
                if bearbeitbar
                else {},
            ),
            "verfuegbare_daten": _vignettenzeilen(
                verfuegbare_vignetten,
                erhebung,
                {"einfuegen_url": "erhebungen:vignette_hinzufuegen"},
            ),
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
@_forschende_oder_administratorin_erforderlich
def eigentuemerin_hinzufuegen(request: HttpRequest, pk: int) -> HttpResponse:
    """Nimmt eine weitere Forschende in den Eigentümer-Kreis auf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    konto: Konto = get_object_or_404(
        erhebung.moegliche_ergaenzungen(), pk=request.POST.get("konto")
    )
    erhebung.eigentuemerinnen.add(konto)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def eigentuemerin_entfernen(
    request: HttpRequest, pk: int, konto_pk: int
) -> HttpResponse:
    """Trägt eine Eigentümerin aus dem Kreis der Erhebung aus.

    Wer sich selbst austrägt, landet auf der Erhebungsliste; scheitert der
    Austritt an der Invariante, bleibt es bei der Detailseite.
    """

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.austreten(konto_pk) and konto_pk == request.user.pk:
        return redirect("erhebungen:liste")
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
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
@_forschende_oder_administratorin_erforderlich
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
@_forschende_oder_administratorin_erforderlich
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
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
def vignette_hinzufuegen(
    request: HttpRequest, pk: int, vignette_pk: int
) -> HttpResponse:
    """Nimmt eine eigene finale Fassung an der gewünschten Position auf.

    Ohne Position landet sie am Ende der Liste.
    """

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    vignette: Vignette = get_object_or_404(
        _eigene_finalen_vignetten(request), pk=vignette_pk
    )
    zugehoerigkeiten: QuerySet[Erhebungsvignette] = (
        erhebung.vignettenzugehoerigkeiten.select_for_update()
    )
    zugehoerigkeit, angelegt = Erhebungsvignette.objects.get_or_create(
        erhebung=erhebung,
        vignette=vignette,
        defaults={
            "position": (
                zugehoerigkeiten.aggregate(Max("position"))["position__max"] or 0
            )
            + 1
        },
    )
    if angelegt:
        _einreihen(zugehoerigkeiten, zugehoerigkeit.pk, _position(request))
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
def vignette_entfernen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Entfernt eine finale Fassung aus einem eigenen Entwurf."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status == Erhebung.Status.ENTWURF:
        zugehoerigkeit: Erhebungsvignette = get_object_or_404(
            erhebung.vignettenzugehoerigkeiten, vignette_id=vignette_pk
        )
        zugehoerigkeit.delete()
        _luecke_schliessen(erhebung.vignettenzugehoerigkeiten.select_for_update())
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
def vignette_verschieben(
    request: HttpRequest, pk: int, vignette_pk: int
) -> HttpResponse:
    """Setzt eine Vignette an eine neue Position ihrer Liste."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        raise PermissionDenied
    zugehoerigkeiten: QuerySet[Erhebungsvignette] = (
        erhebung.vignettenzugehoerigkeiten.select_for_update()
    )
    zugehoerigkeit: Erhebungsvignette = get_object_or_404(
        zugehoerigkeiten, vignette_id=vignette_pk
    )
    position: int | None = _position(request)
    if position is None:
        return HttpResponseBadRequest("Position fehlt.")
    _einreihen(zugehoerigkeiten, zugehoerigkeit.pk, position)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
def reihenfolge_umschalten(request: HttpRequest, pk: int) -> HttpResponse:
    """Wechselt zwischen fester und zufälliger Vignettenreihenfolge.

    Die Positionen der Liste bleiben dabei unberührt; bei zufälliger Reihenfolge
    gelten sie nur nicht für die Teilnahme.
    """

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    randomisierung: str = request.POST.get("randomisierung", "")
    if randomisierung not in Erhebung.Randomisierung.values:
        return HttpResponseBadRequest("Unbekannte Randomisierungsregel.")
    erhebung.randomisierung = randomisierung
    erhebung.save(update_fields=["randomisierung"])
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
def item_hinzufuegen(
    request: HttpRequest, pk: int, item_pk: int, andockpunkt: str
) -> HttpResponse:
    """Nimmt eine eigene finale Item-Fassung an einem Andockpunkt auf.

    An die gewünschte Position, ohne Position ans Ende.
    """

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        raise PermissionDenied
    if andockpunkt not in Erhebungsitem.Andockpunkt.values:
        raise PermissionDenied
    item: FragebogenItem = get_object_or_404(_eigene_finalen_items(request), pk=item_pk)
    zugehoerigkeiten: QuerySet[Erhebungsitem] = (
        erhebung.itemzugehoerigkeiten.select_for_update().filter(
            andockpunkt=andockpunkt
        )
    )
    if zugehoerigkeiten.filter(item=item).exists():
        return HttpResponse(status=409)
    zugehoerigkeit: Erhebungsitem = Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=andockpunkt,
        position=(zugehoerigkeiten.aggregate(Max("position"))["position__max"] or 0)
        + 1,
    )
    _einreihen(zugehoerigkeiten, zugehoerigkeit.pk, _position(request))
    return detail(request, pk)


@login_required
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
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
    zugehoerigkeit.delete()
    _luecke_schliessen(
        erhebung.itemzugehoerigkeiten.select_for_update().filter(
            andockpunkt=andockpunkt
        )
    )
    return detail(request, pk)


@login_required
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
def item_verschieben(
    request: HttpRequest, pk: int, zugehoerigkeit_pk: int
) -> HttpResponse:
    """Setzt eine Item-Zuordnung innerhalb ihres Andockpunkts an eine neue Position."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        raise PermissionDenied
    zugehoerigkeit: Erhebungsitem = get_object_or_404(
        erhebung.itemzugehoerigkeiten, pk=zugehoerigkeit_pk
    )
    position: int | None = _position(request)
    if position is None:
        return HttpResponseBadRequest("Position fehlt.")
    _einreihen(
        erhebung.itemzugehoerigkeiten.select_for_update().filter(
            andockpunkt=zugehoerigkeit.andockpunkt
        ),
        zugehoerigkeit.pk,
        position,
    )
    return detail(request, pk)


@login_required
@_forschende_oder_administratorin_erforderlich
@transaction.atomic
def item_umhaengen(
    request: HttpRequest, pk: int, zugehoerigkeit_pk: int
) -> HttpResponse:
    """Hängt eine Item-Zuordnung ans Ende des anderen Andockpunkts um."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        raise PermissionDenied
    zugehoerigkeit: Erhebungsitem = get_object_or_404(
        erhebung.itemzugehoerigkeiten.select_for_update(), pk=zugehoerigkeit_pk
    )
    bisheriger_andockpunkt: str = zugehoerigkeit.andockpunkt
    ziel: QuerySet[Erhebungsitem] = erhebung.itemzugehoerigkeiten.filter(
        andockpunkt=_ANDERE_ANDOCKPUNKTE[bisheriger_andockpunkt]
    )
    if ziel.filter(item_id=zugehoerigkeit.item_id).exists():
        return HttpResponse(status=409)
    zugehoerigkeit.andockpunkt = _ANDERE_ANDOCKPUNKTE[bisheriger_andockpunkt]
    zugehoerigkeit.position = (
        ziel.aggregate(Max("position"))["position__max"] or 0
    ) + 1
    zugehoerigkeit.save(update_fields=["andockpunkt", "position"])
    _luecke_schliessen(
        erhebung.itemzugehoerigkeiten.select_for_update().filter(
            andockpunkt=bisheriger_andockpunkt
        )
    )
    return detail(request, pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def konfiguration_speichern(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert Instruktions-, Einwilligungs- und Abschlusstext eines Entwurfs."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status != Erhebung.Status.ENTWURF:
        return redirect("erhebungen:detail", pk=erhebung.pk)
    erhebung.instruktionstext = request.POST.get(
        "instruktionstext", erhebung.instruktionstext
    )
    erhebung.einwilligungstext = request.POST.get(
        "einwilligungstext", erhebung.einwilligungstext
    )
    erhebung.abschlusstext = request.POST.get("abschlusstext", erhebung.abschlusstext)
    erhebung.save(
        update_fields=["instruktionstext", "einwilligungstext", "abschlusstext"]
    )
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def loeschen(request: HttpRequest, pk: int) -> HttpResponse:
    """Löscht einen eigenen Entwurf physisch."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    if erhebung.status == Erhebung.Status.ENTWURF:
        erhebung.delete()
    return redirect("erhebungen:liste")


@login_required
@_forschende_oder_administratorin_erforderlich
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen eigenen Entwurf über dessen Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.finalisieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def zurueckziehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht eine eigene finale Erhebung zurück, wenn ihr Guard es erlaubt."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.zurueckziehen)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
def archivieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Archiviert eine eigene finale Erhebung über deren Domänenmethode."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    erhebung: Erhebung = _sichtbare_erhebung(request, pk)
    _validierte_aktion_ausfuehren(request, erhebung.archivieren)
    return redirect("erhebungen:detail", pk=erhebung.pk)


@login_required
@_forschende_oder_administratorin_erforderlich
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
        _bindung_in_session_speichern(request, bindung)
    if bindung.teilnahme.einwilligung_erteilt:
        return _weiter_im_ablauf(bindung)
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
    vignette_beginnen(bindung)
    return _weiter_im_ablauf(bindung)


def _weiter_im_ablauf(bindung: Erhebungsbindung) -> HttpResponseRedirect:
    """Führt die Teilnahme dorthin, wo ihr Ablauf gerade steht.

    Die einzige Verzweigung der Erhebungs-Views über die sechs Ablaufschritte.
    Eine anstehende Vignette wird dabei begonnen, damit jeder Weg in den Ablauf
    — Wiedereinstieg, Debrief, erledigter Block — an derselben Stelle endet.
    """

    teilnahme_link: UUID = bindung.stichprobe.teilnahme_link
    match naechster_schritt(bindung):
        case NochNichtBegonnen():
            return redirect("erhebungen:instruktion", teilnahme_link=teilnahme_link)
        case LaufendeSitzung() | OffenerSitzungsblock():
            return redirect("erhebungen:gespraech", token=bindung.token)
        case NaechsteVignette():
            vignette_beginnen(bindung)
            return redirect("erhebungen:gespraech", token=bindung.token)
        case OffenerAbschlussblock():
            return redirect("erhebungen:itemblock", token=bindung.token)
        case Ende():
            return redirect("erhebungen:abschluss", teilnahme_link=teilnahme_link)


def _umleitung_falls_woanders(
    request: HttpRequest, bindung: Erhebungsbindung
) -> HttpResponseRedirect | None:
    # Folgt dem Ablauf, solange er nicht auf die aufgerufene Seite selbst zeigt.

    weiter: HttpResponseRedirect = _weiter_im_ablauf(bindung)
    return None if weiter.url == request.path else weiter


def _sitzungsnavigation(token: str) -> Sitzungsnavigation:
    # Hält die Erhebungsrouten in der App, der die Erhebungsbindung gehört.

    return Sitzungsnavigation(
        bezeichnung="Erhebung",
        gespraech_url=reverse("erhebungen:gespraech", args=[token]),
        beenden_url=reverse("erhebungen:gespraech_beenden", args=[token]),
        debrief_url=reverse("erhebungen:debrief", args=[token]),
        abbrechen_url=reverse("erhebungen:abbrechen", args=[token]),
        transkription_url=reverse("erhebungen:transkription"),
    )


def _erhebungssitzung(token: str) -> tuple[Sitzung, Erhebungsbindung]:
    # Löst die laufende Sitzung in ihrer besitzenden Erhebungs-App auf.

    bindung = _laufende_bindung(token)
    sitzung: Sitzung | None = laufende_sitzung(bindung)
    if sitzung is None:
        raise Http404("Zu diesem Token läuft keine Sitzung.")
    return sitzung, bindung


def sitzung_fuer_transkription(request: HttpRequest) -> Sitzung:
    """Löst eine laufende Erhebungssitzung ausschließlich aus Browser-Tokens auf."""

    sitzung_pk: str | None = request.POST.get("sitzung_pk")
    if sitzung_pk is None:
        raise PermissionDenied
    jetzt: datetime = timezone.now()
    sitzung: Sitzung | None = (
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme")
        .filter(
            pk=sitzung_pk,
            status=Sitzung.Status.LAUFEND,
            teilnahme__erhebungsbindung__token__in=tokens_im_browser(request),
            teilnahme__erhebungsbindung__stichprobe__beginn__lte=jetzt,
            teilnahme__erhebungsbindung__stichprobe__ende__gte=jetzt,
        )
        .first()
    )
    if sitzung is None:
        raise PermissionDenied
    return sitzung


def gespraech(request: HttpRequest, token: str) -> HttpResponse:
    """Führt einen persistierten Gesprächsschritt anonym über das Token aus."""

    bindung: Erhebungsbindung = _laufende_bindung(token)
    sitzung: Sitzung | None = sitzung_am_zug(bindung)
    if sitzung is None:
        raise Http404("Zu diesem Token steht keine Sitzung offen.")
    return persistiertes_gespraech(
        request,
        sitzung,
        _sitzungsnavigation(token),
        sitzungsblock=lambda: _sitzungsblock_rendern(request, bindung, sitzung),
    )


def gespraech_beenden(request: HttpRequest, token: str) -> HttpResponse:
    """Zeigt für die tokenaufgelöste Sitzung den Debrief."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, _bindung = _erhebungssitzung(token)
    sink: DBSink = DBSink.fuer_sitzung(sitzung)
    sitzung_beenden(sink)
    return persistierten_debrief_anzeigen(request, sitzung, _sitzungsnavigation(token))


def abbrechen(request: HttpRequest, token: str) -> HttpResponse:
    """Bricht eine Erhebungssitzung ohne Diagnose ab."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung, bindung = _erhebungssitzung(token)
    sink: DBSink = DBSink.fuer_sitzung(sitzung)
    sitzung_abbrechen(sink)
    anhang: str = _sitzungsblock_rendern(request, bindung, sitzung)
    if anhang:
        return persistiertes_gespraech(
            request, sitzung, _sitzungsnavigation(token), sitzungsblock=lambda: anhang
        )
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
        DBSink.fuer_sitzung(sitzung).diagnose_setzen(
            request.POST["diagnose"],
            eingabemodus=Eingabemodus.aus_formular(request.POST.get("eingabemodus")),
        )
    anhang: str = _sitzungsblock_rendern(request, bindung, sitzung)
    if anhang:
        return persistierten_debrief_anzeigen(
            request, sitzung, _sitzungsnavigation(token), anhang
        )
    return _weiter_im_ablauf(bindung)


def _sitzungsblock_rendern(
    request: HttpRequest, bindung: Erhebungsbindung, sitzung: Sitzung
) -> str:
    # Rendert die Item-Antwortzeilen unter einer beendeten Sitzung.

    if not _sitzungsblock_ist_offen(bindung, sitzung.pk):
        return ""
    block: Itemblock | None = block_vorlegen(
        bindung, Erhebungsitem.Andockpunkt.NACH_SITZUNG, sitzung
    )
    if block is None:
        return ""
    return render_to_string(
        "erhebungen/includes/itemblock_form.html",
        {"formular": ItemblockFormular(block), "token": bindung.token},
        request=request,
    )


def _sitzungsblock_ist_offen(bindung: Erhebungsbindung, sitzung_pk: int) -> bool:
    # Prüft am Ablauf, ob gerade der Block dieser Sitzung an der Reihe ist.

    sitzung: Sitzung | None = sitzung_mit_offenem_block(bindung)
    return sitzung is not None and sitzung.pk == sitzung_pk


def _offener_block(bindung: Erhebungsbindung) -> Itemblock | None:
    # Fragt den Ablauf, welcher Block gerade offen ist, und legt ihn vor.

    match naechster_schritt(bindung):
        case OffenerSitzungsblock(sitzung):
            return block_vorlegen(
                bindung, Erhebungsitem.Andockpunkt.NACH_SITZUNG, sitzung
            )
        case OffenerAbschlussblock():
            return block_vorlegen(bindung, Erhebungsitem.Andockpunkt.AM_ENDE)
        case _:
            return None


def itemblock(request: HttpRequest, token: str) -> HttpResponse:
    """Zeigt und schreibt die freiwilligen Fragebogen-Items eines Blocks.

    Welcher Block gemeint ist, sagt der Ablauf und nicht das Abgeschickte; das
    Formular liest die Antwortzeilen dieses Blocks.
    """

    ist_htmx = bool(request.headers.get("HX-Request"))
    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    bindung = _laufende_bindung(token)
    teilnahme_link = bindung.stichprobe.teilnahme_link
    _bindung_in_session_speichern(request, bindung)
    if not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    if request.method == "GET":
        umleitung: HttpResponseRedirect | None = _umleitung_falls_woanders(
            request, bindung
        )
        if umleitung is not None:
            return umleitung
        abschlussblock: Itemblock | None = block_vorlegen(
            bindung, Erhebungsitem.Andockpunkt.AM_ENDE
        )
        if abschlussblock is None:
            return redirect("erhebungen:abschluss", teilnahme_link=teilnahme_link)
        formular = ItemblockFormular(abschlussblock)
    else:
        block: Itemblock | None = _offener_block(bindung)
        if block is None:
            return HttpResponseBadRequest("Zu dieser Teilnahme steht kein Block offen.")
        formular = ItemblockFormular(block, request.POST)
        if not formular.is_valid():
            return HttpResponseBadRequest(
                "Unzulässige Antwort auf ein Fragebogen-Item."
            )
        formular.speichern()
        if "weiter" in request.POST:
            block_erledigen(block)
            return _weiter_im_ablauf(bindung)
        # Ein frisches Formular legt den eben geschriebenen Stand wieder vor.
        formular = ItemblockFormular(block)
    template = (
        "erhebungen/includes/itemblock_form.html"
        if ist_htmx
        else "erhebungen/itemblock.html"
    )
    return render(request, template, {"formular": formular, "token": token})


def abschluss(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Zeigt nach allen Vignetten das definierte Ende der Erhebung."""

    stichprobe: Stichprobe = _laufende_stichprobe(teilnahme_link)
    bindung: Erhebungsbindung | None = _bindung_aus_session(request, stichprobe)
    if bindung is None or not bindung.teilnahme.einwilligung_erteilt:
        return redirect("erhebungen:einwilligung", teilnahme_link=teilnahme_link)
    umleitung: HttpResponseRedirect | None = _umleitung_falls_woanders(request, bindung)
    if umleitung is not None:
        return umleitung
    bindung_abschliessen(bindung)
    return render(
        request, "erhebungen/abschluss.html", {"erhebung": stichprobe.erhebung}
    )


def _bindung_aus_session(
    request: HttpRequest, stichprobe: Stichprobe
) -> Erhebungsbindung | None:
    """Lädt die zur Stichprobe passende Bindung des aktuellen Browsers."""

    token: str | None = token_aus_session(request, stichprobe.teilnahme_link)
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


def _bindung_in_session_speichern(
    request: HttpRequest, bindung: Erhebungsbindung
) -> None:
    """Bindet einen tokenbasierten Wiedereinstieg an den aktuellen Browser."""

    token_in_session_speichern(
        request, bindung.stichprobe.teilnahme_link, bindung.token
    )


def _laufende_bindung(token: str) -> Erhebungsbindung:
    """Löst eine Teilnahme über ihr Token innerhalb des laufenden Fensters auf."""

    bindung: Erhebungsbindung = get_object_or_404(
        Erhebungsbindung.objects.select_related("stichprobe", "teilnahme"),
        token=token,
    )
    if (
        bindung.stichprobe.archiviert
        or bindung.stichprobe.phase != Stichprobe.Phase.LAUFEND
    ):
        raise PermissionDenied
    return bindung


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

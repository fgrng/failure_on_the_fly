"""Schreibt die relationale Datenspur einer Erhebung als CSV-Dateien."""

import csv
import json
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime
from io import BytesIO, StringIO
from operator import attrgetter
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from django.db.models import Q, QuerySet
from django.utils import timezone

from fragebogen_items.models import FragebogenItem, LikertSkalenpol
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Vignettenposition,
)
from vignetten.models import Vignette

from .models import (
    Erhebung,
    Erhebungsbindung,
    ItemAntwort,
    Itemblock,
    Vignettenziehung,
)


def _zellenwert(wert: Any) -> str | int | bool:
    """Bildet NULL verlustfrei auf das Export-Literal ab."""

    if wert is None:
        return "NA"
    if isinstance(wert, datetime):
        return timezone.localtime(wert, timezone.UTC).isoformat(timespec="seconds")
    return wert


def _csv_aus_objekten(
    objekte: Iterable[Any],
    spalten: Sequence[str],
    **abgeleitet: Callable[[Any], Any],
) -> str:
    """Erzeugt eine RFC-4180-CSV mit einer Zeile je Objekt.

    Jede Spalte liest das gleichnamige Attribut, sofern ein abgeleiteter
    Zugriff sie nicht anders füllt. Die Kopfzeile steht auch ohne Datenzeile.

    Beispiel::

        _csv_aus_objekten(
            itembloecke,
            ("id", "teilnahme_token"),
            teilnahme_token=attrgetter("erhebungsbindung.token"),
        )
    """

    zugriffe: list[Callable[[Any], Any]] = [
        abgeleitet.get(spalte, attrgetter(spalte)) for spalte in spalten
    ]
    ausgabe: StringIO = StringIO(newline="")
    schreiber: Any = csv.writer(ausgabe)
    schreiber.writerow(spalten)
    schreiber.writerows(
        [_zellenwert(zugriff(objekt)) for zugriff in zugriffe] for objekt in objekte
    )
    return ausgabe.getvalue()


def datenspur_zip(erhebung: Erhebung) -> bytes:
    """Liefert den ersten Export-Durchstich für eine Erhebung als ZIP-Archiv."""

    bindungen: QuerySet[Erhebungsbindung] = (
        Erhebungsbindung.objects.filter(stichprobe__erhebung=erhebung)
        .select_related("teilnahme")
        .order_by("stichprobe_id", "pk")
    )
    ziehungen: QuerySet[Vignettenziehung] = Vignettenziehung.objects.filter(
        erhebungsbindung__stichprobe__erhebung=erhebung
    ).order_by("erhebungsbindung_id", "position")
    positionen: QuerySet[Vignettenposition] = Vignettenposition.objects.filter(
        teilnahme__erhebungsbindung__stichprobe__erhebung=erhebung
    ).order_by("teilnahme__erhebungsbindung__id", "position")
    sitzung_ids: QuerySet[Vignettenposition] = positionen.values("sitzung_id")
    itembloecke: QuerySet[Itemblock] = (
        Itemblock.objects.filter(erhebungsbindung__stichprobe__erhebung=erhebung)
        .select_related("erhebungsbindung")
        .order_by("erhebungsbindung_id", "pk")
    )
    # Antwortzeilen ohne Werte werden nicht herausgefiltert: erst sie
    # trennen »vorgelegt, nicht beantwortet« von »nie vorgelegt« (ADR-0041).
    antworten: QuerySet[ItemAntwort] = (
        ItemAntwort.objects.filter(erhebungsbindung__stichprobe__erhebung=erhebung)
        .select_related("erhebungsbindung", "erhebungsitem__item")
        .order_by("itemblock_id", "erhebungsitem__position", "pk")
    )
    vignetten: QuerySet[Vignette] = Vignette.objects.filter(
        Q(pk__in=ziehungen.values("vignette_id"))
        | Q(pk__in=positionen.values("vignette_id"))
    ).order_by("pk")
    kerne: QuerySet[Simulationskern] = Simulationskern.objects.filter(
        pk__in=positionen.values("sitzung__simulationskern_id")
    ).order_by("pk")
    konfigurationen: QuerySet[ModellKonfiguration] = ModellKonfiguration.objects.filter(
        Q(pk=erhebung.modell_konfiguration_id)
        | Q(pk__in=positionen.values("sitzung__modell_konfiguration_id"))
    ).order_by("pk")
    vorgelegte_items: QuerySet[FragebogenItem] = FragebogenItem.objects.filter(
        pk__in=antworten.values("erhebungsitem__item_id")
    ).order_by("pk")

    tabellen: dict[str, str] = {
        "erhebung.csv": _csv_aus_objekten(
            [erhebung],
            (
                "id",
                "name",
                "randomisierung",
                "instruktionstext",
                "einwilligungstext",
                "abschlusstext",
                "modell_konfiguration_id",
            ),
        ),
        "stichproben.csv": _csv_aus_objekten(
            erhebung.stichprobe_set.order_by("pk"),
            ("id", "beginn", "ende", "archiviert"),
        ),
        "teilnahmen.csv": _csv_aus_objekten(
            bindungen,
            (
                "token",
                "stichprobe_id",
                "sprachmodell_eingewilligt",
                "audioverarbeitung_eingewilligt",
                "speicherung_eingewilligt",
                "randomisierungs_seed",
                "erstellt_am",
            ),
            sprachmodell_eingewilligt=attrgetter("teilnahme.sprachmodell_eingewilligt"),
            audioverarbeitung_eingewilligt=attrgetter(
                "teilnahme.audioverarbeitung_eingewilligt"
            ),
            speicherung_eingewilligt=attrgetter("teilnahme.speicherung_eingewilligt"),
        ),
        "vignettenziehungen.csv": _csv_aus_objekten(
            ziehungen.select_related("erhebungsbindung"),
            ("token", "vignette_id", "position"),
            token=attrgetter("erhebungsbindung.token"),
        ),
        "sitzungen.csv": _csv_aus_objekten(
            positionen.select_related("teilnahme__erhebungsbindung", "sitzung"),
            (
                "id",
                "token",
                "position",
                "status",
                "vignette_id",
                "simulationskern_id",
                "modell_konfiguration_id",
                "erstellt_am",
                "verbrauchte_zeit",
            ),
            id=attrgetter("sitzung_id"),
            token=attrgetter("teilnahme.erhebungsbindung.token"),
            status=attrgetter("sitzung.status"),
            vignette_id=attrgetter("sitzung.vignette_id"),
            simulationskern_id=attrgetter("sitzung.simulationskern_id"),
            modell_konfiguration_id=attrgetter("sitzung.modell_konfiguration_id"),
            erstellt_am=attrgetter("sitzung.erstellt_am"),
            verbrauchte_zeit=attrgetter("sitzung.verbrauchte_zeit"),
        ),
        "gespraechsschritte.csv": _csv_aus_objekten(
            Gespraechsschritt.objects.filter(sitzung_id__in=sitzung_ids).order_by(
                "sitzung_id", "reihenfolge"
            ),
            (
                "id",
                "sitzung_id",
                "reihenfolge",
                "eingabe",
                "denkspur",
                "aeusserung",
                "erstellt_am",
                "eingabemodus",
            ),
        ),
        "fehlversuche.csv": _csv_aus_objekten(
            Fehlversuch.objects.filter(
                gespraechsschritt__sitzung_id__in=sitzung_ids
            ).order_by("gespraechsschritt_id", "pk"),
            ("gespraechsschritt_id", "grund", "rohantwort"),
        ),
        "diagnosen.csv": _csv_aus_objekten(
            Diagnose.objects.filter(sitzung_id__in=sitzung_ids).order_by("sitzung_id"),
            ("sitzung_id", "text", "erstellt_am", "eingabemodus"),
        ),
        "itembloecke.csv": _csv_aus_objekten(
            itembloecke,
            (
                "id",
                "teilnahme_token",
                "andockpunkt",
                "sitzung_id",
                "vorgelegt_am",
                "erledigt_am",
            ),
            teilnahme_token=attrgetter("erhebungsbindung.token"),
        ),
        "item_antworten.csv": _csv_aus_objekten(
            antworten,
            (
                "itemblock_id",
                "teilnahme_token",
                "item_id",
                "item_typ",
                "andockpunkt",
                "sitzung_id",
                "position",
                "freitext",
                "likert_stufe",
            ),
            teilnahme_token=attrgetter("erhebungsbindung.token"),
            item_id=attrgetter("erhebungsitem.item_id"),
            item_typ=attrgetter("erhebungsitem.item.typ"),
            andockpunkt=attrgetter("erhebungsitem.andockpunkt"),
            position=attrgetter("erhebungsitem.position"),
        ),
        "vignettenfassungen.csv": _csv_aus_objekten(
            vignetten,
            (
                "id",
                "historie_id",
                "finalisiert_am",
                "fehlermuster_beschreibung",
                "lernauftrag_text",
                "lernauftrag_bild",
                "lernauftrag_bildbeschreibung",
                "lernauftrag_simulationshinweise",
                "arbeitsheft_text",
                "arbeitsheft_bild",
                "arbeitsheft_bildbeschreibung",
                "arbeitsheft_simulationshinweise",
                "schuelerin_name",
                "schuelerin_geschlecht",
                "lehrperson_name",
                "lehrperson_geschlecht",
                "fach",
                "thema",
                "klassenstufe",
                "referenzdiagnose",
                "budget_typ",
                "budget_wert",
            ),
            lernauftrag_bild=attrgetter("lernauftrag_bild.name"),
            arbeitsheft_bild=attrgetter("arbeitsheft_bild.name"),
        ),
        "simulationskerne.csv": _csv_aus_objekten(
            kerne,
            (
                "id",
                "historie_id",
                "finalisiert_am",
                "system_prompt_vorlage",
                "user_prompt_vorlage",
                "rahmenhandlung_einleitung",
                "rahmenhandlung_gespraechseinleitung",
                "rahmenhandlung_debrief",
            ),
        ),
        "modellkonfigurationen.csv": _csv_aus_objekten(
            konfigurationen,
            ("id", "bezeichnung", "anbieter", "sprachmodell", "parameter"),
            parameter=lambda konfiguration: json.dumps(
                konfiguration.parameter, ensure_ascii=False
            ),
        ),
        "fragebogen_items.csv": _csv_aus_objekten(
            vorgelegte_items, ("id", "typ", "wortlaut")
        ),
        "likert_skala.csv": _csv_aus_objekten(
            LikertSkalenpol,
            ("stufe", "pol"),
            stufe=LikertSkalenpol.stufe_fuer,
            pol=attrgetter("value"),
        ),
    }
    ausgabe: BytesIO = BytesIO()
    with ZipFile(ausgabe, "w", compression=ZIP_DEFLATED) as zip_datei:
        for dateiname, inhalt in tabellen.items():
            zip_datei.writestr(dateiname, inhalt)
    return ausgabe.getvalue()

"""Schreibt die relationale Datenspur einer Erhebung als CSV-Dateien."""

import csv
import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from django.db.models import Q, QuerySet
from django.utils import timezone

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Diagnose, Fehlversuch, Gespraechsschritt
from vignetten.models import Vignette

from .models import Erhebung, Erhebungsbindung, Vignettenposition, Vignettenziehung


def _zellenwert(wert: Any) -> str | int | bool:
    """Bildet NULL verlustfrei auf das Export-Literal ab."""

    if wert is None:
        return "NA"
    if isinstance(wert, datetime):
        return timezone.localtime(wert, timezone.UTC).isoformat(timespec="seconds")
    return wert


def _csv_inhalt(spalten: Sequence[str], zeilen: Iterable[Sequence[Any]]) -> str:
    """Erzeugt eine RFC-4180-CSV, auch wenn keine Datenzeilen vorliegen."""

    ausgabe: StringIO = StringIO(newline="")
    schreiber: Any = csv.writer(ausgabe)
    schreiber.writerow(spalten)
    schreiber.writerows(
        [_zellenwert(wert) for wert in zeile] for zeile in zeilen
    )
    return ausgabe.getvalue()


def datenspur_zip(erhebung: Erhebung) -> bytes:
    """Liefert den ersten Export-Durchstich für eine Erhebung als ZIP-Archiv."""

    ausgabe: BytesIO = BytesIO()
    bindungen: Iterable[Erhebungsbindung] = (
        Erhebungsbindung.objects.filter(stichprobe__erhebung=erhebung)
        .select_related("teilnahme")
        .order_by("stichprobe_id", "pk")
    )
    with ZipFile(ausgabe, "w", compression=ZIP_DEFLATED) as zip_datei:
        zip_datei.writestr(
            "erhebung.csv",
            _csv_inhalt(
                (
                    "id",
                    "name",
                    "randomisierung",
                    "instruktionstext",
                    "einwilligungstext",
                    "abschlusstext",
                    "modell_konfiguration_id",
                ),
                [
                    (
                        erhebung.pk,
                        erhebung.name,
                        erhebung.randomisierung,
                        erhebung.instruktionstext,
                        erhebung.einwilligungstext,
                        erhebung.abschlusstext,
                        erhebung.modell_konfiguration_id,
                    )
                ],
            ),
        )
        zip_datei.writestr(
            "stichproben.csv",
            _csv_inhalt(
                ("id", "beginn", "ende", "archiviert"),
                (
                    (stichprobe.pk, stichprobe.beginn, stichprobe.ende, stichprobe.archiviert)
                    for stichprobe in erhebung.stichprobe_set.order_by("pk")
                ),
            ),
        )
        zip_datei.writestr(
            "teilnahmen.csv",
            _csv_inhalt(
                (
                    "token",
                    "stichprobe_id",
                    "einwilligung_erteilt",
                    "audioverarbeitung_eingewilligt",
                    "randomisierungs_seed",
                    "erstellt_am",
                ),
                (
                    (
                        bindung.token,
                        bindung.stichprobe_id,
                        bindung.teilnahme.einwilligung_erteilt,
                        bindung.teilnahme.audioverarbeitung_eingewilligt,
                        bindung.randomisierungs_seed,
                        bindung.erstellt_am,
                    )
                    for bindung in bindungen
                ),
            ),
        )
        ziehungen: QuerySet[Vignettenziehung] = (
            Vignettenziehung.objects.filter(
                erhebungsbindung__stichprobe__erhebung=erhebung
            ).order_by("erhebungsbindung_id", "position")
        )
        ziehung_vignetten_ids = ziehungen.values("vignette_id")
        zip_datei.writestr(
            "vignettenziehungen.csv",
            _csv_inhalt(
                ("token", "vignette_id", "position"),
                (
                    (
                        ziehung.erhebungsbindung.token,
                        ziehung.vignette_id,
                        ziehung.position,
                    )
                    for ziehung in ziehungen.select_related("erhebungsbindung")
                ),
            ),
        )
        positionen: QuerySet[Vignettenposition] = (
            Vignettenposition.objects.filter(
                erhebungsbindung__stichprobe__erhebung=erhebung
            ).order_by("erhebungsbindung_id", "position")
        )
        zip_datei.writestr(
            "sitzungen.csv",
            _csv_inhalt(
                (
                    "id",
                    "token",
                    "position",
                    "status",
                    "vignette_id",
                    "simulationskern_id",
                    "modell_konfiguration_id",
                    "erstellt_am",
                ),
                (
                    (
                        position.sitzung_id,
                        position.erhebungsbindung.token,
                        position.position,
                        position.sitzung.status,
                        position.sitzung.vignette_id,
                        position.sitzung.simulationskern_id,
                        position.sitzung.modell_konfiguration_id,
                        position.sitzung.erstellt_am,
                    )
                    for position in positionen.select_related(
                        "erhebungsbindung", "sitzung"
                    )
                ),
            ),
        )
        sitzung_ids = positionen.values("sitzung_id")
        gespraechsschritte: Iterable[Gespraechsschritt] = (
            Gespraechsschritt.objects.filter(sitzung_id__in=sitzung_ids).order_by(
                "sitzung_id", "reihenfolge"
            )
        )
        zip_datei.writestr(
            "gespraechsschritte.csv",
            _csv_inhalt(
                (
                    "id",
                    "sitzung_id",
                    "reihenfolge",
                    "eingabe",
                    "denkspur",
                    "aeusserung",
                    "native_reasoning_spur",
                    "erstellt_am",
                ),
                (
                    (
                        schritt.pk,
                        schritt.sitzung_id,
                        schritt.reihenfolge,
                        schritt.eingabe,
                        schritt.denkspur,
                        schritt.aeusserung,
                        schritt.native_reasoning_spur,
                        schritt.erstellt_am,
                    )
                    for schritt in gespraechsschritte
                ),
            ),
        )
        zip_datei.writestr(
            "fehlversuche.csv",
            _csv_inhalt(
                ("gespraechsschritt_id", "grund", "rohantwort"),
                (
                    (
                        fehlversuch.gespraechsschritt_id,
                        fehlversuch.grund,
                        fehlversuch.rohantwort,
                    )
                    for fehlversuch in Fehlversuch.objects.filter(
                        gespraechsschritt__sitzung_id__in=sitzung_ids
                    ).order_by("gespraechsschritt_id", "pk")
                ),
            ),
        )
        zip_datei.writestr(
            "diagnosen.csv",
            _csv_inhalt(
                ("sitzung_id", "text", "erstellt_am"),
                (
                    (diagnose.sitzung_id, diagnose.text, diagnose.erstellt_am)
                    for diagnose in Diagnose.objects.filter(
                        sitzung_id__in=sitzung_ids
                    ).order_by("sitzung_id")
                ),
            ),
        )
        vignetten: QuerySet[Vignette] = Vignette.objects.filter(
            Q(
                pk__in=ziehung_vignetten_ids
            )
            | Q(pk__in=positionen.values("vignette_id"))
        ).order_by("pk")
        zip_datei.writestr(
            "vignettenfassungen.csv",
            _csv_inhalt(
                (
                    "id",
                    "historie_id",
                    "finalisiert_am",
                    "fehlermuster_beschreibung",
                    "lernauftrag",
                    "arbeitsheft_beschreibung",
                    "arbeitsheft_text",
                    "arbeitsheft_bild",
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
                (
                    (
                        vignette.pk,
                        vignette.historie_id,
                        vignette.finalisiert_am,
                        vignette.fehlermuster_beschreibung,
                        vignette.lernauftrag,
                        vignette.arbeitsheft_beschreibung,
                        vignette.arbeitsheft_text,
                        vignette.arbeitsheft_bild.name,
                        vignette.schuelerin_name,
                        vignette.schuelerin_geschlecht,
                        vignette.lehrperson_name,
                        vignette.lehrperson_geschlecht,
                        vignette.fach,
                        vignette.thema,
                        vignette.klassenstufe,
                        vignette.referenzdiagnose,
                        vignette.budget_typ,
                        vignette.budget_wert,
                    )
                    for vignette in vignetten
                ),
            ),
        )
        kerne: QuerySet[Simulationskern] = Simulationskern.objects.filter(
            pk__in=positionen.values("sitzung__simulationskern_id")
        ).order_by("pk")
        zip_datei.writestr(
            "simulationskerne.csv",
            _csv_inhalt(
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
                (
                    (
                        kern.pk,
                        kern.historie_id,
                        kern.finalisiert_am,
                        kern.system_prompt_vorlage,
                        kern.user_prompt_vorlage,
                        kern.rahmenhandlung_einleitung,
                        kern.rahmenhandlung_gespraechseinleitung,
                        kern.rahmenhandlung_debrief,
                    )
                    for kern in kerne
                ),
            ),
        )
        konfigurationen: QuerySet[ModellKonfiguration] = (
            ModellKonfiguration.objects.filter(
                Q(pk=erhebung.modell_konfiguration_id)
                | Q(pk__in=positionen.values("sitzung__modell_konfiguration_id"))
            ).order_by("pk")
        )
        zip_datei.writestr(
            "modellkonfigurationen.csv",
            _csv_inhalt(
                ("id", "sprachmodell", "parameter"),
                (
                    (
                        konfiguration.pk,
                        konfiguration.sprachmodell,
                        json.dumps(konfiguration.parameter, ensure_ascii=False),
                    )
                    for konfiguration in konfigurationen
                ),
            ),
        )
    return ausgabe.getvalue()

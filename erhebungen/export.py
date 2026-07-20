"""Schreibt die relationale Datenspur einer Erhebung als CSV-Dateien."""

import csv
from collections.abc import Iterable, Sequence
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from django.utils import timezone

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
        ziehungen: Iterable[Vignettenziehung] = (
            Vignettenziehung.objects.filter(
                erhebungsbindung__stichprobe__erhebung=erhebung
            ).order_by("erhebungsbindung_id", "position")
        )
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
        positionen: Iterable[Vignettenposition] = (
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
    return ausgabe.getvalue()

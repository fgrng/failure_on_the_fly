"""Lesezugriff der Export-Tests auf das Archiv der Datenspur."""

import csv
from collections.abc import Iterator
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile

from django.http import HttpResponse


def _dateien(antwort: HttpResponse) -> Iterator[tuple[str, TextIOWrapper]]:
    """Liefert je Datei des Archivs ihren Namen und ihren Text."""

    with ZipFile(BytesIO(antwort.content)) as archiv:
        for name in archiv.namelist():
            yield name, TextIOWrapper(archiv.open(name), encoding="utf-8")


def export_lesen(antwort: HttpResponse) -> dict[str, list[dict[str, str]]]:
    """Liefert je Datei des Archivs ihre Datenzeilen, nach Spaltennamen gelesen."""

    return {name: list(csv.DictReader(text)) for name, text in _dateien(antwort)}


def export_kopfzeilen(antwort: HttpResponse) -> dict[str, list[str]]:
    """Liefert je Datei des Archivs ihre Kopfzeile, auch ohne Datenzeile."""

    return {name: next(csv.reader(text)) for name, text in _dateien(antwort)}

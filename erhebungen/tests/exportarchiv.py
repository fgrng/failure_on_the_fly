"""Lesezugriff der Export-Tests auf das Archiv der Datenspur."""

import csv
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile

from django.http import HttpResponse


def export_lesen(antwort: HttpResponse) -> dict[str, list[dict[str, str]]]:
    """Liefert je Datei des Archivs ihre Datenzeilen, nach Spaltennamen gelesen."""

    with ZipFile(BytesIO(antwort.content)) as archiv:
        return {
            name: list(
                csv.DictReader(TextIOWrapper(archiv.open(name), encoding="utf-8"))
            )
            for name in archiv.namelist()
        }


def export_kopfzeilen(antwort: HttpResponse) -> dict[str, list[str]]:
    """Liefert je Datei des Archivs ihre Kopfzeile, auch ohne Datenzeile."""

    with ZipFile(BytesIO(antwort.content)) as archiv:
        return {
            name: next(csv.reader(TextIOWrapper(archiv.open(name), encoding="utf-8")))
            for name in archiv.namelist()
        }

"""Gemeinsame Form der ZIP-Downloads aus den Eigentümer-Kreisen."""

from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify


def zip_download(art: str, pk: int, name: str, inhalt: bytes) -> HttpResponse:
    """Liefert ZIP-Bytes als Download, benannt nach Bestand und UTC-Zeitstempel.

    Beispiel: ``zip_download("training", 7, "Bruchrechnung", daten)`` heißt
    ``training-7-bruchrechnung-20261009T120000Z.zip``.
    """

    zeitstempel: str = (
        timezone.now().astimezone(timezone.UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    dateiname: str = f"{art}-{pk}-{slugify(name)}-{zeitstempel}.zip"
    response: HttpResponse = HttpResponse(inhalt, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response

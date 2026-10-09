"""Gemeinsames Lesen der Trainingsseiten in den Tests."""

import json
import re

from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from konten.models import Konto
from training.models import Training


def tabellenzeilen(antwort: HttpResponse) -> list[dict[str, object]]:
    """Liefert die Zeilen, die eine Tabellenseite als JSON an Alpine ausliefert."""

    if antwort.status_code != 200:
        raise AssertionError(f"Die Seite antwortet mit {antwort.status_code}.")
    treffer: re.Match[str] | None = re.search(
        r'<script id="trainings-data" type="application/json">(.*?)</script>',
        antwort.content.decode(),
        re.DOTALL,
    )
    if treffer is None:
        raise AssertionError("Die Seite liefert keine Tabellenzeilen aus.")
    return json.loads(treffer.group(1))


def kuratierseite(client: Client, training: Training, konto: Konto) -> str:
    """Liefert den Inhalt der Kuratierseite eines Trainings aus Sicht des Kontos."""

    client.force_login(konto)
    antwort: HttpResponse = client.get(
        reverse("training:kuratieren", args=[training.pk])
    )
    if antwort.status_code != 200:
        raise AssertionError(f"Die Seite antwortet mit {antwort.status_code}.")
    return antwort.content.decode()

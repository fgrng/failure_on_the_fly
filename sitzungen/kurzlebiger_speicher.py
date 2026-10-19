"""Der kurzlebige Speicher für vorgehaltene Inhalte.

Einträge liegen als Dateien in `FLUECHTIG_PFAD`, außerhalb der
Forschungsdatenbank und jedes Backups. Jeder Eintrag gilt bis einen Tag nach
seinem letzten Schreiben; danach ist er abgelaufen und wird nicht mehr
geliefert. Der Speicher kennt nur Schlüssel, weder Token noch Konto (ADR-0055).
"""

import json
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

FRIST: timedelta = timedelta(days=1)
_GUELTIGER_SCHLUESSEL: re.Pattern[str] = re.compile(r"[a-z0-9-]+")


def lesen(schluessel: str) -> Any | None:
    """Liefert den Inhalt eines Eintrags, oder nichts, wenn er fehlt oder abgelaufen ist.

    Das Lesen verschiebt die Frist nicht.
    """

    try:
        eintrag: dict[str, Any] = json.loads(_datei(schluessel).read_text("utf-8"))
    except FileNotFoundError:
        return None
    if datetime.fromisoformat(eintrag["bis"]) <= timezone.now():
        return None
    return eintrag["inhalt"]


def schreiben(schluessel: str, inhalt: Any) -> None:
    """Legt den Inhalt unter dem Schlüssel ab und setzt die Frist neu an."""

    verzeichnis: Path = _verzeichnis()
    eintrag: str = json.dumps(
        {"bis": (timezone.now() + FRIST).isoformat(), "inhalt": inhalt}
    )
    # Erst vollständig schreiben, dann ersetzen: Ein paralleler Leser sieht
    # nie einen halben Eintrag.
    deskriptor, temporaer = tempfile.mkstemp(dir=verzeichnis)
    with os.fdopen(deskriptor, "w", encoding="utf-8") as datei:
        datei.write(eintrag)
    os.replace(temporaer, _datei(schluessel))


def vorhalten(schluessel: str) -> None:
    """Verschiebt die Frist eines noch gültigen Eintrags auf einen Tag ab jetzt.

    Ein abgelaufener Eintrag bleibt abgelaufen.
    """

    inhalt: Any | None = lesen(schluessel)
    if inhalt is not None:
        schreiben(schluessel, inhalt)


def _verzeichnis() -> Path:
    # Legt das Verzeichnis bei Bedarf an, nur für den Dienst lesbar.

    verzeichnis: Path = Path(settings.FLUECHTIG_PFAD)
    verzeichnis.mkdir(mode=0o700, parents=True, exist_ok=True)
    return verzeichnis


def _datei(schluessel: str) -> Path:
    # Der Schlüssel wird Dateiname und darf deshalb nicht aus dem Verzeichnis führen.

    if not _GUELTIGER_SCHLUESSEL.fullmatch(schluessel):
        raise ValueError(f"Unzulässiger Schlüssel: {schluessel!r}")
    return Path(settings.FLUECHTIG_PFAD) / schluessel

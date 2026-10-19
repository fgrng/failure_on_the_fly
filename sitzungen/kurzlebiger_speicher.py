"""Der kurzlebige Speicher für vorgehaltene Inhalte.

Einträge liegen als Dateien in `FLUECHTIG_PFAD`, außerhalb der
Forschungsdatenbank und jedes Backups. Jeder Eintrag gilt bis einen Tag nach
seinem letzten Schreiben oder Vorhalten; danach ist er abgelaufen und wird
nicht mehr geliefert. Der Speicher kennt nur Schlüssel, weder Token noch Konto
(ADR-0055).
"""

import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

_FRIST: timedelta = timedelta(days=1)
_GUELTIGER_SCHLUESSEL: re.Pattern[str] = re.compile(r"[a-z0-9-]+")


def lesen(schluessel: str) -> Any | None:
    """Liefert den Inhalt eines Eintrags, oder nichts, wenn er fehlt oder abgelaufen ist.

    Das Lesen verschiebt die Frist nicht.
    """

    datei: Path = _datei(schluessel)
    try:
        if _ist_abgelaufen(datei):
            return None
        return json.loads(datei.read_text("utf-8"))
    except FileNotFoundError:
        return None


def schreiben(schluessel: str, inhalt: Any) -> None:
    """Legt den Inhalt unter dem Schlüssel ab und setzt die Frist neu an."""

    ziel: Path = _datei(schluessel)
    # Erst vollständig schreiben, dann ersetzen: Ein paralleler Leser sieht
    # nie einen halben Eintrag.
    deskriptor, temporaer = tempfile.mkstemp(dir=_verzeichnis())
    try:
        with os.fdopen(deskriptor, "w", encoding="utf-8") as datei:
            datei.write(json.dumps(inhalt))
        _frist_ansetzen(Path(temporaer))
        os.replace(temporaer, ziel)
    except BaseException:
        Path(temporaer).unlink(missing_ok=True)
        raise


def vorhalten(schluessel: str) -> None:
    """Verschiebt die Frist eines noch gültigen Eintrags auf einen Tag ab jetzt.

    Ein abgelaufener Eintrag bleibt abgelaufen. Der Inhalt bleibt unberührt,
    damit ein gleichzeitiges Schreiben nicht überschrieben wird.
    """

    datei: Path = _datei(schluessel)
    try:
        if not _ist_abgelaufen(datei):
            _frist_ansetzen(datei)
    except FileNotFoundError:
        return


def loeschen(schluessel: str) -> None:
    """Entfernt einen Eintrag; ein fehlender ist schon gelöscht."""

    _datei(schluessel).unlink(missing_ok=True)


def alle_loeschen(praefix: str) -> None:
    """Entfernt jeden Eintrag, dessen Schlüssel mit dem Präfix beginnt."""

    for datei in _verzeichnis().glob(f"{_datei(praefix).name}*"):
        datei.unlink(missing_ok=True)


def _ist_abgelaufen(datei: Path) -> bool:
    # Die Frist läuft einen Tag ab dem letzten Schreiben oder Vorhalten, das
    # die Änderungszeit der Datei festhält.

    geaendert: datetime = datetime.fromtimestamp(datei.stat().st_mtime, tz=UTC)
    return geaendert + _FRIST <= timezone.now()


def _frist_ansetzen(datei: Path) -> None:
    # Setzt die Änderungszeit auf jetzt, nach der gesteuerten Uhr von Django.

    jetzt: float = timezone.now().timestamp()
    os.utime(datei, (jetzt, jetzt))


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

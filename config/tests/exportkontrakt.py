"""Zugriff der Export-Tests auf die Kontrakttabelle aus ADR-0029."""

from pathlib import Path


REPO_ROOT: Path = Path(__file__).parents[2]
ADR_0029_PATH: Path = REPO_ROOT / "docs/adr/0029-datenspur-export-kontrakt.md"


def exportkontrakt_aus_adr_0029() -> dict[str, list[str]]:
    """Liefert je Datei der Kontrakttabelle des Export-ADR ihre Spalten."""
    dateiformat: str = (
        ADR_0029_PATH.read_text().split("## Dateiformat")[1].split("\n## ")[0]
    )
    kontrakt: dict[str, list[str]] = {}
    for zeile in dateiformat.splitlines():
        if zeile.startswith("| `"):
            datei, *spalten = zeile.split("`")[1::2]
            kontrakt[datei] = spalten
    return kontrakt

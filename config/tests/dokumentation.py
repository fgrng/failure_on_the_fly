"""Gemeinsame Zugriffe der Vertragstests auf die Projektdokumentation."""

from pathlib import Path


REPO_ROOT: Path = Path(__file__).parents[2]
CONTEXT_PATH: Path = REPO_ROOT / "CONTEXT.md"
README_PATH: Path = REPO_ROOT / "README.md"
VERHALTEN_PATH: Path = REPO_ROOT / "docs/verhalten.md"
ADR_0029_PATH: Path = REPO_ROOT / "docs/adr/0029-datenspur-export-kontrakt.md"


def in_einer_zeile(text: str) -> str:
    """Faltet den Text zu einer Zeile, damit der Umbruch nichts verdeckt."""
    return " ".join(text.split())


def abschnitt(pfad: Path, ueberschrift: str) -> str:
    """Liefert den Rohtext des Abschnitts unter der Überschrift."""
    return pfad.read_text().split(f"## {ueberschrift}")[1].split("\n## ")[0]


def readme_abschnitt(ueberschrift: str) -> str:
    """Liefert den README-Abschnitt unter der Überschrift in einer Zeile."""
    return in_einer_zeile(abschnitt(README_PATH, ueberschrift))


def verhalten_abschnitt(ueberschrift: str) -> str:
    """Liefert den Abschnitt der Verhaltensdoku unter der Überschrift in einer Zeile."""
    return in_einer_zeile(abschnitt(VERHALTEN_PATH, ueberschrift))


def glossareintrag(begriff: str) -> str:
    """Liefert den Glossartext zu einem Begriff aus CONTEXT.md in einer Zeile."""
    eintrag: str = (
        CONTEXT_PATH.read_text().split(f"\n**{begriff}**:")[1].split("\n_Avoid_")[0]
    )
    return in_einer_zeile(eintrag)


def exportkontrakt_aus_adr_0029() -> dict[str, list[str]]:
    """Liefert je Datei der Kontrakttabelle des Export-ADR ihre Spalten."""
    kontrakt: dict[str, list[str]] = {}
    for zeile in abschnitt(ADR_0029_PATH, "Dateiformat").splitlines():
        if zeile.startswith("| `"):
            datei, *spalten = zeile.split("`")[1::2]
            kontrakt[datei] = spalten
    return kontrakt

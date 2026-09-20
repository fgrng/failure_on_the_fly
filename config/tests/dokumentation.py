"""Gemeinsame Zugriffe der Vertragstests auf die Projektdokumentation."""

from pathlib import Path


REPO_ROOT: Path = Path(__file__).parents[2]
CONTEXT_PATH: Path = REPO_ROOT / "CONTEXT.md"
README_PATH: Path = REPO_ROOT / "README.md"


def readme_abschnitt(ueberschrift: str) -> str:
    """Liefert den README-Abschnitt unter der Überschrift in einer Zeile."""
    abschnitt: str = (
        README_PATH.read_text().split(f"## {ueberschrift}")[1].split("\n## ")[0]
    )
    return " ".join(abschnitt.split())


def glossareintrag(begriff: str) -> str:
    """Liefert den Glossartext zu einem Begriff aus CONTEXT.md in einer Zeile."""
    eintrag: str = (
        CONTEXT_PATH.read_text().split(f"\n**{begriff}**:")[1].split("\n_Avoid_")[0]
    )
    return " ".join(eintrag.split())

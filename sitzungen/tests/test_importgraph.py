"""Kontrakttest zur Kantenrichtung aus ADR-0016.

Die Apps liegen nebeneinander unter der Projektwurzel; ihre Quellen werden
gelesen, nicht geladen. Ein `import erhebungen` in dieser Datei wäre selbst die
Kante, die der erste Test verbietet.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

import sitzungen

_PROJEKTWURZEL: Path = Path(sitzungen.__file__).parent.parent


def _absolut_importierte_module(baum: ast.Module) -> set[str]:
    # Sammelt jeden absoluten Import einer Datei, gleich auf welcher
    # Verschachtelungstiefe. Relative Importe bleiben außen vor: Sie zeigen
    # per Definition innerhalb der eigenen App und sind nie eine App-Kante.

    module: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            module.update(alias.name for alias in knoten.names)
        elif (
            isinstance(knoten, ast.ImportFrom)
            and knoten.level == 0
            and knoten.module is not None
        ):
            module.add(knoten.module)
    return module


def _quellen(app: str, *, mit_tests: bool) -> list[Path]:
    # Sammelt die Dateien einer App; die Wurzel wird gelesen, nicht importiert.

    wurzel: Path = _PROJEKTWURZEL / app
    assert wurzel.is_dir(), f"Die App {app} liegt nicht neben `sitzungen`."
    return [
        datei
        for datei in sorted(wurzel.rglob("*.py"))
        if mit_tests or "tests" not in datei.parts
    ]


def _verstoesse(dateien: list[Path], *verbotene_apps: str) -> list[str]:
    # Nennt jede Datei, die eine der verbotenen Apps importiert.

    gefunden: list[str] = []
    for datei in dateien:
        baum: ast.Module = ast.parse(datei.read_text(encoding="utf-8"))
        for modul in _absolut_importierte_module(baum):
            if modul.split(".")[0] in verbotene_apps:
                gefunden.append(f"{datei.relative_to(_PROJEKTWURZEL)}: {modul}")
    return gefunden


class ImportgraphTests(SimpleTestCase):
    """Die Kanten zwischen den Apps zeigen in genau eine Richtung (ADR-0016)."""

    def test_sitzungen_importiert_weder_training_noch_erhebungen(self) -> None:
        """Auch ein funktionslokaler Import wäre eine Kante zum Aufrufer."""
        quellen: list[Path] = _quellen("sitzungen", mit_tests=True)

        self.assertEqual(_verstoesse(quellen, "training", "erhebungen"), [])

    def test_erhebungen_importiert_training_nicht(self) -> None:
        """`erhebungen` darf nichts von Konten wissen (ADR-0006, ADR-0043).

        Die Abschrift liest die Erhebungsbindung von `training` aus; die
        Gegenrichtung brächte ein Konto in die App, die keines kennen darf.
        Die Tests der App bleiben außen vor: Sie stellen Trainingsdaten her,
        um zu zeigen, dass die Erhebung sie nicht anfasst.
        """
        quellen: list[Path] = _quellen("erhebungen", mit_tests=False)

        self.assertEqual(_verstoesse(quellen, "training"), [])

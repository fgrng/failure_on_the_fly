"""Kontrakttest zur Kantenrichtung aus ADR-0016."""

import ast
from pathlib import Path

from django.test import SimpleTestCase

import sitzungen

_VERBOTENE_APPS: frozenset[str] = frozenset({"training", "erhebungen"})


def _importierte_module(baum: ast.AST) -> set[str]:
    # Sammelt jeden Import einer Datei, gleich auf welcher Verschachtelungstiefe.

    module: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            module.update(alias.name for alias in knoten.names)
        elif isinstance(knoten, ast.ImportFrom) and knoten.module is not None:
            module.add(knoten.module)
    return module


class ImportgraphTests(SimpleTestCase):
    """`sitzungen` kennt seine beiden Aufrufer-Apps nicht (ADR-0016)."""

    def test_sitzungen_importiert_weder_training_noch_erhebungen(self) -> None:
        """Auch ein funktionslokaler Import wäre eine Kante zum Aufrufer."""
        wurzel: Path = Path(sitzungen.__file__).parent
        verstoesse: list[str] = []

        for datei in sorted(wurzel.rglob("*.py")):
            baum: ast.AST = ast.parse(datei.read_text(encoding="utf-8"))
            for modul in _importierte_module(baum):
                if modul.split(".")[0] in _VERBOTENE_APPS:
                    verstoesse.append(f"{datei.relative_to(wurzel)}: {modul}")

        self.assertEqual(verstoesse, [])

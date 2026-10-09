"""Kontrakttest zum App-Graphen aus ADR-0016.

Die Apps liegen nebeneinander unter der Projektwurzel; ihre Quellen werden
gelesen, nicht geladen. Gezählt wird jeder absolute Import, auch ein
funktionslokaler und einer nur zur Typprüfung: Im Graphen steht er trotzdem.
"""

import ast
from pathlib import Path

import pytest
from django.conf import settings

_PROJEKTWURZEL: Path = Path(settings.BASE_DIR)

# Wohin der Produktionscode jeder App zeigen darf (ADR-0016, ADR-0037). Die
# Tabelle ist die Kantenrichtung: Eine Kante hinzuzufügen ist eine Aussage über
# die Architektur und gehört in ein ADR, nicht nur hierher. `konten` zeigt auf
# keine App; `config` und `texte` sind Querschnitt, auf den nur gezeigt wird;
# `seeds` ist das Blatt, das alles kennen darf.
_KANTEN: dict[str, frozenset[str]] = {
    "config": frozenset(),
    "konten": frozenset(),
    "texte": frozenset({"konten"}),
    "fragebogen_items": frozenset({"konten"}),
    "simulation": frozenset({"konten"}),
    "vignetten": frozenset({"konten", "simulation"}),
    "sitzungen": frozenset({"konten", "texte", "simulation", "vignetten"}),
    "erhebungen": frozenset(
        {
            "config",
            "konten",
            "texte",
            "fragebogen_items",
            "simulation",
            "vignetten",
            "sitzungen",
        }
    ),
    "training": frozenset(
        {
            "config",
            "konten",
            "texte",
            "simulation",
            "vignetten",
            "sitzungen",
            "erhebungen",
        }
    ),
    "seeds": frozenset(
        {
            "konten",
            "texte",
            "fragebogen_items",
            "simulation",
            "vignetten",
            "sitzungen",
            "erhebungen",
            "training",
        }
    ),
}


def _projekt_apps() -> set[str]:
    # Die Apps dieses Projekts: installiert und als Verzeichnis an der Wurzel.

    return {app for app in settings.INSTALLED_APPS if (_PROJEKTWURZEL / app).is_dir()}


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

    return [
        datei
        for datei in sorted((_PROJEKTWURZEL / app).rglob("*.py"))
        if mit_tests or "tests" not in datei.parts
    ]


def _verstoesse(dateien: list[Path], app: str, erlaubt: frozenset[str]) -> list[str]:
    # Nennt je Datei jeden Import, der in eine andere Projekt-App außerhalb
    # der erlaubten führt.

    verboten: set[str] = _projekt_apps() - erlaubt - {app}
    gefunden: list[str] = []
    for datei in dateien:
        baum: ast.Module = ast.parse(datei.read_text(encoding="utf-8"))
        for modul in sorted(_absolut_importierte_module(baum)):
            if modul.split(".")[0] in verboten:
                gefunden.append(f"{datei.relative_to(_PROJEKTWURZEL)}: {modul}")
    return gefunden


def test_jede_app_steht_in_der_kantentabelle() -> None:
    """Eine neue App bekommt ihre Kanten, bevor sie Code enthält."""

    assert _projekt_apps() == set(_KANTEN)


@pytest.mark.parametrize("app", sorted(_KANTEN))
def test_app_zeigt_nur_entlang_der_kantentabelle(app: str) -> None:
    """Keine Kante gegen die Richtung aus ADR-0016, auch keine zyklische."""

    quellen: list[Path] = _quellen(app, mit_tests=False)

    assert _verstoesse(quellen, app, _KANTEN[app]) == []


def test_sitzungen_kennt_auch_in_tests_weder_training_noch_erhebungen() -> None:
    """Eine Sitzung ist die atomare Auswertungseinheit; ihre Aufrufer bleiben fremd.

    Anders als bei den übrigen Apps gilt das auch für die Tests: Ein Test, der
    einen Aufrufer braucht, prüft ihn und gehört zu ihm.
    """

    quellen: list[Path] = _quellen("sitzungen", mit_tests=True)
    erlaubt: frozenset[str] = frozenset(_projekt_apps() - {"training", "erhebungen"})

    assert _verstoesse(quellen, "sitzungen", erlaubt) == []

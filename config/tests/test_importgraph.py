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
# die Architektur und gehört in ein ADR, nicht nur hierher. `konten` und
# `config` zeigen auf keine App; `texte` ist Querschnitt und zeigt nur auf
# `konten`; `seeds` ist das Blatt, das alle Domänen-Apps kennen darf.
_KANTEN: dict[str, frozenset[str]] = {
    "config": frozenset(),
    "konten": frozenset(),
    "texte": frozenset({"konten"}),
    "fragebogen_items": frozenset({"konten"}),
    "simulation": frozenset({"konten"}),
    "vignetten": frozenset({"konten", "simulation"}),
    "sitzungen": frozenset({"konten", "texte", "simulation", "vignetten"}),
    # Nichts zeigt auf `evals`; `vignetten` liest den Evallauf allein über den
    # Reverse-Accessor und verlinkt per URL-Name (ADR-0046).
    "evals": frozenset({"konten", "simulation", "vignetten"}),
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

    wurzel: Path = _PROJEKTWURZEL / app
    assert wurzel.is_dir(), f"Die App {app} liegt nicht an der Projektwurzel."
    return [
        datei
        for datei in sorted(wurzel.rglob("*.py"))
        if mit_tests or "tests" not in datei.parts
    ]


def _verstoesse(dateien: list[Path], verboten: set[str]) -> list[str]:
    # Nennt je Datei jeden Import, der in eine der verbotenen Apps führt.

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
    verboten: set[str] = _projekt_apps() - _KANTEN[app] - {app}

    assert _verstoesse(quellen, verboten) == []


def test_sitzungen_kennt_auch_in_tests_weder_training_noch_erhebungen() -> None:
    """Eine Sitzung ist die atomare Auswertungseinheit; ihre Aufrufer bleiben fremd.

    Anders als bei den übrigen Apps gilt das auch für die Tests: Ein Test, der
    einen Aufrufer braucht, prüft ihn und gehört zu ihm.
    """

    quellen: list[Path] = _quellen("sitzungen", mit_tests=True)

    assert _verstoesse(quellen, {"training", "erhebungen"}) == []

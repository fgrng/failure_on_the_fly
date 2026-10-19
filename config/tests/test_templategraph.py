"""Kontrakttest zur Kantenrichtung in den Templates (ADR-0068, ADR-0055).

Die Templates werden als Text gelesen. Eine Kante ist jedes `{% include %}`
und `{% extends %}` auf ein Template einer anderen App und jedes `{% load %}`
einer Tag-Bibliothek einer anderen App; erlaubt ist sie nur laut derselben
Kantentabelle, die den Importgraphen bewacht. Links per `{% url %}` zählen
nicht: Navigation ist frei. Template-Namen aus Variablen sieht der Test nicht.
"""

import re
from functools import cache
from pathlib import Path

import pytest

from config.tests.test_importgraph import _KANTEN, _PROJEKTWURZEL, _projekt_apps

_KOMMENTAR: re.Pattern[str] = re.compile(
    r"\{#.*?#\}|\{%\s*comment\b.*?%\}.*?\{%\s*endcomment\s*%\}", re.DOTALL
)
_EINBINDUNG: re.Pattern[str] = re.compile(
    r"""\{%\s*(include|extends)\s+["']([^"']+)["']"""
)
_LADEN: re.Pattern[str] = re.compile(r"\{%\s*load\s+(.+?)\s*%\}")


@cache
def _bibliotheken() -> dict[str, str]:
    # Jede Tag-Bibliothek gehört der App, in deren `templatetags` sie liegt.

    return {
        datei.stem: app
        for app in _projekt_apps()
        for datei in (_PROJEKTWURZEL / app / "templatetags").glob("*.py")
        if datei.stem != "__init__"
    }


def _geladene_bibliotheken(ausdruck: str) -> list[str]:
    # `{% load a b %}` lädt a und b, `{% load x y from c %}` nur c.

    teile: list[str] = ausdruck.split()
    if "from" in teile:
        return [teile[-1]]
    return teile


def _ziele(datei: Path) -> list[tuple[str, str, str | None]]:
    # Nennt je Einbindung und geladener Bibliothek Art, Ziel und Ziel-App;
    # globale Templates und Django-eigene Bibliotheken haben keine Ziel-App.

    apps: set[str] = _projekt_apps()
    bibliotheken: dict[str, str] = _bibliotheken()
    # Auskommentierte Tags rendern nicht und sind keine Kante.
    text: str = _KOMMENTAR.sub("", datei.read_text(encoding="utf-8"))
    ziele: list[tuple[str, str, str | None]] = []
    for art, name in _EINBINDUNG.findall(text):
        erster_teil: str = name.split("/")[0]
        ziele.append((art, name, erster_teil if erster_teil in apps else None))
    for ausdruck in _LADEN.findall(text):
        for bibliothek in _geladene_bibliotheken(ausdruck):
            ziele.append(("load", bibliothek, bibliotheken.get(bibliothek)))
    return ziele


def _templates(wurzel: Path) -> list[Path]:
    # Sammelt jede Datei unter einem Template-Verzeichnis; fehlt es, keine.

    return sorted(datei for datei in wurzel.rglob("*") if datei.is_file())


def _verstoesse(app: str | None, dateien: list[Path]) -> list[str]:
    # Nennt je Template jede Kante, die die Tabelle der App nicht erlaubt; die
    # globalen Templates (`app` ist None) dürfen auf keine App zeigen.

    erlaubt: frozenset[str] = _KANTEN[app] if app else frozenset()
    quelle: str = app or "global"
    gefunden: list[str] = []
    for datei in dateien:
        for art, ziel, ziel_app in _ziele(datei):
            if ziel_app is None or ziel_app == app or ziel_app in erlaubt:
                continue
            gefunden.append(
                f"{datei.relative_to(_PROJEKTWURZEL)}: {art} {ziel} "
                f"({quelle} → {ziel_app})"
            )
    return gefunden


@pytest.mark.parametrize("app", sorted(_KANTEN))
def test_templates_liegen_unter_dem_namen_ihrer_app(app: str) -> None:
    """Ein Template gehört der App, die der erste Teil seines Namens nennt."""

    wurzel: Path = _PROJEKTWURZEL / app / "templates"
    fremd: list[str] = [
        str(datei.relative_to(_PROJEKTWURZEL))
        for datei in _templates(wurzel)
        if datei.relative_to(wurzel).parts[0] != app
    ]

    assert fremd == []


@pytest.mark.parametrize("app", sorted(_KANTEN))
def test_templates_zeigen_nur_entlang_der_kantentabelle(app: str) -> None:
    """Includes, extends und Tag-Bibliotheken folgen der Richtung aus ADR-0055."""

    dateien: list[Path] = _templates(_PROJEKTWURZEL / app / "templates")

    assert _verstoesse(app, dateien) == []


def test_globale_templates_zeigen_auf_keine_app() -> None:
    """Die globalen Templates liegen unter allen Apps (ADR-0068)."""

    dateien: list[Path] = _templates(_PROJEKTWURZEL / "templates")

    assert _verstoesse(None, dateien) == []


def test_waechter_sieht_einbindungen_aber_keine_kommentare(tmp_path: Path) -> None:
    """Eine auskommentierte Einbindung ist keine Kante, eine aktive schon."""

    datei: Path = tmp_path / "seite.html"
    datei.write_text(
        '{% include "erhebungen/a.html" %}\n'
        '{# {% include "vignetten/b.html" %} #}\n'
        "{% comment %}\n"
        '  {% extends "training/c.html" %}{% load texte %}\n'
        "{% endcomment %}\n"
        "{% load static texte %}\n",
        encoding="utf-8",
    )

    assert _ziele(datei) == [
        ("include", "erhebungen/a.html", "erhebungen"),
        ("load", "static", None),
        ("load", "texte", "texte"),
    ]

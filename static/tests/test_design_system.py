"""Regression checks for the public design-system CSS contract."""

import re
from pathlib import Path


STATIC: Path = Path(__file__).parents[1]


def _stylesheets() -> list[Path]:
    """Alle ausgelieferten CSS-Dateien; neue Dateien prüfen die Lint-Regeln mit."""

    return list((STATIC / "css").glob("*.css"))


def test_benutzte_custom_properties_sind_deklariert() -> None:
    """Jede mit `var(--x)` gelesene Custom Property ist irgendwo als `--x:` deklariert.

    Eine Deklaration mit einer unbekannten Property verwirft der Browser
    stillschweigend (#374).
    """

    stylesheets: list[Path] = _stylesheets()
    # Nur am Anfang einer Deklaration, sonst zählt `.button--danger:hover` mit.
    deklaration: re.Pattern[str] = re.compile(r"(?:^|[;{])\s*(--[\w-]+)\s*:", re.M)
    deklariert: set[str] = {
        name for path in stylesheets for name in deklaration.findall(path.read_text())
    }

    unbekannt: list[str] = [
        f"{path.name}: {name}"
        for path in stylesheets
        for name in re.findall(r"var\(\s*(--[\w-]+)", path.read_text())
        if name not in deklariert
    ]

    assert unbekannt == []


def test_feature_styles_only_consume_semantic_color_tokens() -> None:
    """Feature-CSS greift nicht direkt auf PHSG-Farbprimitive zu."""

    for path in _stylesheets():
        if path.name != "tokens.css":
            assert "var(--phsg-" not in path.read_text(), path


def test_page_sections_follow_the_main_area_not_the_viewport() -> None:
    """Kein `@media`-Block nennt Seitenabschnitte; sie brechen am Hauptbereich um."""

    media_block: re.Pattern[str] = re.compile(
        r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}"
    )

    verstoesse: list[str] = [
        path.name
        for path in _stylesheets()
        for block in media_block.findall(path.read_text())
        if ".page-section" in block or ".field-grid" in block
    ]

    assert verstoesse == []


def test_feature_styles_use_spacing_tokens() -> None:
    """Layout-Abstände verwenden das öffentliche 8-px-Abstandsraster."""

    spacing_with_pixels: re.Pattern[str] = re.compile(
        r"(?:^|[;{])\s*"
        r"(?:gap|row-gap|column-gap|"
        r"margin(?:-(?:top|right|bottom|left|inline|block)(?:-(?:start|end))?)?|"
        r"padding(?:-(?:top|right|bottom|left|inline|block)(?:-(?:start|end))?)?|"
        r"inset(?:-(?:top|right|bottom|left|inline|block)(?:-(?:start|end))?)?|"
        r"top|right|bottom|left)"
        r"\s*:[^;{}]*\d+(?:\.\d+)?px"
    )

    violations: list[str] = []
    for path in _stylesheets():
        for match in spacing_with_pixels.finditer(path.read_text()):
            violations.append(f"{path.name}: {match.group().strip(' ;{')}")

    assert violations == []


def test_markdown_text_steps_its_headings_below_the_section_head() -> None:
    """h3–h5 der Markdown-Texte sind gestuft und auf Seitenfeldern (Text 1rem)
    kleiner als der Abschnittskopf."""

    page_css: str = (STATIC / "css" / "page.css").read_text()
    markdown_css: str = (STATIC / "css" / "markdown-text.css").read_text()
    abschnittskopf: float = float(
        re.search(r"\.page-section__head h2 \{[^}]*font-size: ([\d.]+)rem", page_css)[1]
    )

    groessen: list[float] = [
        float(
            re.search(
                rf"\.markdown-text\.markdown-text {ebene} \{{[^}}]*font-size: ([\d.]+)em",
                markdown_css,
            )[1]
        )
        for ebene in ("h3", "h4", "h5")
    ]

    assert groessen == sorted(groessen, reverse=True)
    assert len(set(groessen)) == 3
    assert max(groessen) < abschnittskopf


def test_szenentext_headings_stand_above_the_scene_text() -> None:
    """In der Sitzung sind h3–h5 gestuft und nie kleiner als der Fließtext."""

    sitzung_css: str = (STATIC / "css" / "sitzung.css").read_text()
    groessen: list[float] = [
        float(
            re.search(
                rf"\.markdown-text\.markdown-text {ebene} \{{ font-size: ([\d.]+)em",
                sitzung_css,
            )[1]
        )
        for ebene in ("h3", "h4", "h5")
    ]

    assert groessen == sorted(groessen, reverse=True)
    assert len(set(groessen)) == 3
    assert min(groessen) >= 1

"""Regression checks for the public design-system CSS contract."""

import re
from pathlib import Path

import pytest


STATIC: Path = Path(__file__).parents[1]
TOKENS: tuple[tuple[str, str], ...] = (
    ("--color-area-participant-solid", "--phsg-mint-dark"),
    ("--color-area-participant-on-solid", "--phsg-white"),
    ("--color-area-participant-tint", "--phsg-green-light"),
    ("--color-area-authoring-solid", "--phsg-yellow-dark"),
    ("--color-area-authoring-on-solid", "--phsg-white"),
    ("--color-area-authoring-tint", "--phsg-yellow-light"),
    ("--color-area-research-solid", "--phsg-purple-dark"),
    ("--color-area-research-on-solid", "--phsg-white"),
    ("--color-area-research-tint", "--phsg-purple-light"),
    ("--color-area-system-solid", "--phsg-blue-dark"),
    ("--color-area-system-on-solid", "--phsg-white"),
    ("--color-area-system-tint", "--phsg-blue-light"),
    ("--color-danger", "--phsg-red-dark"),
    ("--color-danger-tint", "--phsg-red-light"),
    ("--color-danger-emphasis", "--phsg-red-deep"),
    ("--color-success", "--phsg-green-dark"),
    ("--color-info", "--phsg-blue-dark"),
)
COMPONENT_SELECTORS: tuple[str, ...] = (
    ".area-band",
    ".area--participant",
    ".area--authoring",
    ".area--research",
    ".area--system",
    ".card",
    ".card-grid",
    ".card--disabled",
    ".badge",
    ".badge--draft",
    ".badge--final",
    ".badge--system",
    ".badge--archived",
    ".form label",
    ".button--danger",
    ".messages",
    ".message--",
)


@pytest.fixture(scope="module")
def tokens_css() -> str:
    """Liest die öffentlich ausgelieferten semantischen Farb-Tokens."""

    return (STATIC / "css" / "tokens.css").read_text()


@pytest.fixture(scope="module")
def main_css() -> str:
    """Liest die öffentlich ausgelieferten Komponenten-Stile."""

    return (STATIC / "css" / "main.css").read_text()


@pytest.mark.parametrize(("token", "primitive"), TOKENS)
def test_design_system_exposes_semantic_tokens(
    tokens_css: str, token: str, primitive: str
) -> None:
    """Jeder semantische Farb-Token verweist auf die vorgesehene PHSG-Farbe."""

    assert f"{token}: var({primitive});" in tokens_css


@pytest.mark.parametrize("selector", COMPONENT_SELECTORS)
def test_design_system_exposes_shared_component(selector: str, main_css: str) -> None:
    """Jede gemeinsame Komponente stellt ihren dokumentierten Selektor bereit."""

    assert selector in main_css


def test_card_body_stays_on_the_neutral_surface(main_css: str) -> None:
    """Bereichsfarben bleiben im Rahmen und Kopf statt im Karteninhalt."""

    assert "background: var(--color-surface);" in main_css
    assert "background: var(--area-tint" not in main_css


def test_form_controls_are_styled_without_a_form_wrapper(main_css: str) -> None:
    """Die generischen Formularstile benötigen keine zusätzliche Hülle."""

    assert "input,\ntextarea,\nselect {" in main_css


def test_feature_styles_only_consume_semantic_color_tokens() -> None:
    """Feature-CSS greift nicht direkt auf PHSG-Farbprimitive zu."""

    for path in (STATIC / "css").glob("*.css"):
        if path.name != "tokens.css":
            assert "var(--phsg-" not in path.read_text(), path


def test_main_layout_exposes_eight_column_grid() -> None:
    """Standardseiten nutzen acht Spalten, Sitzungen die mittleren vier."""

    navigation_css: str = (STATIC / "css" / "navigation.css").read_text()
    sitzung_css: str = (STATIC / "css" / "sitzung.css").read_text()
    tokens_css: str = (STATIC / "css" / "tokens.css").read_text()

    assert "grid-template-columns: repeat(8, minmax(0, 1fr));" in navigation_css
    assert "column-gap: var(--space-3);" in navigation_css
    assert ":where(.site-main) > * { grid-column: 1 / -1; }" in navigation_css
    assert "max-width: var(--content-max-width);" in navigation_css
    assert "grid-template-columns: minmax(0, 1fr);" in navigation_css
    assert "grid-column: 3 / span 4;" in sitzung_css
    assert ".sitzung-seite { grid-column: 1 / -1; }" in sitzung_css
    assert "--content-max-width: 1440px;" in tokens_css


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
    for path in (STATIC / "css").glob("*.css"):
        for match in spacing_with_pixels.finditer(path.read_text()):
            violations.append(f"{path.name}: {match.group().strip(' ;{')}")

    assert violations == []

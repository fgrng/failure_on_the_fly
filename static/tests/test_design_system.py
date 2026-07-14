"""Regression checks for the public design-system CSS contract."""

from pathlib import Path

import pytest


STATIC: Path = Path(__file__).parents[1]
TOKENS: tuple[tuple[str, str], ...] = (
    ("--color-area-participant-solid", "--phsg-mint-dark"),
    ("--color-area-participant-on-solid", "--phsg-white"),
    ("--color-area-participant-tint", "--phsg-green-light"),
    ("--color-area-authoring-solid", "--phsg-yellow-light"),
    ("--color-area-authoring-on-solid", "--phsg-yellow-deep"),
    ("--color-area-authoring-tint", "--phsg-yellow-light"),
    ("--color-area-research-solid", "--phsg-purple-dark"),
    ("--color-area-research-on-solid", "--phsg-white"),
    ("--color-area-research-tint", "--phsg-purple-light"),
    ("--color-area-system-solid", "--phsg-blue-dark"),
    ("--color-area-system-on-solid", "--phsg-white"),
    ("--color-area-system-tint", "--phsg-blue-light"),
    ("--color-danger", "--phsg-red-dark"),
    ("--color-danger-tint", "--phsg-red-light"),
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


def test_cards_default_to_the_surface_tint(main_css: str) -> None:
    """Karten ohne Bereichsfarbe verwenden die neutrale Oberfläche."""

    assert "background: var(--area-tint, var(--color-surface));" in main_css

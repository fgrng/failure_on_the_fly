from pathlib import Path


STATIC = Path(__file__).parents[1]


def test_design_system_exposes_area_colours_and_shared_components():
    tokens = (STATIC / "css" / "tokens.css").read_text()
    main = (STATIC / "css" / "main.css").read_text()

    assert "--color-area-participant-solid: var(--phsg-mint-dark);" in tokens
    assert "--color-area-participant-on-solid: var(--phsg-white);" in tokens
    assert "--color-area-participant-tint: var(--phsg-green-light);" in tokens
    assert "--color-area-authoring-solid: var(--phsg-yellow-light);" in tokens
    assert "--color-area-authoring-on-solid: var(--phsg-yellow-deep);" in tokens
    assert "--color-area-authoring-tint: var(--phsg-yellow-light);" in tokens
    assert "--color-area-research-solid: var(--phsg-purple-dark);" in tokens
    assert "--color-area-research-on-solid: var(--phsg-white);" in tokens
    assert "--color-area-research-tint: var(--phsg-purple-light);" in tokens
    assert "--color-area-system-solid: var(--phsg-blue-dark);" in tokens
    assert "--color-area-system-on-solid: var(--phsg-white);" in tokens
    assert "--color-area-system-tint: var(--phsg-blue-light);" in tokens
    assert "--color-danger: var(--phsg-red-dark);" in tokens
    assert "--color-danger-tint: var(--phsg-red-light);" in tokens

    for selector in (
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
    ):
        assert selector in main

    assert "background: var(--area-tint, var(--color-surface));" in main

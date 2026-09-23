"""Rendert die Markdown-Quelle eines Textfelds zu sicherem HTML.

Zwei Profile: Der **Informationstext** (Instruktions-, Einwilligungs- und
Abschlusstext einer Erhebung) erlaubt Links nach außen, der **Szenentext**
(Lernauftrag, Arbeitsheft, Rahmenhandlung) nicht. Beide kennen Absätze mit
erhaltenen Zeilenumbrüchen, Fett, Kursiv, `#`–`###` als `h3`–`h5`, Listen und
Zitatblock. Alles andere erscheint wörtlich. Sicher wird das HTML dadurch, dass
der Parser rohes HTML nie durchreicht; einen nachgelagerten Sanitizer gibt es
nicht (siehe ADR „Markdown mit zwei Profilen, Quelle bleibt roh").
"""

from collections.abc import Sequence

from django.utils.safestring import SafeString, mark_safe
from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.rules_core import StateCore
from markdown_it.rules_inline import StateInline
from markdown_it.rules_inline.image import image
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

_ABGESCHALTET: tuple[str, ...] = (
    "code",
    "fence",
    "hr",
    "lheading",
    "html_block",
    "html_inline",
    "backticks",
    "autolink",
    "entity",
    "image",
)
_OBERSTE_EBENE: int = 3
_TIEFSTE_QUELLEBENE: int = 3
_LINK_SCHEMATA: tuple[str, ...] = ("https:", "http:", "mailto:")


def _ueberschriften_einordnen(state: StateCore) -> None:
    # `#`–`###` rücken unter Seitenkopf (h1) und Abschnittskopf (h2); tiefere
    # Ebenen gehören nicht zum Umfang und werden zum Absatz mit ihren Rauten.

    for position, token in enumerate(state.tokens):
        if token.type not in ("heading_open", "heading_close"):
            continue
        ebene: int = int(token.tag[1])
        if ebene <= _TIEFSTE_QUELLEBENE:
            token.tag = f"h{ebene + _OBERSTE_EBENE - 1}"
            continue
        token.type = token.type.replace("heading", "paragraph")
        token.tag = "p"
        if token.nesting == 1:
            inhalt: Token = state.tokens[position + 1]
            inhalt.content = f"{token.markup} {inhalt.content}".rstrip()


def _bild_woertlich(state: StateInline, silent: bool) -> bool:
    # Erkennt Bildsyntax, um sie als Text auszugeben. Ohne diese Regel machte
    # der Linkparser aus `![Tafel](https://…)` ein `!` vor einem Link.

    anfang: int = state.pos
    if not image(state, True):
        return False
    if not silent:
        state.push("text", "", 0).content = state.src[anfang : state.pos]
    return True


def _link_erlaubt(ziel: str) -> bool:
    # Andere Schemata und relative Pfade lässt der Parser als Text stehen.

    return ziel.strip().lower().startswith(_LINK_SCHEMATA)


def _externer_link_auf(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    index: int,
    options: OptionsDict,
    env: EnvType,
) -> str:
    # Öffnet im neuen Tab, damit etwa getroffene Einwilligungen nicht verloren
    # gehen, und ohne der Zielseite Zugriff auf die Plattform zu geben.

    tokens[index].attrSet("target", "_blank")
    tokens[index].attrSet("rel", "noopener noreferrer")
    return renderer.renderToken(tokens, index, options, env)


def _externer_link_zu(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    index: int,
    options: OptionsDict,
    env: EnvType,
) -> str:
    # Den sichtbaren Pfeil setzt das Stylesheet; Screenreader lesen diesen Text.

    return (
        '<span class="markdown-text__extern"> (öffnet in neuem Tab)</span>'
        + renderer.renderToken(tokens, index, options, env)
    )


def _parser(mit_links: bool) -> MarkdownIt:
    # Baut einen Parser je Profil; beide teilen denselben Grundumfang.

    md: MarkdownIt = MarkdownIt(
        "commonmark",
        {"html": False, "breaks": True, "linkify": False, "xhtmlOut": False},
    )
    md.disable(list(_ABGESCHALTET))
    md.core.ruler.after("block", "ueberschriften", _ueberschriften_einordnen)
    md.inline.ruler.before("link", "bild_woertlich", _bild_woertlich)
    if mit_links:
        md.validateLink = _link_erlaubt  # type: ignore[method-assign]
        md.add_render_rule("link_open", _externer_link_auf)
        md.add_render_rule("link_close", _externer_link_zu)
    else:
        md.disable(["link", "reference"])
    return md


_INFORMATIONSTEXT: MarkdownIt = _parser(mit_links=True)
_SZENENTEXT: MarkdownIt = _parser(mit_links=False)


def informationstext(quelle: str) -> SafeString:
    """Rendert Instruktions-, Einwilligungs- und Abschlusstext, mit Links."""

    return mark_safe(_INFORMATIONSTEXT.render(quelle) if quelle else "")


def szenentext(quelle: str) -> SafeString:
    """Rendert Lernauftrag, Arbeitsheft und Rahmenhandlung, ohne Links."""

    return mark_safe(_SZENENTEXT.render(quelle) if quelle else "")

"""Template-Filter der beiden Markdown-Profile (`{% load texte %}`)."""

from django import template
from django.utils.safestring import SafeString

from texte import markdown

register: template.Library = template.Library()
register.filter("informationstext", markdown.informationstext)
register.filter("szenentext", markdown.szenentext)


@register.simple_tag
def markdown_hinweis(profil: str) -> SafeString:
    """Liefert den Markdown-Hinweis, der unter einem Editorfeld des Profils steht."""

    return markdown.PROFILE[profil].hinweis


@register.filter("markdown")
def im_profil(quelle: str, profil: str) -> SafeString:
    """Rendert eine Quelle im genannten Profil, etwa `wert|markdown:profil`."""

    return markdown.PROFILE[profil].rendern(quelle)

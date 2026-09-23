"""Template-Filter der beiden Markdown-Profile (`{% load texte %}`)."""

from django import template

from texte import markdown

register: template.Library = template.Library()
register.filter("informationstext", markdown.informationstext)
register.filter("szenentext", markdown.szenentext)

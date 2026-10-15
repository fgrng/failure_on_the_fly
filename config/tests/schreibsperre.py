"""Gemeinsamer Testadapter: Rendern ohne gehaltene Schreibsperre (ADR-0059)."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.db import connection
from django.template import Template
from django.test.signals import template_rendered


@contextmanager
def rendern_ohne_schreibsperre() -> Iterator[list[str]]:
    """Sammelt die im Block gerenderten Templates.

    Vor jedem Template holt eine zweite Verbindung die Schreibsperre ohne
    Wartezeit; hält die Anfrage sie noch, scheitert das Rendern.
    """

    gerendert: list[str] = []

    def rendern_beobachten(sender: object, template: Template, **kwargs: Any) -> None:
        with sqlite3.connect(
            str(connection.settings_dict["NAME"]), uri=True, timeout=0
        ) as zweite:
            zweite.execute("BEGIN IMMEDIATE")
            zweite.rollback()
        gerendert.append(str(template.name))

    template_rendered.connect(rendern_beobachten)
    try:
        yield gerendert
    finally:
        template_rendered.disconnect(rendern_beobachten)

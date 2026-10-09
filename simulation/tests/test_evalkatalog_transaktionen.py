"""Transaktionsgrenzen des Editors über HTTP und die Datenbank prüfen."""

import sqlite3
from typing import Any

import pytest
from django.db import connection
from django.template import Template
from django.test import Client
from django.test.signals import template_rendered
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen
from simulation.models import Eval, Evalinput, Evalkatalog
from simulation.tests.evalkatalog_bau import vollstaendiger_katalog


def _knoten(katalog: Evalkatalog, knoten: str) -> str:
    # Löst die drei speichernden Knoten derselben Fassung auf.
    args = [katalog.pk]
    if knoten != "kriterien":
        eval_ = Eval.objects.get(katalog=katalog)
        args.append(eval_.pk)
        if knoten == "evalinput":
            args.append(Evalinput.objects.get(eval=eval_).pk)
    return reverse(f"simulation:evalkatalog_{knoten}", args=args)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("knoten", ["kriterien", "eval", "evalinput"])
@pytest.mark.parametrize("zustand", ["entwurf", "final", "ueberholt"])
def test_get_haelt_beim_rendern_keine_schreibsperre(
    client: Client, knoten: str, zustand: str
) -> None:
    katalog = vollstaendiger_katalog()
    if zustand != "entwurf":
        katalog.finalisieren()
    if zustand == "ueberholt":
        katalog.bearbeiten().finalisieren()
    client.force_login(konto_mit_rollen("ada", is_superuser=True))
    gerendert = []

    def rendern_beobachten(sender: object, template: Template, **kwargs: Any) -> None:
        if template.name != "simulation/evalkatalog_editor.html":
            return
        assert not connection.in_atomic_block
        with sqlite3.connect(
            str(connection.settings_dict["NAME"]), uri=True, timeout=0
        ) as zweite:
            zweite.execute("BEGIN IMMEDIATE")
            zweite.rollback()
        gerendert.append(template.name)

    template_rendered.connect(rendern_beobachten)
    try:
        response = client.get(_knoten(katalog, knoten))
    finally:
        template_rendered.disconnect(rendern_beobachten)

    assert response.status_code == 200
    assert gerendert == ["simulation/evalkatalog_editor.html"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("knoten", ["kriterien", "eval", "evalinput"])
@pytest.mark.parametrize("fehler", [False, True])
def test_post_speichert_alle_eingaben_atomisch(
    client: Client, knoten: str, fehler: bool
) -> None:
    katalog = vollstaendiger_katalog()
    kriterium = katalog.kriterium_anlegen("Bisherige Rubrik")
    eval_ = Eval.objects.get(katalog=katalog)
    url = _knoten(katalog, knoten)
    client.force_login(konto_mit_rollen("ada", is_superuser=True))
    schreibtransaktionen = []

    def schreiben_beobachten(
        execute: Any, sql: str, params: Any, many: bool, context: dict[str, Any]
    ) -> Any:
        if sql.startswith("UPDATE"):
            schreibtransaktionen.append(connection.in_atomic_block)
            # Ein Datenbankfehler nach dem ersten Schreiben darf keine
            # teilweise gespeicherten Formulareingaben hinterlassen.
            if fehler and len(schreibtransaktionen) == 2:
                raise RuntimeError("Schreiben fehlgeschlagen")
        return execute(sql, params, many, context)

    with connection.execute_wrapper(schreiben_beobachten):
        daten = {
            f"kriterium-{kriterium.pk}": "Geänderte Rubrik",
            f"eval-{eval_.pk}": "Geändertes Eval",
        }
        if fehler:
            with pytest.raises(RuntimeError, match="Schreiben fehlgeschlagen"):
                client.post(url, daten)
        else:
            response = client.post(url, daten)
            assert response.status_code == 302
            assert response.headers["Location"] == url

    assert schreibtransaktionen and all(schreibtransaktionen)
    response = client.get(_knoten(katalog, "kriterien"))
    inhalt = response.content.decode()
    if fehler:
        assert "Bisherige Rubrik" in inhalt
        assert "Geänderte Rubrik" not in inhalt
        assert "Geändertes Eval" not in inhalt
        assert "Ergänzt" in inhalt
    else:
        assert "Geänderte Rubrik" in inhalt
        assert "Geändertes Eval" in inhalt

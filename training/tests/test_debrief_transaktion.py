"""Der Training-Debrief rendert nicht unter der Schreibsperre (ADR-0059)."""

import sqlite3
from typing import Any

import pytest
from django.db import connection
from django.http import HttpResponse
from django.template import Template
from django.test import Client
from django.test.signals import template_rendered
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE
from simulation.models import Verwendung
from sitzungen.models import Sitzung
from training.models import Training
from training.tests.aufbau import gespielte_sitzung


@pytest.mark.django_db(transaction=True)
def test_gescheiterter_debrief_rendert_ohne_schreibsperre(client: Client) -> None:
    """Die Fehlerseite entsteht erst, wenn die Sperre wieder frei ist."""
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    training: Training = Training.objects.anlegen(ausbilderin, name="Bruchrechnung")
    vignette = finale_vignette(ausbilderin, name="Brüche addieren")
    training.vignette_aufnehmen(vignette)
    training.veroeffentlichen()
    training.beitreten(teilnehmerin)
    sitzung: Sitzung = gespielte_sitzung(
        training, teilnehmerin, vignette, Sitzung.Status.GESCHEITERT
    )
    client.force_login(teilnehmerin)
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
        response: HttpResponse = client.post(
            reverse("training:debrief", args=[sitzung.pk]), {"diagnose": "Bruchfehler"}
        )
    finally:
        template_rendered.disconnect(rendern_beobachten)

    assert response.status_code == 200
    assert "Die Antwort konnte nicht erzeugt werden." in response.content.decode()
    assert gerendert
    sitzung.refresh_from_db()
    assert sitzung.status == Sitzung.Status.GESCHEITERT

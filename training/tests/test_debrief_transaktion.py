"""Der Training-Debrief rendert nicht unter der Schreibsperre (ADR-0059)."""

import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from config.tests.schreibsperre import rendern_ohne_schreibsperre
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

    with rendern_ohne_schreibsperre() as gerendert:
        response: HttpResponse = client.post(
            reverse("training:debrief", args=[sitzung.pk]), {"diagnose": "Bruchfehler"}
        )

    assert "sitzungen/sitzung.html" in gerendert
    assert "Die Antwort konnte nicht erzeugt werden." in response.content.decode()

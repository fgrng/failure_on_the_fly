"""Gespeicherte Fehlerdetails aller Rollen über Ausführung und HTTP-Ansicht."""

import re

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from config.tests.formular import text_ohne_tags
from config.tests.sprachmodell import vor_jedem_aufruf
from evals.tests.aufbau import (
    aeusserungen,
    antworten,
    drei_fakes,
    finaler_katalog,
    gelenkt,
    urteile,
)
from vignetten.models import Vignette


@pytest.fixture
def gestarteter_lauf() -> tuple[Client, Vignette]:
    """Eine angemeldete Autor:in startet ihren Lauf über die Oberfläche."""

    ada = konto_mit_rollen("ada", "Autor:in")
    vignette = finale_vignette(ada)
    client = Client()
    client.force_login(ada)
    client.post(reverse("evals:starten", args=[vignette.pk]))
    return client, vignette


@pytest.fixture
def erfolgreiche_wiederholungen() -> None:
    """Lehrperson und Bewerter liefern nach Formatbruch/Filter gültige Ausgaben."""

    finaler_katalog(k=1, schritte=(gelenkt("Nachfragen"),), uebergreifende=())
    drei_fakes(
        schuelerin=antworten(1),
        lehrperson=[{"fehler": "formatbruch", "rohantwort": "Lehrerfehler"}]
        + aeusserungen(1),
        bewerter=[{"fehler": "content_filter", "rohantwort": "Bewerterfehler"}]
        + urteile(True),
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("erfolgreiche_wiederholungen")
def test_erfolgreiche_wiederholungen_erhalten_fehler_ohne_das_bestehen_zu_aendern(
    gestarteter_lauf: tuple[Client, Vignette],
) -> None:
    client, vignette = gestarteter_lauf
    call_command("evallaeufe_abarbeiten", "--einmal")

    antwort = client.get(reverse("evals:evallauf", args=[vignette.pk]))
    seite = text_ohne_tags(antwort)

    assert "1 von 1 · bestanden" in seite
    assert "Fertig · Bestanden" in seite
    assert "Gelenkte Frage 1" in seite
    assert "Formatbruch" in seite
    assert "Lehrerfehler" in seite
    assert "Content-Filter" in seite
    assert "Bewerterfehler" in seite
    assert antwort.content.decode().count("<summary>Fehlversuche · 1</summary>") == 2
    assert not re.search(
        r"<details\b[^>]*\bopen\b[^>]*>\s*<summary>Fehlversuche",
        antwort.content.decode(),
    )


@pytest.mark.django_db
@pytest.mark.parametrize("position", [1, 2])
def test_endgueltiger_lehrpersonenfehler_bleibt_am_betroffenen_schritt_sichtbar(
    position: int,
) -> None:
    schritte = ["Vorherige Frage"] * (position - 1) + [gelenkt("Nachfragen")]
    finaler_katalog(k=1, schritte=schritte)
    drei_fakes(
        schuelerin=antworten(position - 1),
        lehrperson=[{"fehler": "anbieterfehler", "rohantwort": "Anbieter offline"}] * 3,
    )
    ada = konto_mit_rollen("ada", "Autor:in")
    vignette = finale_vignette(ada)
    client = Client()
    client.force_login(ada)
    client.post(reverse("evals:starten", args=[vignette.pk]))
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite = text_ohne_tags(client.get(reverse("evals:evallauf", args=[vignette.pk])))

    assert f"Lehrperson konnte Schritt {position} nicht formulieren." in seite
    assert "Fehlversuche · 3" in seite
    assert seite.count("Anbieterfehler") == 3
    assert seite.count("Anbieter offline") == 3
    assert "1 ohne Urteil" in seite
    assert "Antwortversuch endgültig gescheitert" not in seite
    assert ("Antwort 1" in seite) == (position == 2)


@pytest.mark.django_db
def test_ungueltige_bewerterausgabe_bleibt_escaped_neben_dem_fehlenden_urteil() -> None:
    finaler_katalog(k=1, schritte=("Frage",), uebergreifende=())
    drei_fakes(
        schuelerin=antworten(1),
        bewerter=[{"erfuellt": "ja", "rohantwort": "<script>unerlaubt</script>"}] * 3,
    )
    ada = konto_mit_rollen("ada", "Autor:in")
    vignette = finale_vignette(ada)
    client = Client()
    client.force_login(ada)
    client.post(reverse("evals:starten", args=[vignette.pk]))
    call_command("evallaeufe_abarbeiten", "--einmal")

    html = client.get(reverse("evals:evallauf", args=[vignette.pk])).content.decode()

    assert "&lt;script&gt;unerlaubt&lt;/script&gt;" in html
    assert "<script>unerlaubt</script>" not in html
    assert html.count("Formatbruch") == 3
    assert "1 ohne Urteil" in html


@pytest.mark.django_db
@pytest.mark.usefixtures("erfolgreiche_wiederholungen")
def test_abbruch_nach_lehrpersonenversuch_erhaelt_details_ohne_falsche_fehlerrolle(
    gestarteter_lauf: tuple[Client, Vignette],
) -> None:
    client, vignette = gestarteter_lauf

    def abbrechen(nachrichten: list[dict[str, str]]) -> None:
        # Ein externer Aufruf endet unerwartet, nachdem die Lehrperson antwortete.
        if nachrichten[-1]["content"] == "Gelenkte Frage 1":
            raise RuntimeError("Unterbrechung vor Schüler:innen-Antwort")

    with vor_jedem_aufruf(abbrechen):
        call_command("evallaeufe_abarbeiten", "--einmal")

    seite = text_ohne_tags(client.get(reverse("evals:evallauf", args=[vignette.pk])))

    assert "Abgebrochen" in seite
    assert "Formatbruch" in seite
    assert "Lehrerfehler" in seite
    assert "Für Schritt 1 liegt noch kein vollständiger Wechsel vor." in seite
    assert "Lehrperson konnte Schritt" not in seite
    assert "Antwortversuch endgültig gescheitert" not in seite

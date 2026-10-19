"""Tests für das nächtliche Aufräumen abgelaufener Einträge und Sessions."""

from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.management import call_command
from time_machine import TimeMachineFixture

from sitzungen import kurzlebiger_speicher

pytestmark = pytest.mark.django_db

_BEGINN: datetime = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


def test_loescht_abgelaufene_eintraege_und_laesst_frische_stehen(
    time_machine: TimeMachineFixture,
) -> None:
    """Teilnahme und Probelauf verschwinden nach Ablauf, frische Einträge bleiben."""

    time_machine.move_to(_BEGINN, tick=False)
    kurzlebiger_speicher.schreiben("sitzung-1", {"schritte": 1})
    kurzlebiger_speicher.schreiben("probelauf-3-alt", {"schritte": 1})

    time_machine.move_to(_BEGINN + timedelta(hours=20), tick=False)
    kurzlebiger_speicher.schreiben("sitzung-2", {"schritte": 1})
    kurzlebiger_speicher.schreiben("probelauf-3-neu", {"schritte": 1})

    time_machine.move_to(_BEGINN + timedelta(hours=30), tick=False)
    call_command("aufraeumen")

    # Zurück zu einem Zeitpunkt, an dem alle vier noch gültig wären: Was jetzt
    # fehlt, hat der Befehl gelöscht.
    time_machine.move_to(_BEGINN + timedelta(hours=21), tick=False)
    assert kurzlebiger_speicher.lesen("sitzung-1") is None
    assert kurzlebiger_speicher.lesen("probelauf-3-alt") is None
    assert kurzlebiger_speicher.lesen("sitzung-2") == {"schritte": 1}
    assert kurzlebiger_speicher.lesen("probelauf-3-neu") == {"schritte": 1}


def test_entfernt_abgelaufene_konto_sessions(time_machine: TimeMachineFixture) -> None:
    """Der Befehl führt clearsessions aus: abgelaufene Zeilen gehen, gültige bleiben."""

    time_machine.move_to(_BEGINN, tick=False)
    abgelaufen = SessionStore()
    abgelaufen.set_expiry(timedelta(hours=1))
    abgelaufen.create()
    gueltig = SessionStore()
    gueltig.set_expiry(timedelta(days=7))
    gueltig.create()

    time_machine.move_to(_BEGINN + timedelta(hours=2), tick=False)
    call_command("aufraeumen")

    assert set(Session.objects.values_list("session_key", flat=True)) == {
        gueltig.session_key
    }

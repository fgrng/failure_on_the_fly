"""Migrationstest der Bereinigung von django_session; die Abschlussphase streicht ihn (ADR-0031).

Die Migration ändert nur Daten. Vor und nach ihr ist das Schema gleich, der
Test legt seinen Bestand deshalb über die heutigen Modelle an.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from django.contrib.sessions.backends.db import SessionStore
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen

VORHER: list[tuple[str, str]] = [("sitzungen", "0018_laufende_sitzungen_pinnen")]
NACHHER: list[tuple[str, str]] = [("sitzungen", "0019_altbestand_aus_session")]

ALTBESTAND: dict[str, object] = {
    "erhebung_teilnahme_tokens": {"link": "token"},
    "fluechtige_sitzungen": {"1": {"schritte": ["Denkspur"]}},
    "probelauf": {"vignette": 1, "schritte": ["Denkspur"]},
}


def _sitzung(schluessel: str) -> dict[str, object]:
    # Liest den Inhalt der Session mit diesem Schlüssel aus django_session.
    return dict(SessionStore(session_key=schluessel).load())


@contextmanager
def _ab(stand: list[tuple[str, str]]) -> Iterator[None]:
    # Migriert auf den Stand und danach wieder auf den neuesten Stand vor.
    ziel: list[tuple[str, str]] = MigrationExecutor(
        connection
    ).loader.graph.leaf_nodes()
    MigrationExecutor(connection).migrate(stand)
    try:
        yield
    finally:
        MigrationExecutor(connection).migrate(ziel)


@pytest.mark.django_db(transaction=True)
def test_migration_entfernt_nur_den_altbestand(client: Client) -> None:
    """Nur die drei Schlüssel fallen weg; fremde Schlüssel und die Anmeldung bleiben."""

    with _ab(VORHER):
        client.force_login(konto_mit_rollen("ada"))
        angemeldet = client.session
        angemeldet.update({**ALTBESTAND, "fremd": "bleibt"})
        angemeldet.save()
        anonym = SessionStore()
        anonym.update(ALTBESTAND)
        anonym.save()
        ohne_altbestand = SessionStore()
        ohne_altbestand["fremd"] = 1
        ohne_altbestand.save()
        vorher: dict[str, object] = _sitzung(angemeldet.session_key)

        MigrationExecutor(connection).migrate(NACHHER)

    erwartet: dict[str, object] = {
        k: v for k, v in vorher.items() if k not in ALTBESTAND
    }
    assert "_auth_user_id" in erwartet
    assert _sitzung(angemeldet.session_key) == erwartet
    assert _sitzung(anonym.session_key) == {}
    assert _sitzung(ohne_altbestand.session_key) == {"fremd": 1}
    antwort = client.get(reverse("start"))
    assert antwort.wsgi_request.user.username == "ada"


@pytest.mark.django_db(transaction=True)
def test_migration_rueckwaerts_ist_ein_noop() -> None:
    """Rückwärts migriert, bleibt eine Session unverändert."""

    with _ab(NACHHER):
        sitzung = SessionStore()
        sitzung.update({**ALTBESTAND, "fremd": "bleibt"})
        sitzung.save()
        MigrationExecutor(connection).migrate(VORHER)
        assert _sitzung(sitzung.session_key) == {**ALTBESTAND, "fremd": "bleibt"}

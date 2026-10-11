"""Auslösen prüft den Eingabestand und serialisiert gleichzeitige Starts."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from django.core.exceptions import ValidationError
from django.db import connection, connections

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from evals.models import Evallauf
from evals.tests.aufbau import drei_fakes, finaler_katalog


@pytest.mark.django_db
def test_ohne_gepinnten_kern_laesst_sich_keine_fassung_pruefen() -> None:
    """Ein Entwurf ohne finalen Kern erhält die fachliche Fehlermeldung."""

    finaler_katalog()
    drei_fakes()
    vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in")).bearbeiten()
    vignette.gepinnter_kern = None
    vignette.save()

    with pytest.raises(ValidationError, match="fehlt ein gepinnter Simulationskern"):
        Evallauf.objects.ausloesen(vignette)


@pytest.mark.django_db(transaction=True)
def test_gleichzeitige_starts_stellen_nur_einen_lauf_ein(tmp_path: Path) -> None:
    """Der zweite Start sieht den wartenden Lauf und erhält die fachliche Meldung."""

    finaler_katalog()
    drei_fakes()
    vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))
    # SQLite wartet nur bei einer Datei auf die Schreibsperre; die geteilte
    # In-Memory-Testdatenbank meldet stattdessen sofort SQLITE_LOCKED.
    datenbank = tmp_path / "gleichzeitige-starts.sqlite3"
    with sqlite3.connect(datenbank) as ziel:
        connection.connection.backup(ziel)
    start = Barrier(2)

    def ausloesen() -> str:
        # Jeder Thread hat seine eigene Datenbankverbindung, wie zwei Requests.
        try:
            connections["default"].settings_dict = {
                **connection.settings_dict,
                "NAME": str(datenbank),
            }
            start.wait(timeout=10)
            Evallauf.objects.ausloesen(vignette)
            return "eingestellt"
        except ValidationError as error:
            return error.messages[0]
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as threads:
        ergebnisse = list(threads.map(lambda _: ausloesen(), range(2)))

    assert sorted(ergebnisse) == [
        "Für diese Fassung wartet oder läuft bereits ein Evallauf.",
        "eingestellt",
    ]

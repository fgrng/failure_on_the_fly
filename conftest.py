"""Testweite Einstellungen, die die Produktivkonfiguration nicht berühren."""

from pathlib import Path

import pytest
from django.conf import settings


@pytest.hookimpl(tryfirst=True)
def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    """Einzelne Dateien und Tests laufen seriell, Verzeichnisse parallel.

    Vier Worker richten je Django und die Testdatenbank ein; das kostet mehr,
    als eine einzelne Datei an Laufzeit hat. `tryfirst`, weil sonst die
    Standardimplementierung von xdist zuerst antwortet.
    """
    ziele: list[str] = [argument.split("::")[0] for argument in config.args]
    if not ziele or any(Path(ziel).is_dir() for ziel in ziele):
        return 4
    return 0


def pytest_configure(config: pytest.Config) -> None:
    """Tests hashen Passwörter schnell statt sicher.

    PBKDF2 bremst vor allem die Workshop-Seed-Tests. Kein Test prüft die
    Stärke des Hashings.
    """
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

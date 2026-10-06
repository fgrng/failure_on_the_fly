"""Testweite Einstellungen, die die Produktivkonfiguration nicht berühren."""

import pytest
from django.conf import settings


def pytest_configure(config: pytest.Config) -> None:
    """Tests hashen Passwörter schnell statt sicher.

    PBKDF2 bremst vor allem die Workshop-Seed-Tests. Kein Test prüft die
    Stärke des Hashings.
    """
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

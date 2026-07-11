"""Integrationstests für das Nutzer-Modell."""

import pytest
from django.contrib.auth import authenticate, get_user_model

from konten.models import Konto


@pytest.mark.django_db
def test_konto_ist_das_aktive_nutzermodell() -> None:
    """Ein Konto meldet sich mit username an und behält Standardfelder."""
    konto: Konto = get_user_model().objects.create_user(
        username="lehrerin",
        password="sicheres-passwort",
        email="lehrerin@example.test",
        first_name="Ada",
        last_name="Lovelace",
    )

    assert (konto._meta.label, konto.username, konto.email, konto.first_name, konto.last_name) == (
        "konten.Konto",
        "lehrerin",
        "lehrerin@example.test",
        "Ada",
        "Lovelace",
    )


@pytest.mark.django_db
def test_konto_meldet_sich_mit_username_und_passwort_an() -> None:
    """Ein Konto nutzt den Django-Standardweg zur Anmeldung."""
    konto: Konto = get_user_model().objects.create_user(
        username="lehrerin",
        password="sicheres-passwort",
    )

    assert authenticate(username="lehrerin", password="sicheres-passwort") == konto

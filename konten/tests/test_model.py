"""Integrationstests für das Nutzer-Modell."""

import pytest
from django.apps import apps
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate

from konten.models import Konto


@pytest.mark.django_db
def test_kontorollen_werden_nach_migration_angelegt() -> None:
    """Die vier Kontorollen existieren als berechtigungsfreie Django-Groups."""
    rollen = Group.objects.order_by("name")

    assert list(rollen.values_list("name", flat=True)) == [
        "Administrator:in",
        "Ausbilder:in",
        "Autor:in",
        "Forschende:r",
    ]
    assert not rollen.filter(permissions__isnull=False).exists()


@pytest.mark.django_db
def test_kontorollen_werden_beim_zweiten_post_migrate_lauf_nicht_dupliziert() -> None:
    """Ein erneuter Migrationslauf lässt die vier Kontorollen unverändert."""
    konten_config = apps.get_app_config("konten")
    Group.objects.get(name="Autor:in").permissions.add(Permission.objects.first())

    post_migrate.send(
        sender=konten_config,
        app_config=konten_config,
        using="default",
    )

    assert Group.objects.count() == 4
    assert not Group.objects.filter(permissions__isnull=False).exists()


@pytest.mark.django_db
def test_konto_kann_mehrere_rollen_tragen() -> None:
    """Ein Konto kann zugleich Autor:in und Forschende:r sein."""
    konto: Konto = get_user_model().objects.create_user(
        username="lehrerin",
        password="sicheres-passwort",
    )
    konto.groups.add(
        Group.objects.get(name="Autor:in"),
        Group.objects.get(name="Forschende:r"),
    )

    assert set(konto.groups.values_list("name", flat=True)) == {
        "Autor:in",
        "Forschende:r",
    }


def test_konto_ist_das_aktive_nutzermodell() -> None:
    """Konto ist das von Django verwendete Nutzer-Modell."""
    assert get_user_model() is Konto


@pytest.mark.django_db
def test_konto_behaelt_django_standardfelder() -> None:
    """Ein Konto behält Djangos Standardfelder für Personendaten."""
    konto: Konto = get_user_model().objects.create_user(
        username="lehrerin",
        password="sicheres-passwort",
        email="lehrerin@example.test",
        first_name="Ada",
        last_name="Lovelace",
    )

    assert (konto.username, konto.email, konto.first_name, konto.last_name) == (
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

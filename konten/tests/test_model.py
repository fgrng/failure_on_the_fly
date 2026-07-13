"""Integrationstests für das Nutzer-Modell."""

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.db.models import QuerySet

from konten.models import Konto
from vignetten.models import Vignettenhistorie


@pytest.mark.django_db
def test_kontorollen_werden_nach_migration_angelegt() -> None:
    """Die vier Kontorollen existieren als berechtigungsfreie Django-Groups."""
    rollen: QuerySet[Group] = Group.objects.order_by("name")

    assert list(rollen.values_list("name", flat=True)) == [
        "Administrator:in",
        "Ausbilder:in",
        "Autor:in",
        "Forschende:r",
    ]
    assert not rollen.filter(permissions__isnull=False).exists()


@pytest.mark.django_db
def test_erneute_migration_dupliziert_kontorollen_nicht() -> None:
    """Ein erneuter Migrationslauf dupliziert die vier Kontorollen nicht."""
    call_command("migrate", verbosity=0)

    assert Group.objects.count() == 4


@pytest.mark.django_db
def test_erneute_migration_entfernt_berechtigungen_der_kontorollen() -> None:
    """Ein erneuter Migrationslauf entfernt vergebene Django-Permissions."""
    berechtigung: Permission = Permission.objects.get(
        codename="add_group",
        content_type__app_label="auth",
        content_type__model="group",
    )
    Group.objects.get(name="Autor:in").permissions.add(berechtigung)

    call_command("migrate", verbosity=0)

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
def test_konto_loeschen_alleinige_eigentuemerin_aktiver_historie_wird_blockiert() -> None:
    """Eine aktive Vignettenhistorie darf nicht eigentümerlos werden."""
    konto: Konto = get_user_model().objects.create_user(username="ada")
    historie: Vignettenhistorie = Vignettenhistorie.objects.create()
    historie.eigentuemerinnen.add(konto)

    with pytest.raises(ProtectedError):
        konto.delete()

    assert Konto.objects.filter(pk=konto.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("archiviert", "mit_koeigentuemerin"), [(True, False), (False, True)]
)
def test_konto_loeschen_archivierte_oder_geteilte_historie_ist_erlaubt(
    archiviert: bool, mit_koeigentuemerin: bool
) -> None:
    """Archivierte oder geteilte Historien blockieren keine Kontolöschung."""
    konto: Konto = get_user_model().objects.create_user(username="ada")
    historie: Vignettenhistorie = Vignettenhistorie.objects.create(archiviert=archiviert)
    historie.eigentuemerinnen.add(konto)
    if mit_koeigentuemerin:
        historie.eigentuemerinnen.add(
            get_user_model().objects.create_user(username="grace")
        )

    konto.delete()

    assert not Konto.objects.filter(pk=konto.pk).exists()


@pytest.mark.django_db
def test_konto_meldet_sich_mit_username_und_passwort_an() -> None:
    """Ein Konto nutzt den Django-Standardweg zur Anmeldung."""
    konto: Konto = get_user_model().objects.create_user(
        username="lehrerin",
        password="sicheres-passwort",
    )

    assert authenticate(username="lehrerin", password="sicheres-passwort") == konto

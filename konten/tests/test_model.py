"""Integrationstests für das Nutzer-Modell."""

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db.models import QuerySet

from config.tests.aufbau import aktive_modell_konfiguration
from erhebungen.models import Erhebung
from konten.models import Konto
from simulation.models import Verwendung
from vignetten.models import Vignettenhistorie


@pytest.mark.django_db
def test_kontorollen_werden_nach_migration_angelegt() -> None:
    """Die drei Fachrollen existieren als berechtigungsfreie Django-Groups."""
    rollen: QuerySet[Group] = Group.objects.order_by("name")

    assert list(rollen.values_list("name", flat=True)) == [
        "Ausbilder:in",
        "Autor:in",
        "Forschende:r",
    ]
    assert not rollen.filter(permissions__isnull=False).exists()


@pytest.mark.django_db
def test_erneute_migration_dupliziert_kontorollen_nicht() -> None:
    """Ein erneuter Migrationslauf dupliziert die drei Kontorollen nicht."""
    call_command("migrate", verbosity=0)

    assert Group.objects.count() == 3


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
def test_rollen_nennen_alle_fachrollen_und_die_administration() -> None:
    """Die Rollenanzeige führt jede Fachrolle und zuletzt die Administration."""
    konto: Konto = Konto.objects.create_user(username="lehrerin", is_superuser=True)
    konto.groups.add(
        Group.objects.get(name="Forschende:r"),
        Group.objects.get(name="Autor:in"),
    )

    assert konto.rollen() == ["Autor:in", "Forschende:r", "Administrator:in"]


@pytest.mark.django_db
def test_rollen_sind_ohne_rolle_leer() -> None:
    """Ein Konto ohne Fachrolle und Administration trägt keine Rolle."""
    konto: Konto = Konto.objects.create_user(username="teilnehmerin")

    assert konto.rollen() == []


@pytest.mark.django_db
def test_superuser_wird_beim_speichern_auch_staff() -> None:
    """Der Django-Admin-Zutritt folgt dem Superuser-Status in beide Richtungen."""
    konto: Konto = Konto.objects.create_user(username="admin", is_superuser=True)
    konto.refresh_from_db()
    assert konto.is_staff

    konto.is_superuser = False
    konto.save()
    konto.refresh_from_db()
    assert not konto.is_staff

    konto.is_superuser = True
    konto.save(update_fields=["is_superuser"])
    konto.refresh_from_db()
    assert konto.is_staff


@pytest.mark.django_db
def test_konto_loeschen_archivierte_historie_ist_erlaubt() -> None:
    """Eine archivierte Vignettenhistorie blockiert keine Kontolöschung."""
    ada: Konto = Konto.objects.create_user(username="ada")
    # Archiviert wird eine Historie heute nur über das Kennzeichen, bis #236
    # eine öffentliche Geste bringt.
    historie: Vignettenhistorie = Vignettenhistorie.objects.create(archiviert=True)
    historie.eigentuemerinnen.add(ada)

    ada.delete()

    assert not Konto.objects.filter(pk=ada.pk).exists()


@pytest.mark.django_db
def test_konto_loeschen_archivierte_erhebung_ueberlebt() -> None:
    """Eine archivierte Erhebung darf ihre letzte Eigentümerin verlieren."""
    ada: Konto = Konto.objects.create_user(username="ada")
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Archiv")
    erhebung.finalisieren()
    erhebung.archivieren()

    ada.delete()

    assert not Konto.objects.filter(pk=ada.pk).exists()
    erhebung.refresh_from_db()
    assert not erhebung.eigentuemerinnen.exists()

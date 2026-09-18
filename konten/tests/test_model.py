"""Integrationstests für das Nutzer-Modell."""

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import StateApps
from django.db.models import ProtectedError, QuerySet

from konten.models import Konto
from erhebungen.models import Erhebung
from training.models import Training
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


@pytest.mark.django_db(transaction=True)
def test_administrationsmigration_macht_gruppenmitglied_zum_superuser() -> None:
    """Die alte Administration wird ohne Rollenverlust zu Django migriert."""
    vorher: list[tuple[str, str]] = [("konten", "0001_initial")]
    nachher: list[tuple[str, str]] = MigrationExecutor(
        connection
    ).loader.graph.leaf_nodes()
    executor: MigrationExecutor = MigrationExecutor(connection)
    executor.migrate(vorher)
    try:
        apps: StateApps = executor.loader.project_state(vorher).apps
        KontoVorher: type[Konto] = apps.get_model("konten", "Konto")
        GroupVorher: type[Group] = apps.get_model("auth", "Group")
        administration: Group = GroupVorher.objects.create(name="Administrator:in")
        konto: Konto = KontoVorher.objects.create(username="ada")
        konto.groups.add(administration)

        executor = MigrationExecutor(connection)
        executor.migrate([("konten", "0002_administration_ist_superuser")])
        apps = executor.loader.project_state(
            [("konten", "0002_administration_ist_superuser")]
        ).apps
        KontoNachher: type[Konto] = apps.get_model("konten", "Konto")

        migriert: Konto = KontoNachher.objects.get(pk=konto.pk)
        assert (
            migriert.is_superuser,
            migriert.is_staff,
            Group.objects.filter(name="Administrator:in").exists(),
        ) == (True, True, False)
    finally:
        MigrationExecutor(connection).migrate(nachher)


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
def test_superuser_wird_beim_speichern_auch_staff() -> None:
    """Der Superuser-Status öffnet stets auch den Django-Admin."""
    konto: Konto = Konto.objects.create_user(username="admin", is_superuser=True)

    konto.refresh_from_db()

    assert konto.is_staff


@pytest.mark.django_db
def test_konten_mit_rolle_oder_administration_enthaelt_beide() -> None:
    """Ko-Autorinnen können die Fachrolle oder Administration tragen."""
    ausbilderin: Konto = Konto.objects.create_user(username="ausbilderin")
    ausbilderin.groups.add(Group.objects.get(name="Ausbilder:in"))
    administratorin: Konto = Konto.objects.create_user(
        username="administratorin", is_superuser=True
    )
    Konto.objects.create_user(username="teilnehmerin")

    konten: QuerySet[Konto] = Konto.objects.mit_rolle_oder_administration(
        "Ausbilder:in"
    )

    assert set(konten) == {ausbilderin, administratorin}


@pytest.mark.django_db
def test_konto_loeschen_alleinige_eigentuemerin_aktiver_historie_wird_blockiert() -> (
    None
):
    """Eine aktive Vignettenhistorie darf nicht eigentümerlos werden."""
    konto: Konto = get_user_model().objects.create_user(username="ada")
    historie: Vignettenhistorie = Vignettenhistorie.objects.create()
    historie.eigentuemerinnen.add(konto)

    with pytest.raises(ProtectedError):
        konto.delete()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("archiviert", "mit_koeigentuemerin"), [(True, False), (False, True)]
)
def test_konto_loeschen_archivierte_oder_geteilte_historie_ist_erlaubt(
    archiviert: bool, mit_koeigentuemerin: bool
) -> None:
    """Archivierte oder geteilte Historien blockieren keine Kontolöschung."""
    konto: Konto = get_user_model().objects.create_user(username="ada")
    historie: Vignettenhistorie = Vignettenhistorie.objects.create(
        archiviert=archiviert
    )
    historie.eigentuemerinnen.add(konto)
    if mit_koeigentuemerin:
        historie.eigentuemerinnen.add(
            get_user_model().objects.create_user(username="grace")
        )

    konto.delete()


@pytest.mark.django_db
def test_konto_loeschen_alleinige_eigentuemerin_eines_trainings_wird_blockiert() -> (
    None
):
    """Ein Training braucht vor dem Löschen seiner Eigentümerin eine Nachfolgerin."""
    konto: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(konto, name="Brüche")

    with pytest.raises(ProtectedError, match="übertragen"):
        konto.delete()

    assert Training.objects.filter(pk=training.pk).exists()


@pytest.mark.django_db
def test_konto_loeschen_geteiltes_training_ueberlebt() -> None:
    """Eine Ko-Eigentümerin ermöglicht die Kontolöschung ohne Trainingsverlust."""
    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    training: Training = Training.objects.anlegen(ada, name="Brüche")
    training.eigentuemerinnen.add(grace)

    ada.delete()

    training.refresh_from_db()
    assert list(training.eigentuemerinnen.all()) == [grace]


@pytest.mark.django_db
def test_konto_loeschen_aktive_alleinige_erhebung_wird_blockiert() -> None:
    """Aktive Erhebungen brauchen vor der Kontolöschung eine Nachfolgerin."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")

    with pytest.raises(ProtectedError, match="Erhebungen"):
        ada.delete()

    assert Erhebung.objects.filter(pk=erhebung.pk).exists()


@pytest.mark.django_db
def test_konto_loeschen_geteilte_oder_archivierte_erhebung_ueberlebt() -> None:
    """Geteilte und archivierte Erhebungen dürfen den Eigentümer-Kreis verlieren."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    linus: Konto = Konto.objects.create_user(username="linus")
    administratorin: Konto = Konto.objects.create_user(
        username="admin", is_superuser=True
    )
    geteilt: Erhebung = Erhebung.objects.anlegen(ada, name="Geteilt")
    geteilt.eigentuemerinnen.add(grace, linus)
    ada.delete()
    geteilt.refresh_from_db()
    assert set(geteilt.eigentuemerinnen.all()) == {grace, linus}

    archiviert: Erhebung = Erhebung.objects.anlegen(grace, name="Archiv")
    archiviert._schreibqueryset().filter(pk=archiviert.pk).update(
        status=Erhebung.Status.ARCHIVIERT
    )
    grace.delete()
    archiviert.refresh_from_db()
    assert not archiviert.eigentuemerinnen.exists()
    assert list(Erhebung.objects.sichtbar_fuer(administratorin)) == [
        geteilt,
        archiviert,
    ]
    geteilt.refresh_from_db()
    assert list(geteilt.eigentuemerinnen.all()) == [linus]


@pytest.mark.django_db
def test_konto_meldet_sich_mit_username_und_passwort_an() -> None:
    """Ein Konto nutzt den Django-Standardweg zur Anmeldung."""
    konto: Konto = get_user_model().objects.create_user(
        username="lehrerin",
        password="sicheres-passwort",
    )

    assert authenticate(username="lehrerin", password="sicheres-passwort") == konto

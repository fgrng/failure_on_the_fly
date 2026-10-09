"""HTTP-Tests für Auslösen und Ansicht eines Evallaufs."""

import pytest
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from config.tests.aufbau import (
    finale_vignette,
    konto_mit_rollen,
    vignetten_entwurf,
)
from config.tests.formular import submit_knoepfe
from evals.models import Evallauf
from evals.tests.aufbau import (
    antworten,
    drei_fakes,
    fake_aktivieren,
    finaler_katalog,
    urteile,
)
from konten.models import Konto
from simulation.models import Verwendung
from vignetten.models import Vignette

_STARTEN: str = "Evallauf starten"


def _client(konto: Konto) -> Client:
    # Ein angemeldeter Testclient.

    client: Client = Client()
    client.force_login(konto)
    return client


def _knoepfe(antwort: HttpResponse) -> list[str]:
    # Die Beschriftungen aller Absendeknöpfe der Seite.

    return [beschriftung for beschriftung, _ in submit_knoepfe(antwort)]


def _ansicht(vignette: Vignette) -> str:
    # Die URL der Evallauf-Ansicht einer Fassung.

    return reverse("evals:evallauf", args=[vignette.pk])


def _starten(client: Client, vignette: Vignette) -> HttpResponse:
    # Startet per POST und folgt der Weiterleitung auf die Ansicht.

    return client.post(reverse("evals:starten", args=[vignette.pk]), follow=True)


@pytest.fixture
def ada() -> Konto:
    """Eine Autor:in mit eigener Vignette."""

    return konto_mit_rollen("ada", "Autor:in")


@pytest.fixture
def evals_bereit() -> None:
    """Finaler Katalog mit 3 Wiederholungen und drei belegte Verwendungen."""

    finaler_katalog(k=3)
    drei_fakes(
        schuelerin=antworten(6), bewerter=urteile(True, True, False, True, True, True)
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_ohne_lauf_bietet_die_ansicht_den_start_an(ada: Konto) -> None:
    """Eine ungeprüfte Fassung zeigt den Startknopf."""

    vignette: Vignette = vignetten_entwurf(ada)

    antwort: HttpResponse = _client(ada).get(_ansicht(vignette))

    assert _STARTEN in _knoepfe(antwort)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_start_stellt_einen_wartenden_lauf_ohne_zweite_startaktion_ein(
    ada: Konto,
) -> None:
    """Nach dem Start zeigt die Ansicht den Zustand und keinen Startknopf."""

    vignette: Vignette = vignetten_entwurf(ada)

    antwort: HttpResponse = _starten(_client(ada), vignette)

    assert Evallauf.objects.get(vignette=vignette).zustand == Evallauf.Zustand.WARTET
    assert "Wartet" in antwort.content.decode()
    assert _STARTEN not in _knoepfe(antwort)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_wartender_lauf_bietet_neuladen_statt_start(ada: Konto) -> None:
    """Aktualisiert wird durch Neuladen; die Seite darf geschlossen werden."""

    vignette: Vignette = vignetten_entwurf(ada)

    seite: str = _starten(_client(ada), vignette).content.decode()

    assert "Stand neu laden" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_konto_ohne_autorinnenrolle_erhaelt_keinen_zugriff(ada: Konto) -> None:
    """Ansicht und Start ergeben 403 für Konten ohne Autor:innen-Rolle."""

    vignette: Vignette = vignetten_entwurf(ada)
    client: Client = _client(konto_mit_rollen("tom"))

    assert (
        client.get(_ansicht(vignette)).status_code,
        client.post(reverse("evals:starten", args=[vignette.pk])).status_code,
    ) == (403, 403)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_fertiger_lauf_zeigt_quote_und_bestehen(ada: Konto) -> None:
    """Die Übersicht nennt je Zelle Quote und Bestehen zusammen."""

    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _client(ada).get(_ansicht(vignette)).content.decode()

    assert "Fertig" in seite
    assert "2 von 3" in seite and "nicht bestanden" in seite
    assert "3 von 3" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_ko_autorin_und_administration_duerfen_starten(ada: Konto) -> None:
    """Der Eigentümer-Kreis und die Administration, jeweils über den Startknopf."""

    grace: Konto = konto_mit_rollen("grace", "Autor:in")
    admin: Konto = konto_mit_rollen("admin", is_superuser=True)
    eigene: Vignette = vignetten_entwurf(ada)
    eigene.historie.eigentuemerinnen.add(grace)
    andere: Vignette = finale_vignette(konto_mit_rollen("lin", "Autor:in"))

    _starten(_client(grace), eigene)
    _starten(_client(admin), andere)

    assert Evallauf.objects.filter(vignette__in=[eigene, andere]).count() == 2


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_fremde_vignette_bleibt_unlesbar_und_unstartbar(ada: Konto) -> None:
    """Fremde Fassungen ergeben 404, ein Start legt nichts an."""

    fremde: Vignette = finale_vignette(konto_mit_rollen("lin", "Autor:in"))
    client: Client = _client(ada)

    assert client.get(_ansicht(fremde)).status_code == 404
    assert client.post(reverse("evals:starten", args=[fremde.pk])).status_code == 404
    assert not Evallauf.objects.exists()


@pytest.mark.django_db
def test_ohne_dritte_verwendung_gibt_es_keine_evals(ada: Konto) -> None:
    """Fehlt eine Verwendung, sind Ansicht, Start und Verlinkung weg."""

    finaler_katalog()
    fake_aktivieren(Verwendung.SCHUELERIN)
    fake_aktivieren(Verwendung.LEHRPERSON)
    vignette: Vignette = finale_vignette(ada)
    client: Client = _client(ada)

    assert client.get(_ansicht(vignette)).status_code == 404
    assert client.post(reverse("evals:starten", args=[vignette.pk])).status_code == 404
    detail: str = client.get(
        reverse("vignetten:detail", args=[vignette.pk])
    ).content.decode()
    assert _ansicht(vignette) not in detail


@pytest.mark.django_db
def test_ohne_finalen_katalog_gibt_es_keine_evals(ada: Konto) -> None:
    """Ohne finalen Evalkatalog ist die Ansicht nicht erreichbar."""

    drei_fakes()
    vignette: Vignette = finale_vignette(ada)

    assert _client(ada).get(_ansicht(vignette)).status_code == 404


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_vignettenansicht_verlinkt_den_evallauf(ada: Konto) -> None:
    """Die Vignette verlinkt ihre Evals-Ansicht samt Zustand."""

    vignette: Vignette = vignetten_entwurf(ada)
    _starten(_client(ada), vignette)

    detail: str = (
        _client(ada)
        .get(reverse("vignetten:detail", args=[vignette.pk]))
        .content.decode()
    )

    assert _ansicht(vignette) in detail
    assert "Wartet" in detail


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_zweiter_start_ersetzt_keinen_wartenden_lauf(ada: Konto) -> None:
    """Auch ein veralteter Browserstand legt keinen zweiten Lauf an."""

    vignette: Vignette = vignetten_entwurf(ada)
    client: Client = _client(ada)
    _starten(client, vignette)
    erster: Evallauf = Evallauf.objects.get()

    antwort: HttpResponse = _starten(client, vignette)

    assert list(Evallauf.objects.all()) == [erster]
    assert "wartet oder läuft bereits" in antwort.content.decode()


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_neuer_start_ersetzt_den_fertigen_lauf(ada: Konto) -> None:
    """Ein fertiger Vorgänger weicht samt seinen Gesprächen dem neuen Lauf."""

    vignette: Vignette = finale_vignette(ada)
    client: Client = _client(ada)
    _starten(client, vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    alter: Evallauf = Evallauf.objects.get()

    antwort: HttpResponse = _starten(client, vignette)

    neuer: Evallauf = Evallauf.objects.get()
    assert neuer.pk != alter.pk
    assert (neuer.zustand, neuer.gespraeche.count()) == (Evallauf.Zustand.WARTET, 0)
    assert _STARTEN not in _knoepfe(antwort)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_archivierte_fassung_ist_nicht_startbar_und_behaelt_ihren_lauf(
    ada: Konto,
) -> None:
    """Die abgewiesene Startprüfung lässt den bisherigen Lauf unberührt."""

    vignette: Vignette = finale_vignette(ada)
    client: Client = _client(ada)
    _starten(client, vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    bisheriger: Evallauf = Evallauf.objects.get()
    vignette.archivieren()

    antwort: HttpResponse = _starten(client, vignette)

    assert list(Evallauf.objects.all()) == [bisheriger]
    assert _STARTEN not in _knoepfe(antwort)
    assert "Archivierte Fassungen" in antwort.content.decode()


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_finalisieren_behaelt_den_lauf_an_derselben_fassung(ada: Konto) -> None:
    """Der Lauf des Entwurfs gilt nach dem Finalisieren für die finale Fassung."""

    entwurf: Vignette = finale_vignette(ada).bearbeiten()
    _starten(_client(ada), entwurf)
    lauf: Evallauf = Evallauf.objects.get()

    entwurf.finalisieren()

    assert Vignette.objects.get(evallauf=lauf).zustand == Vignette.Zustand.FINAL


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_loeschen_des_entwurfs_entfernt_seinen_lauf(ada: Konto) -> None:
    """Nichts verwaist, wenn der Entwurf verschwindet."""

    entwurf: Vignette = vignetten_entwurf(ada)
    _starten(_client(ada), entwurf)

    entwurf.delete()

    assert not Evallauf.objects.exists()


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_start_nur_per_post(ada: Konto) -> None:
    """Ein GET auf die Startroute legt nichts an."""

    vignette: Vignette = vignetten_entwurf(ada)

    antwort: HttpResponse = _client(ada).get(
        reverse("evals:starten", args=[vignette.pk])
    )

    assert antwort.status_code == 405
    assert not Evallauf.objects.exists()

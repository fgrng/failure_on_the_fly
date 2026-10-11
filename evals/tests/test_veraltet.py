"""Wann ein Evallauf als veraltet gilt, geprüft über die öffentlichen Schreibnähte."""

import pytest
from django.core.management import call_command

from config.tests.aufbau import finale_vignette, konto_mit_rollen, vignetten_entwurf
from evals.models import Evallauf
from evals.tests.aufbau import (
    antworten,
    drei_fakes,
    fake_aktivieren,
    finaler_katalog,
    urteile,
)
from simulation.models import Evalkatalog, Simulationskern, Verwendung
from vignetten.models import Vignette


@pytest.fixture
def entwurf() -> Vignette:
    """Ein Entwurf bei finalem Katalog und drei belegten Verwendungen."""

    finaler_katalog(k=1)
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, True))
    return vignetten_entwurf(konto_mit_rollen("ada", "Autor:in"))


def _lauf(vignette: Vignette) -> Evallauf:
    # Der Lauf der Fassung, frisch gelesen.

    return Evallauf.objects.get(vignette=vignette)


def _neuer_kern() -> Simulationskern:
    # Finalisiert eine neue Kern-Fassung; die bisherige wird überholt.

    neuer: Simulationskern = Simulationskern.objects.finale_fassung().bearbeiten()
    neuer.finalisieren()
    return neuer


@pytest.mark.django_db
def test_unveraenderter_lauf_ist_aktuell(entwurf: Vignette) -> None:
    """Ohne Änderung seit dem Start gibt es keinen Grund."""

    Evallauf.objects.ausloesen(entwurf)

    assert (_lauf(entwurf).veraltet, _lauf(entwurf).veraltungsgruende) == (False, [])


@pytest.mark.django_db
def test_gespeicherter_entwurf_macht_den_lauf_veraltet(entwurf: Vignette) -> None:
    """Jedes Speichern des Entwurfs nach dem Start zählt."""

    Evallauf.objects.ausloesen(entwurf)

    entwurf.thema = "Neues Thema"
    entwurf.save()

    assert _lauf(entwurf).veraltungsgruende == ["Vignette bearbeitet"]


@pytest.mark.django_db
def test_eingeschraenkte_feldaktualisierung_macht_den_lauf_veraltet(
    entwurf: Vignette,
) -> None:
    """Auch ein Speichern mit update_fields setzt den Änderungszeitstempel."""

    Evallauf.objects.ausloesen(entwurf)

    entwurf.thema = "Neues Thema"
    entwurf.save(update_fields=["thema"])

    assert _lauf(entwurf).veraltet


@pytest.mark.django_db
def test_leere_feldaktualisierung_laesst_den_lauf_aktuell(entwurf: Vignette) -> None:
    """Ein Speichern ohne Felder schreibt nichts und ändert damit auch nichts."""

    Evallauf.objects.ausloesen(entwurf)

    entwurf.save(update_fields=[])

    assert not _lauf(entwurf).veraltet


@pytest.mark.django_db
def test_vorspulen_macht_den_lauf_veraltet(entwurf: Vignette) -> None:
    """Ein neuer Kern-Pin nach dem Start zählt als geänderte Vignette und Kern."""

    Evallauf.objects.ausloesen(entwurf)
    _neuer_kern()

    entwurf.vorspulen()

    assert _lauf(entwurf).veraltungsgruende == [
        "Vignette bearbeitet",
        "Simulationskern gewechselt",
    ]


@pytest.mark.django_db
def test_neuer_finaler_kern_allein_laesst_den_lauf_aktuell(entwurf: Vignette) -> None:
    """Der gepinnte Kern bleibt der festgehaltene, solange niemand vorspult."""

    Evallauf.objects.ausloesen(entwurf)

    _neuer_kern()

    assert not _lauf(entwurf).veraltet


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("verwendung", "grund"),
    [
        (Verwendung.SCHUELERIN, "Konfiguration Schüler:in gewechselt"),
        (Verwendung.LEHRPERSON, "Konfiguration Lehrperson gewechselt"),
        (Verwendung.BEWERTER, "Konfiguration Bewerter gewechselt"),
    ],
)
def test_gewechselte_konfiguration_macht_den_lauf_veraltet(
    entwurf: Vignette, verwendung: Verwendung, grund: str
) -> None:
    """Jede der drei Verwendungen zählt für sich."""

    Evallauf.objects.ausloesen(entwurf)

    fake_aktivieren(verwendung)

    assert _lauf(entwurf).veraltungsgruende == [grund]


@pytest.mark.django_db
def test_neue_finale_katalogfassung_macht_den_lauf_veraltet(entwurf: Vignette) -> None:
    """Geprüft wurde gegen eine Katalogfassung, die nicht mehr gilt."""

    Evallauf.objects.ausloesen(entwurf)

    Evalkatalog.objects.finale_fassung().bearbeiten().finalisieren()

    assert _lauf(entwurf).veraltungsgruende == ["Evalkatalog gewechselt"]


@pytest.mark.django_db
def test_aenderung_waehrend_der_lauf_wartet_ist_erkennbar(entwurf: Vignette) -> None:
    """Verglichen wird mit dem Stand beim Auslösen, nicht beim Arbeitsbeginn."""

    Evallauf.objects.ausloesen(entwurf)
    entwurf.thema = "Neues Thema"
    entwurf.save()

    call_command("evallaeufe_abarbeiten", "--einmal")

    lauf: Evallauf = _lauf(entwurf)
    assert (lauf.zustand, lauf.veraltet) == (Evallauf.Zustand.FERTIG, True)


@pytest.mark.django_db
def test_finalisieren_laesst_den_lauf_aktuell() -> None:
    """Finalisieren ist kein Bearbeiten; der Lauf bleibt an derselben Fassung aktuell."""

    finaler_katalog(k=1)
    drei_fakes()
    entwurf: Vignette = finale_vignette(
        konto_mit_rollen("ada", "Autor:in")
    ).bearbeiten()
    Evallauf.objects.ausloesen(entwurf)

    entwurf.finalisieren()

    lauf: Evallauf = _lauf(entwurf)
    assert (lauf.vignette.zustand, lauf.veraltet) == (Vignette.Zustand.FINAL, False)

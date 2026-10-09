"""Tests der gemeinsamen Aufbau-Helfer."""

import pytest
from django.contrib.auth.models import Group

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    finaler_kern,
    konto_mit_rollen,
    vignetten_entwurf,
)
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from vignetten.models import Vignette


@pytest.mark.django_db
def test_konto_traegt_die_uebergebenen_rollen() -> None:
    """Das Konto trägt jede übergebene Rolle und keine andere Fachrolle."""

    angelegt: Konto = konto_mit_rollen("ada", "Forschende:r", "Autor:in")

    assert angelegt.rollen() == ["Autor:in", "Forschende:r"]


@pytest.mark.django_db
def test_konto_ohne_rolle_traegt_keine() -> None:
    """Ohne Rolle entsteht ein schlichtes Konto."""

    assert konto_mit_rollen("ada").rollen() == []


@pytest.mark.django_db
def test_konto_mit_unbekannter_rolle_scheitert() -> None:
    """Ein Tippfehler im Rollennamen fällt auf, statt eine leere Gruppe anzulegen."""

    with pytest.raises(Group.DoesNotExist):
        konto_mit_rollen("ada", "Autorin")


@pytest.mark.django_db
def test_finaler_kern_ist_final() -> None:
    """Der gelieferte Kern ist final."""

    assert finaler_kern().zustand == Simulationskern.Zustand.FINAL


@pytest.mark.django_db
def test_finaler_kern_liefert_beim_zweiten_aufruf_denselben() -> None:
    """Ein zweiter Aufruf liefert den schon finalen Kern statt zu scheitern."""

    kern: Simulationskern = finaler_kern()

    assert finaler_kern() == kern


@pytest.mark.django_db
def test_aktive_modell_konfiguration_belegt_die_verwendung() -> None:
    """Die angelegte Konfiguration ist für ihre Verwendung aktiv."""

    konfiguration: ModellKonfiguration = aktive_modell_konfiguration(
        Verwendung.BEWERTER
    )

    assert ModellKonfiguration.objects.belegte(Verwendung.BEWERTER) == konfiguration


@pytest.mark.django_db
def test_vignetten_entwurf_ist_ein_entwurf() -> None:
    """Der Helfer liefert einen Entwurf."""

    entwurf: Vignette = vignetten_entwurf(konto_mit_rollen("ada"))

    assert entwurf.zustand == Vignette.Zustand.ENTWURF


@pytest.mark.django_db
def test_vignetten_entwurf_liegt_im_bestand_des_kontos() -> None:
    """Der Entwurf gehört dem übergebenen Konto."""

    autorin: Konto = konto_mit_rollen("ada")

    entwurf: Vignette = vignetten_entwurf(autorin)

    assert Vignette.objects.sichtbar_fuer(autorin).get() == entwurf


@pytest.mark.django_db
def test_finale_vignette_ist_final_und_pinnt_einen_finalen_kern() -> None:
    """Ohne vorhandenen Kern legt der Helfer selbst einen finalen an."""

    vignette: Vignette = finale_vignette(konto_mit_rollen("ada"))

    assert vignette.zustand == Vignette.Zustand.FINAL
    assert vignette.gepinnter_kern.zustand == Simulationskern.Zustand.FINAL


@pytest.mark.django_db
def test_finale_vignette_uebernimmt_uebergebene_felder() -> None:
    """Übergebene Felder und der Name ersetzen die Vorgaben."""

    vignette: Vignette = finale_vignette(
        konto_mit_rollen("ada"), name="Zweite Fassung", fach="Deutsch", budget_wert=7
    )

    vignette.refresh_from_db()
    assert (vignette.historie.name, vignette.fach, vignette.budget_wert) == (
        "Zweite Fassung",
        "Deutsch",
        7,
    )


@pytest.mark.django_db
def test_finale_vignette_weist_ein_unbekanntes_feld_ab() -> None:
    """Ein Tippfehler im Feldnamen fällt auf, statt die Vorgabe stehen zu lassen."""

    with pytest.raises(TypeError):
        finale_vignette(konto_mit_rollen("ada"), fachh="Deutsch")

"""Tests für den gemeinsamen Eigentümer-Kreis der bestandstragenden Modelle."""

import pytest
from django.apps import apps
from django.db.models import Model

from erhebungen.models import Erhebung
from fragebogen_items.models import FragebogenItemHistorie
from konten.eigentuemerschaft import EigentuemerKreis
from konten.models import Konto
from konten.navigation import (
    AUSBILDERIN_GRUPPE,
    AUTORIN_GRUPPE,
    FORSCHENDE_GRUPPE,
)
from simulation.models import ModellKonfiguration, Simulationskern
from training.models import Training
from vignetten.models import Vignettenhistorie


def _eigentuemer_tragende_modelle() -> list[type[Model]]:
    # Dieselbe Herleitung, die der Löschpfad später benutzt: die Registrierung.
    return [
        modell for modell in apps.get_models() if issubclass(modell, EigentuemerKreis)
    ]


def test_die_vier_bestaende_tragen_den_gemeinsamen_kreis() -> None:
    """Genau die vier eigentümer-tragenden Bestände erben von der Basis."""
    assert set(_eigentuemer_tragende_modelle()) == {
        Vignettenhistorie,
        FragebogenItemHistorie,
        Training,
        Erhebung,
    }


def test_simulationskern_traegt_keinen_eigentuemer_kreis() -> None:
    """Der Kern gehört der Administration und hat keinen Eigentümer-Kreis."""
    assert not issubclass(Simulationskern, EigentuemerKreis)
    assert not hasattr(Simulationskern, "eigentuemerinnen")


@pytest.mark.parametrize("modell", _eigentuemer_tragende_modelle())
def test_jeder_kreis_zeigt_auf_konten(modell: type[Model]) -> None:
    """Der Kreis ist überall dasselbe M2M-Feld auf das Konto."""
    feld = modell._meta.get_field("eigentuemerinnen")

    assert feld.many_to_many
    assert feld.related_model is Konto


@pytest.mark.parametrize(
    ("modell", "gruppe"),
    [
        (Vignettenhistorie, AUTORIN_GRUPPE),
        (Training, AUSBILDERIN_GRUPPE),
        (Erhebung, FORSCHENDE_GRUPPE),
        (FragebogenItemHistorie, FORSCHENDE_GRUPPE),
    ],
)
def test_jeder_kreis_nennt_seine_rollengruppe(modell: type[Model], gruppe: str) -> None:
    """Aus dem Modell folgt, welche Rolle in seinen Kreis eintragbar ist."""
    assert modell.ROLLENGRUPPE == gruppe


@pytest.mark.django_db
def test_training_und_item_historie_sind_immer_aktiv() -> None:
    """Beide kennen keine Stilllegung und bleiben deshalb aktiv."""
    assert Training.objects.create(name="Kurs").ist_aktiv()
    assert FragebogenItemHistorie.objects.create().ist_aktiv()


@pytest.mark.django_db
def test_vignettenhistorie_ist_archiviert_nicht_mehr_aktiv() -> None:
    """Die Vignettenhistorie leitet ihren Haken aus dem Archiv-Kennzeichen ab."""
    assert Vignettenhistorie.objects.create(archiviert=False).ist_aktiv()
    assert not Vignettenhistorie.objects.create(archiviert=True).ist_aktiv()


@pytest.mark.django_db
def test_erhebung_ist_archiviert_nicht_mehr_aktiv() -> None:
    """Die Erhebung leitet ihren Haken aus ihrem Status ab."""
    konto: Konto = Konto.objects.create_user(username="ada")
    ModellKonfiguration.objects.aktivieren(
        ModellKonfiguration.objects.create(sprachmodell="fake")
    )
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Studie")

    assert erhebung.ist_aktiv()

    erhebung.finalisieren()
    erhebung.archivieren()

    assert not erhebung.ist_aktiv()


@pytest.mark.django_db
def test_kreis_meldet_ob_mehr_als_eine_eigentuemerin_eingetragen_ist() -> None:
    """Die Eigenschaft trägt, was heute vier Views als Kontext bauen."""
    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    training: Training = Training.objects.anlegen(ada, name="Kurs")

    assert not training.hat_mehrere_eigentuemerinnen

    training.eigentuemerinnen.add(grace)

    assert training.hat_mehrere_eigentuemerinnen

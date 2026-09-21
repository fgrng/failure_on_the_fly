"""Tests für den gemeinsamen Eigentümer-Kreis der bestandstragenden Modelle."""

from collections.abc import Callable

import pytest
from django.db import connection
from django.db.models import Model

from erhebungen.models import Erhebung
from fragebogen_items.models import FragebogenItemHistorie
from konten.eigentuemerschaft import EigentuemerKreis, bestandsmodelle
from konten.models import Konto
from konten.navigation import (
    AUSBILDERIN_GRUPPE,
    AUTORIN_GRUPPE,
    FORSCHENDE_GRUPPE,
)
from simulation.models import ModellKonfiguration, Simulationskern
from training.models import Training
from vignetten.models import Vignettenhistorie


def test_die_vier_bestaende_tragen_den_gemeinsamen_kreis() -> None:
    """Genau die vier eigentümer-tragenden Bestände erben von der Basis."""
    assert set(bestandsmodelle()) == {
        Vignettenhistorie,
        FragebogenItemHistorie,
        Training,
        Erhebung,
    }


def test_simulationskern_traegt_keinen_eigentuemer_kreis() -> None:
    """Der Kern gehört der Administration und hat keinen Eigentümer-Kreis."""
    assert not issubclass(Simulationskern, EigentuemerKreis)
    assert not hasattr(Simulationskern, "eigentuemerinnen")


@pytest.mark.parametrize("modell", bestandsmodelle())
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


@pytest.mark.django_db
def test_austritt_eines_fremden_kontos_entfernt_nichts() -> None:
    """Wer nicht im Kreis steht, kann ihn nicht verlassen."""
    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    linus: Konto = Konto.objects.create_user(username="linus")
    training: Training = Training.objects.anlegen(ada, name="Kurs")
    training.eigentuemerinnen.add(grace)

    assert not training.austreten(linus.pk)
    assert list(training.eigentuemerinnen.all()) == [ada, grace]


@pytest.mark.django_db
def test_archivierter_bestand_behaelt_seine_letzte_eigentuemerin() -> None:
    """Die Invariante am Objekt fragt nicht nach `ist_aktiv()` (ADR-0032)."""
    ada: Konto = Konto.objects.create_user(username="ada")
    historie: Vignettenhistorie = Vignettenhistorie.objects.create(archiviert=True)
    historie.eigentuemerinnen.add(ada)

    assert not historie.austreten(ada.pk)
    assert list(historie.eigentuemerinnen.all()) == [ada]


@pytest.mark.django_db(transaction=True)
def test_austritt_laeuft_vollstaendig_in_einer_transaktion() -> None:
    """Zwei gleichzeitige Austritte können den Kreis nicht eigentümerlos machen.

    Serialisiert wird über die Verbindungsoption `transaction_mode: IMMEDIATE`:
    Die Schreibsperre hängt am `atomic()` selbst. Beobachtet wird deshalb, dass
    jede Anweisung des Austritts zur selben Transaktion gehört — im Autocommit
    läsen zwei Austritte denselben Zwei-Personen-Kreis und träten beide aus.
    """
    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    training: Training = Training.objects.anlegen(ada, name="Kurs")
    training.eigentuemerinnen.add(grace)
    kreistabelle: str = Training.eigentuemerinnen.through._meta.db_table
    in_transaktion: list[bool] = []

    def mitschreiben(
        ausfuehren: Callable[..., object],
        sql: str,
        parameter: object,
        viele: bool,
        kontext: dict[str, object],
    ) -> object:
        # Die Transaktionsklammer selbst (BEGIN, COMMIT) bleibt außen vor;
        # gefragt ist, ob Lesen und Schreiben am Kreis drinnen liegen.
        if kreistabelle in sql:
            in_transaktion.append(connection.in_atomic_block)
        return ausfuehren(sql, parameter, viele, kontext)

    with connection.execute_wrapper(mitschreiben):
        assert training.austreten(ada.pk)

    assert in_transaktion and all(in_transaktion)
    assert list(training.eigentuemerinnen.all()) == [grace]

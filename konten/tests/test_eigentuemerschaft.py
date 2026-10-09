"""Tests für den gemeinsamen Eigentümer-Kreis der bestandstragenden Modelle."""

from collections.abc import Callable

import pytest
from django.db import connection

from config.tests.aufbau import konto_mit_rollen
from erhebungen.models import Erhebung
from fragebogen_items.models import FragebogenItemHistorie
from konten.eigentuemerschaft import EigentuemerKreis, bestandsmodelle
from konten.models import Konto
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("modell", "gruppe", "andere_fachrolle"),
    [
        (Vignettenhistorie, "Autor:in", "Forschende:r"),
        (Training, "Ausbilder:in", "Autor:in"),
        (Erhebung, "Forschende:r", "Autor:in"),
        (FragebogenItemHistorie, "Forschende:r", "Ausbilder:in"),
    ],
    ids=lambda wert: wert.__name__ if isinstance(wert, type) else wert,
)
def test_jeder_kreis_nimmt_nur_seine_rollengruppe_auf(
    modell: type[EigentuemerKreis], gruppe: str, andere_fachrolle: str
) -> None:
    """Aus dem Modell folgt, welche Rolle in seinen Kreis eintragbar ist."""
    ada: Konto = Konto.objects.create_user(username="ada")
    passend: Konto = konto_mit_rollen("passend", gruppe)
    unpassend: Konto = konto_mit_rollen("unpassend", andere_fachrolle)
    bestand: EigentuemerKreis = modell.objects.anlegen(ada)  # ty: ignore[unresolved-attribute]

    kandidaten: set[Konto] = set(bestand.moegliche_ergaenzungen())

    assert passend in kandidaten
    assert unpassend not in kandidaten


@pytest.mark.django_db
def test_kreis_meldet_ob_mehr_als_eine_eigentuemerin_eingetragen_ist() -> None:
    """Die Eigenschaft steuert, ob der Abschnitt eine Entfernen-Aktion anbietet."""
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

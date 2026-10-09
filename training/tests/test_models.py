"""ORM-Tests für Trainings."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from config.tests.aufbau import finale_vignette, vignetten_entwurf
from konten.models import Konto
from sitzungen.models import Teilnahme
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette


@pytest.mark.django_db
def test_veroeffentlichen_ueberfuehrt_einen_entwurf() -> None:
    """Ein Training kann genau einmal vom Entwurf veröffentlicht werden."""

    training: Training = Training.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Bruchrechnung"
    )

    training.veroeffentlichen()

    training.refresh_from_db()
    assert training.zustand == Training.Zustand.VEROEFFENTLICHT


@pytest.mark.django_db
def test_veroeffentlichen_lehnt_wiederholung_ab() -> None:
    """Ein veröffentlichtes Training kann nicht erneut veröffentlicht werden."""

    training: Training = Training.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Bruchrechnung"
    )
    training.veroeffentlichen()

    with pytest.raises(ValidationError, match="Nur Entwürfe"):
        training.veroeffentlichen()


@pytest.mark.django_db
def test_veroeffentlichen_lehnt_veralteten_entwurf_ab() -> None:
    """Auch eine veraltete Instanz kann ein Training nicht erneut veröffentlichen."""

    training: Training = Training.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Bruchrechnung"
    )
    veralteter_entwurf: Training = Training.objects.get(pk=training.pk)
    training.veroeffentlichen()

    with pytest.raises(ValidationError, match="Nur Entwürfe"):
        veralteter_entwurf.veroeffentlichen()


@pytest.mark.django_db
def test_training_muss_als_entwurf_angelegt_werden() -> None:
    """Veröffentlichen bleibt der einzige Einstieg in den veröffentlichten Zustand."""

    with pytest.raises(ValidationError, match="Lebenszyklus"):
        Training.objects.create(
            name="Bruchrechnung", zustand=Training.Zustand.VEROEFFENTLICHT
        )


@pytest.mark.django_db
def test_training_verhindert_direkte_zustandswechsel_beim_speichern() -> None:
    """Der Zustand eines gespeicherten Trainings wechselt nur im Lebenszyklus."""

    training: Training = Training.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Bruchrechnung"
    )
    training.veroeffentlichen()
    training.zustand = Training.Zustand.ENTWURF

    with pytest.raises(ValidationError, match="Zustandswechsel"):
        training.save()


@pytest.mark.django_db
def test_training_verhindert_massenhafte_zustandswechsel() -> None:
    """Der QuerySet-Weg umgeht die Lebenszyklus-Naht nicht."""

    training: Training = Training.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Bruchrechnung"
    )
    training.veroeffentlichen()

    with pytest.raises(RuntimeError, match="Lebenszyklus"):
        Training.objects.filter(pk=training.pk).update(zustand=Training.Zustand.ENTWURF)


@pytest.mark.django_db
def test_training_bindet_nur_finale_vignetten_und_bleibt_austauschbar() -> None:
    """Finale Fassungen lassen sich auch nach der Veröffentlichung austauschen."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    entwurf: Vignette = vignetten_entwurf(ada)
    finale: Vignette = finale_vignette(ada)

    with pytest.raises(ValidationError, match="finale"), transaction.atomic():
        training.vignetten.add(entwurf)
    with pytest.raises(IntegrityError, match="finale"), transaction.atomic():
        training.vignetten.through.objects.create(
            training=training,
            vignette=entwurf,
        )

    training.vignetten.add(finale)
    training.veroeffentlichen()
    training.vignetten.remove(finale)

    assert list(training.vignetten.all()) == []


@pytest.mark.django_db
def test_finale_vignette_kann_rueckwaerts_eingebunden_und_archiviert_werden() -> None:
    """Die Rückwärtsrelation akzeptiert finale Fassungen und Archivieren entfernt sie."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    finale: Vignette = finale_vignette(ada)

    finale.training_set.add(training)
    assert list(training.vignetten.all()) == [finale]

    finale.archivieren()

    assert list(training.vignetten.all()) == []


@pytest.mark.django_db
def test_teilnahme_traegt_hoechstens_eine_trainingsbindung() -> None:
    """Eine Teilnahme lässt sich nicht an eine zweite Trainingsbindung koppeln."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    teilnahme: Teilnahme = Teilnahme.objects.create()
    Trainingsbindung.objects.create(
        teilnahme=teilnahme,
        training=Training.objects.anlegen(ada, name="Bruchrechnung"),
        konto=ada,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Trainingsbindung.objects.create(
            teilnahme=teilnahme,
            training=Training.objects.anlegen(grace, name="Addition"),
            konto=grace,
        )


@pytest.mark.django_db
def test_konto_hat_je_training_hoechstens_eine_trainingsbindung() -> None:
    """Dasselbe Konto bindet sich an dasselbe Training nicht ein zweites Mal."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    Trainingsbindung.objects.create(
        teilnahme=Teilnahme.objects.create(), training=training, konto=ada
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Trainingsbindung.objects.create(
            teilnahme=Teilnahme.objects.create(), training=training, konto=ada
        )

"""ORM-Tests für Trainings."""

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.utils import timezone

from konten.models import Konto
from sitzungen.models import Teilnahme
from training.models import Training
from training.models import Trainingsbindung
from vignetten.models import Vignette, Vignettenhistorie


@pytest.mark.django_db
def test_veroeffentlichen_ueberfuehrt_einen_entwurf_und_lehnt_wiederholung_ab() -> None:
    """Ein Training kann genau einmal vom Entwurf veröffentlicht werden."""

    training: Training = Training.objects.create(
        name="Bruchrechnung",
        eigentuemerin=Konto.objects.create_user(username="ada"),
    )

    training.veroeffentlichen()

    training.refresh_from_db()
    assert training.zustand == Training.Zustand.VEROEFFENTLICHT
    with pytest.raises(ValidationError, match="Nur Entwürfe"):
        training.veroeffentlichen()
    training.zustand = Training.Zustand.ENTWURF
    with pytest.raises(ValidationError, match="Zustandswechsel"):
        training.save()
    with pytest.raises(RuntimeError, match="Lebenszyklus"):
        Training.objects.filter(pk=training.pk).update(zustand=Training.Zustand.ENTWURF)


@pytest.mark.django_db
def test_training_bindet_nur_finale_vignetten_und_bleibt_austauschbar() -> None:
    """Finale Fassungen lassen sich auch nach der Veröffentlichung austauschen."""

    training: Training = Training.objects.create(
        name="Bruchrechnung",
        eigentuemerin=Konto.objects.create_user(username="ada"),
    )
    entwurf: Vignette = Vignette.objects._erstellen(
        historie=Vignettenhistorie.objects.create()
    )
    finale: Vignette = Vignette.objects._erstellen(
        historie=Vignettenhistorie.objects.create(),
        zustand=Vignette.Zustand.FINAL,
        finalisiert_am=timezone.now(),
        arbeitsheft_text="Bearbeitung",
    )

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
def test_trainingsbindung_haelt_training_konto_und_genau_eine_teilnahme() -> None:
    """Eine Teilnahme kann nur an eine Trainingsbindung gekoppelt sein."""

    konto: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.create(
        name="Bruchrechnung", eigentuemerin=konto
    )
    teilnahme: Teilnahme = Teilnahme.objects.create()

    bindung: Trainingsbindung = Trainingsbindung.objects.create(
        teilnahme=teilnahme,
        training=training,
        konto=konto,
    )

    assert (bindung.teilnahme, bindung.training, bindung.konto) == (
        teilnahme,
        training,
        konto,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Trainingsbindung.objects.create(
            teilnahme=teilnahme,
            training=training,
            konto=konto,
        )


@pytest.mark.django_db
def test_sichtbar_fuer_liefert_eigene_trainings_und_alle_fuer_administration() -> None:
    """Ausbilderinnen sehen nur eigene Trainings, Administratorinnen alle."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    administratorin: Konto = Konto.objects.create_user(username="linus")
    administratorin.groups.add(Group.objects.get(name="Administrator:in"))
    eigenes: Training = Training.objects.create(name="Brüche", eigentuemerin=ada)
    fremdes: Training = Training.objects.create(name="Addition", eigentuemerin=grace)

    assert list(Training.objects.sichtbar_fuer(ada)) == [eigenes]
    assert list(Training.objects.sichtbar_fuer(administratorin)) == [eigenes, fremdes]

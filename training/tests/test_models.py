"""ORM-Tests für Trainings."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from konten.models import Konto
from sitzungen.models import Teilnahme
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette, Vignettenhistorie


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

    training: Training = Training.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Bruchrechnung"
    )
    entwurf: Vignette = Vignette.objects._erstellen(
        historie=Vignettenhistorie.objects.create()
    )
    finale: Vignette = Vignette.objects._erstellen(
        historie=Vignettenhistorie.objects.create(),
        zustand=Vignette.Zustand.FINAL,
        finalisiert_am=timezone.now(),
        lernauftrag_text="Lernauftrag",
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
def test_finale_vignette_kann_rueckwaerts_eingebunden_und_archiviert_werden() -> None:
    """Die Rückwärtsrelation akzeptiert finale Fassungen und Archivieren entfernt sie."""

    training: Training = Training.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Bruchrechnung"
    )
    Vignette.objects._erstellen(historie=Vignettenhistorie.objects.create())
    finale: Vignette = Vignette.objects._erstellen(
        historie=Vignettenhistorie.objects.create(),
        zustand=Vignette.Zustand.FINAL,
        finalisiert_am=timezone.now(),
        lernauftrag_text="Lernauftrag",
        arbeitsheft_text="Bearbeitung",
    )

    finale.training_set.add(training)
    assert list(training.vignetten.all()) == [finale]

    finale.archivieren()

    assert list(training.vignetten.all()) == []


@pytest.mark.django_db
def test_trainingsbindung_haelt_training_konto_und_genau_eine_teilnahme() -> None:
    """Eine Teilnahme kann nur an eine Trainingsbindung gekoppelt sein."""

    konto: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(konto, name="Bruchrechnung")
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
    administratorin.is_superuser = True
    administratorin.save()
    eigenes: Training = Training.objects.anlegen(ada, name="Brüche")
    fremdes: Training = Training.objects.anlegen(grace, name="Addition")

    assert list(Training.objects.sichtbar_fuer(ada)) == [eigenes]
    assert list(Training.objects.sichtbar_fuer(administratorin)) == [eigenes, fremdes]


@pytest.mark.django_db
def test_geteiltes_training_ist_fuer_alle_eigentuemerinnen_sichtbar() -> None:
    """Alle Eigentümerinnen können ein gemeinsames Training sehen."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    training: Training = Training.objects.anlegen(ada, name="Brüche")
    training.eigentuemerinnen.add(grace)

    assert list(Training.objects.sichtbar_fuer(ada)) == [training]
    assert list(Training.objects.sichtbar_fuer(grace)) == [training]


@pytest.mark.django_db
def test_veroeffentlichtes_training_behaelt_aenderbaren_eigentuemerinnenkreis() -> None:
    """Das Veröffentlichen friert die Verantwortung nicht ein."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    training: Training = Training.objects.anlegen(ada, name="Brüche")
    training.veroeffentlichen()

    training.eigentuemerinnen.add(grace)
    training.eigentuemerinnen.remove(ada)

    assert list(training.eigentuemerinnen.all()) == [grace]
    assert training.zustand == Training.Zustand.VEROEFFENTLICHT

"""ORM-Tests für Trainings."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from config.tests.aufbau import finale_vignette, vignetten_entwurf
from konten.models import Konto
from sitzungen.models import Teilnahme
from training.models import Training, Trainingsbindung, Trainingsvignette
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
        training.vignette_aufnehmen(entwurf)
    with pytest.raises(IntegrityError, match="finale"), transaction.atomic():
        Trainingsvignette.objects.bulk_create(
            [Trainingsvignette(training=training, vignette=entwurf, position=1)]
        )

    training.vignette_aufnehmen(finale)
    training.veroeffentlichen()
    training.vignette_entfernen(finale)

    assert list(training.vignetten_in_reihenfolge()) == []


@pytest.mark.django_db
def test_archivieren_entfernt_die_vignette_aus_allen_trainings() -> None:
    """Eine archivierte Fassung verschwindet aus den Trainings, die sie enthielten."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    zweites: Training = Training.objects.anlegen(ada, name="Addition")
    finale: Vignette = finale_vignette(ada)
    bleibende: Vignette = finale_vignette(ada, name="Bleibt")
    training.vignette_aufnehmen(finale)
    training.vignette_aufnehmen(bleibende)
    zweites.vignette_aufnehmen(finale)

    finale.archivieren()

    assert [
        list(training.vignetten_in_reihenfolge()),
        list(zweites.vignetten_in_reihenfolge()),
    ] == [[bleibende], []]


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


@pytest.mark.django_db
def test_neu_aufgenommene_vignette_steht_am_ende() -> None:
    """Die Vignetten eines Trainings folgen der Reihenfolge ihrer Aufnahme."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    erste: Vignette = finale_vignette(ada, name="Erste")
    zweite: Vignette = finale_vignette(ada, name="Zweite")
    dritte: Vignette = finale_vignette(ada, name="Dritte")

    training.vignette_aufnehmen(zweite)
    training.vignette_aufnehmen(dritte)
    training.vignette_aufnehmen(erste)

    assert list(training.vignetten_in_reihenfolge()) == [zweite, dritte, erste]


@pytest.mark.django_db
def test_entfernen_laesst_die_nachfolgenden_lueckenlos_nachruecken() -> None:
    """Nach dem Entfernen tragen die übrigen Vignetten wieder die Positionen 1..n."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    vignetten: list[Vignette] = [
        finale_vignette(ada, name=name) for name in ("Erste", "Zweite", "Dritte")
    ]
    for vignette in vignetten:
        training.vignette_aufnehmen(vignette)

    training.vignette_entfernen(vignetten[0])

    assert list(
        training.vignettenzugehoerigkeiten.values_list("vignette", "position")
    ) == [(vignetten[1].pk, 1), (vignetten[2].pk, 2)]


@pytest.mark.django_db
def test_erneutes_aufnehmen_laesst_die_position_unveraendert() -> None:
    """Eine Vignette steht höchstens einmal im Training."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    erste: Vignette = finale_vignette(ada, name="Erste")
    zweite: Vignette = finale_vignette(ada, name="Zweite")
    training.vignette_aufnehmen(erste)
    training.vignette_aufnehmen(zweite)

    training.vignette_aufnehmen(erste)

    assert list(training.vignetten_in_reihenfolge()) == [erste, zweite]


@pytest.mark.django_db
def test_reihenfolge_gilt_je_training() -> None:
    """Dieselbe Vignette steht in zwei Trainings an unterschiedlichen Stellen."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    zweites: Training = Training.objects.anlegen(ada, name="Addition")
    erste: Vignette = finale_vignette(ada, name="Erste")
    zweite: Vignette = finale_vignette(ada, name="Zweite")
    training.vignette_aufnehmen(erste)
    training.vignette_aufnehmen(zweite)
    zweites.vignette_aufnehmen(zweite)
    zweites.vignette_aufnehmen(erste)

    assert [
        list(training.vignetten_in_reihenfolge()),
        list(zweites.vignetten_in_reihenfolge()),
    ] == [[erste, zweite], [zweite, erste]]


@pytest.mark.django_db
def test_trainingsvignette_braucht_eine_position() -> None:
    """Ohne Position lässt sich keine Vignette in ein Training einbinden."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")

    with pytest.raises(IntegrityError), transaction.atomic():
        Trainingsvignette.objects.create(
            training=training, vignette=finale_vignette(ada), position=None
        )


@pytest.mark.django_db
def test_position_ist_je_training_eindeutig() -> None:
    """Zwei Vignetten eines Trainings teilen sich keine Position."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    Trainingsvignette.objects.create(
        training=training, vignette=finale_vignette(ada, name="Erste"), position=1
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Trainingsvignette.objects.create(
            training=training, vignette=finale_vignette(ada, name="Zweite"), position=1
        )


@pytest.mark.django_db
def test_vignette_steht_hoechstens_einmal_im_training() -> None:
    """Das Paar aus Training und Vignette gibt es nur einmal."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    vignette: Vignette = finale_vignette(ada)
    Trainingsvignette.objects.create(training=training, vignette=vignette, position=1)

    with pytest.raises(IntegrityError), transaction.atomic():
        Trainingsvignette.objects.create(
            training=training, vignette=vignette, position=2
        )


@pytest.mark.django_db
def test_entfernen_schliesst_auch_vorhandene_luecken() -> None:
    """Auch eine Reihenfolge mit Lücken wird beim Entfernen wieder lückenlos."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    vignetten: list[Vignette] = [
        finale_vignette(ada, name=name) for name in ("Erste", "Zweite", "Dritte")
    ]
    for position, vignette in zip((1, 4, 7), vignetten, strict=True):
        Trainingsvignette.objects.create(
            training=training, vignette=vignette, position=position
        )

    training.vignette_entfernen(vignetten[2])

    assert list(
        training.vignettenzugehoerigkeiten.values_list("vignette", "position")
    ) == [(vignetten[0].pk, 1), (vignetten[1].pk, 2)]


@pytest.mark.django_db
def test_verschieben_reiht_die_uebrigen_neu_ein() -> None:
    """Die verschobene Vignette steht an der Zielposition, die übrigen rücken."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    erste, zweite, dritte = (
        finale_vignette(ada, name=name) for name in ("Erste", "Zweite", "Dritte")
    )
    for vignette in (erste, zweite, dritte):
        training.vignette_aufnehmen(vignette)

    training.vignette_verschieben(dritte, 1)

    assert list(
        training.vignettenzugehoerigkeiten.values_list("vignette", "position")
    ) == [(dritte.pk, 1), (erste.pk, 2), (zweite.pk, 3)]


@pytest.mark.django_db
def test_verschieben_begrenzt_die_zielposition_auf_die_liste() -> None:
    """Eine Zielposition außerhalb der Liste setzt an Anfang oder Ende."""

    ada: Konto = Konto.objects.create_user(username="ada")
    training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
    erste: Vignette = finale_vignette(ada, name="Erste")
    zweite: Vignette = finale_vignette(ada, name="Zweite")
    training.vignette_aufnehmen(erste)
    training.vignette_aufnehmen(zweite)

    training.vignette_verschieben(erste, 9)
    nach_hinten: list[Vignette] = list(training.vignetten_in_reihenfolge())
    training.vignette_verschieben(erste, 0)

    assert [nach_hinten, list(training.vignetten_in_reihenfolge())] == [
        [zweite, erste],
        [erste, zweite],
    ]

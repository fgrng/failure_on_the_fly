"""ORM-nahe Tests der persistierten Sitzung."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
    Vignettenposition,
)
from vignetten.models import Vignette


def _sitzung_anlegen() -> Sitzung:
    """Legt die minimale, vollständig gepinnte Sitzung für Constraint-Tests an."""

    return _sitzungen_anlegen(Teilnahme.objects.create(), 1)[0]


def _sitzungen_anlegen(teilnahme: Teilnahme, anzahl: int) -> list[Sitzung]:
    # Legt gepinnte Sitzungen einer Teilnahme an, jede mit eigener Vignette.

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    autorin: Konto = Konto.objects.create_user(username="ada")
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Test", sprachmodell="fake"
    )
    return [
        Sitzung.objects.create(
            teilnahme=teilnahme,
            vignette=Vignette.objects.anlegen(autorin),
            simulationskern=kern,
            modell_konfiguration=konfiguration,
        )
        for _ in range(anzahl)
    ]


@pytest.mark.django_db
def test_gespraechsschritt_lehnt_aeusserung_ohne_denkspur_ab() -> None:
    """Die Datenbank akzeptiert sichtbare Antworten nur mit Denkspur."""

    sitzung: Sitzung = _sitzung_anlegen()

    with pytest.raises(IntegrityError), transaction.atomic():
        Gespraechsschritt.objects.create(
            sitzung=sitzung,
            eingabe="Warum?",
            aeusserung="Weil das so ist.",
            reihenfolge=1,
        )


@pytest.mark.django_db
def test_gespraechsschritt_lehnt_denkspur_ohne_aeusserung_ab() -> None:
    """Die Datenbank akzeptiert Denkspuren nur zu sichtbaren Antworten."""

    with pytest.raises(IntegrityError), transaction.atomic():
        Gespraechsschritt.objects.create(
            sitzung=_sitzung_anlegen(),
            eingabe="Warum?",
            denkspur="Ich folge meiner Regel.",
            reihenfolge=1,
        )


@pytest.mark.django_db
def test_answerless_gespraechsschritt_ohne_fehlversuch_wird_abgelehnt() -> None:
    """Ein Abbruchschritt braucht mindestens einen gespeicherten Fehlversuch."""

    sitzung: Sitzung = _sitzung_anlegen()

    with pytest.raises(IntegrityError), transaction.atomic():
        Gespraechsschritt.objects.create(
            sitzung=sitzung,
            eingabe="Warum?",
            reihenfolge=1,
        )


@pytest.mark.django_db
def test_answerless_gespraechsschritt_mit_fehlversuch_wird_gespeichert() -> None:
    """Ein gescheiterter Antwortversuch bleibt mit seinen Fehlversuchen erhalten."""

    sitzung: Sitzung = _sitzung_anlegen()

    schritt: Gespraechsschritt = Gespraechsschritt.objects.answerless_anlegen(
        sitzung=sitzung,
        eingabe="Warum?",
        reihenfolge=1,
        fehlversuche=[
            Fehlversuch(
                grund="Formatbruch",
                rohantwort="Keine gültige Antwort",
            )
        ],
    )

    assert (schritt.denkspur, schritt.aeusserung) == (None, None)
    assert Fehlversuch.objects.filter(gespraechsschritt=schritt).count() == 1


@pytest.mark.django_db
def test_answerless_gespraechsschritt_beendet_das_diagnosegespraech() -> None:
    """Nach einem endgültig gescheiterten Schritt kann keiner mehr folgen."""

    sitzung: Sitzung = _sitzung_anlegen()
    Gespraechsschritt.objects.answerless_anlegen(
        sitzung=sitzung,
        eingabe="Warum?",
        reihenfolge=1,
        fehlversuche=[
            Fehlversuch(
                grund="Formatbruch",
                rohantwort="Keine gültige Antwort",
            )
        ],
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Gespraechsschritt.objects.create(
            sitzung=sitzung,
            eingabe="Und sonst?",
            denkspur="Ich folge meiner Regel.",
            aeusserung="Das weiß ich nicht.",
            reihenfolge=2,
        )


@pytest.mark.django_db
def test_der_letzte_fehlversuch_eines_answerless_schritts_bleibt_gespeichert() -> None:
    """Das Löschen darf keinen answerless Schritt ohne Fehlversuch hinterlassen."""

    schritt: Gespraechsschritt = Gespraechsschritt.objects.answerless_anlegen(
        sitzung=_sitzung_anlegen(),
        eingabe="Warum?",
        reihenfolge=1,
        fehlversuche=[
            Fehlversuch(
                grund="Formatbruch",
                rohantwort="Keine Antwort",
            )
        ],
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Fehlversuch.objects.get(gespraechsschritt=schritt).delete()


@pytest.mark.django_db
def test_diagnose_ist_je_sitzung_eindeutig() -> None:
    """Eine Sitzung kann genau eine freie Diagnose tragen."""

    sitzung: Sitzung = _sitzung_anlegen()
    Diagnose.objects.create(sitzung=sitzung, text="Brüche werden addiert.")

    with pytest.raises(IntegrityError), transaction.atomic():
        Diagnose.objects.create(sitzung=sitzung, text="Noch eine Diagnose.")


@pytest.mark.django_db
def test_vignettenpositionen_einer_teilnahme_sind_nach_position_geordnet() -> None:
    """Die Datenspur bewahrt die gespielte Vignetten-Reihenfolge je Teilnahme."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    erste_sitzung, zweite_sitzung = _sitzungen_anlegen(teilnahme, 2)

    Vignettenposition.objects.create(
        teilnahme=teilnahme,
        sitzung=zweite_sitzung,
        position=2,
        vignette=zweite_sitzung.vignette,
    )
    Vignettenposition.objects.create(
        teilnahme=teilnahme,
        sitzung=erste_sitzung,
        position=1,
        vignette=erste_sitzung.vignette,
    )

    assert list(
        teilnahme.vignettenpositionen.values_list("position", "sitzung", "vignette")
    ) == [
        (1, erste_sitzung.pk, erste_sitzung.vignette_id),
        (2, zweite_sitzung.pk, zweite_sitzung.vignette_id),
    ]


@pytest.mark.django_db
def test_vignettenposition_lehnt_sitzung_einer_anderen_teilnahme_ab() -> None:
    """Eine Vignettenposition bleibt bei ihrer eigenen Teilnahme."""

    fremde_sitzung: Sitzung = _sitzung_anlegen()

    with pytest.raises(ValidationError, match="anderen Teilnahme"):
        Vignettenposition.objects.create(
            teilnahme=Teilnahme.objects.create(),
            sitzung=fremde_sitzung,
            position=1,
            vignette=fremde_sitzung.vignette,
        )


@pytest.mark.django_db
def test_vignettenposition_lehnt_vignette_aus_einer_anderen_sitzung_ab() -> None:
    """Die Datenspur bewahrt die tatsächlich in der Sitzung gespielte Fassung."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    sitzung, andere_sitzung = _sitzungen_anlegen(teilnahme, 2)

    with pytest.raises(ValidationError, match="stimmt nicht mit der Sitzung"):
        Vignettenposition.objects.create(
            teilnahme=teilnahme,
            sitzung=sitzung,
            position=1,
            vignette=andere_sitzung.vignette,
        )


@pytest.mark.django_db
def test_position_ist_je_teilnahme_eindeutig() -> None:
    """Zwei Sitzungen derselben Teilnahme teilen sich keine Position."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    erste_sitzung, zweite_sitzung = _sitzungen_anlegen(teilnahme, 2)
    Vignettenposition.objects.create(
        teilnahme=teilnahme,
        sitzung=erste_sitzung,
        position=1,
        vignette=erste_sitzung.vignette,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Vignettenposition.objects.create(
            teilnahme=teilnahme,
            sitzung=zweite_sitzung,
            position=1,
            vignette=zweite_sitzung.vignette,
        )

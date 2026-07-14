"""ORM-nahe Tests der persistierten Sitzung."""

import pytest
from django.db import IntegrityError, transaction

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
)
from vignetten.models import Vignette


def _sitzung_anlegen() -> Sitzung:
    """Legt die minimale, vollständig gepinnte Sitzung für Constraint-Tests an."""

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    vignette: Vignette = Vignette.objects.anlegen(
        Konto.objects.create_user(username="ada")
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    return Sitzung.objects.create(
        teilnahme=Teilnahme.objects.create(),
        vignette=vignette,
        simulationskern=kern,
        modell_konfiguration=konfiguration,
    )


def test_teilnahme_traegt_nur_ihre_eigene_identitaet() -> None:
    """Sitzungen kennen weder Training noch Konto als Aufrufer."""

    assert [feld.name for feld in Teilnahme._meta.fields] == ["id"]


def test_sitzung_hat_die_vier_vorgegebenen_statuswerte() -> None:
    """Eine Sitzung unterscheidet laufende und ihre drei Ausgänge."""

    assert [wert for wert, _ in Sitzung.Status.choices] == [
        "laufend",
        "abgeschlossen",
        "abgebrochen",
        "gescheitert",
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

    assert schritt.denkspur is None
    assert schritt.aeusserung is None
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

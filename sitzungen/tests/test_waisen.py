"""Tests der einmaligen Auflösung liegen gebliebener laufender Sitzungen."""

from datetime import UTC, datetime

import pytest
from django.db import connection

from sitzungen.models import Sitzung, Teilnahme
from sitzungen.tests.test_models import sitzungen_anlegen
from sitzungen.waisen import waisen_aufloesen


@pytest.fixture
def ohne_constraint(db: None) -> None:
    """Erlaubt Waisen wie im Altbestand vor dem Constraint.

    SQLite ändert sein Schema transaktional; der Test rollt das Entfernen mit
    seinen Daten zurück.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            "DROP INDEX sitzungen_hoechstens_eine_laufende_sitzung_je_teilnahme"
        )


def _erstellt_am(sitzung: Sitzung, stunde: int) -> None:
    # Setzt den Beginn fest; `auto_now_add` lässt ihn beim Anlegen nicht zu.

    Sitzung.objects.filter(pk=sitzung.pk).update(
        erstellt_am=datetime(2026, 10, 1, stunde, tzinfo=UTC)
    )


def _status(*sitzungen: Sitzung) -> list[str]:
    # Liest den gespeicherten Status der Sitzungen in ihrer Reihenfolge.

    return [Sitzung.objects.get(pk=sitzung.pk).status for sitzung in sitzungen]


@pytest.mark.usefixtures("ohne_constraint")
def test_nur_die_juengste_laufende_sitzung_bleibt_laufend() -> None:
    """Mehrere Waisen einer Teilnahme: alle älteren werden abgebrochen."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    aelteste, juengste, mittlere = sitzungen_anlegen(teilnahme, 3)
    _erstellt_am(aelteste, 8)
    _erstellt_am(juengste, 12)
    _erstellt_am(mittlere, 10)

    assert waisen_aufloesen(Sitzung.objects.all()) == 2

    assert _status(aelteste, mittlere, juengste) == [
        Sitzung.Status.ABGEBROCHEN,
        Sitzung.Status.ABGEBROCHEN,
        Sitzung.Status.LAUFEND,
    ]


@pytest.mark.usefixtures("ohne_constraint")
def test_bei_gleichem_beginn_bleibt_die_hoechste_pk_laufend() -> None:
    """Gleichstand bei `erstellt_am` entscheidet die pk."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    erste, zweite = sitzungen_anlegen(teilnahme, 2)
    _erstellt_am(erste, 9)
    _erstellt_am(zweite, 9)

    waisen_aufloesen(Sitzung.objects.all())

    assert _status(erste, zweite) == [
        Sitzung.Status.ABGEBROCHEN,
        Sitzung.Status.LAUFEND,
    ]


@pytest.mark.usefixtures("ohne_constraint")
def test_teilnahmen_ohne_waisen_bleiben_unberuehrt() -> None:
    """Eine einzelne laufende Sitzung und beendete Sitzungen ändern sich nicht."""

    mit_waisen: Teilnahme = Teilnahme.objects.create()
    _, _, laufende, abgeschlossene, gescheiterte = sitzungen_anlegen(mit_waisen, 5)
    einzeln: Teilnahme = Teilnahme.objects.create()
    Sitzung.objects.filter(pk__in=[laufende.pk, abgeschlossene.pk]).update(
        teilnahme=einzeln
    )
    Sitzung.objects.filter(pk=abgeschlossene.pk).update(
        status=Sitzung.Status.ABGESCHLOSSEN
    )
    Sitzung.objects.filter(pk=gescheiterte.pk).update(
        teilnahme=Teilnahme.objects.create(), status=Sitzung.Status.GESCHEITERT
    )

    assert waisen_aufloesen(Sitzung.objects.all()) == 1

    assert _status(laufende, abgeschlossene, gescheiterte) == [
        Sitzung.Status.LAUFEND,
        Sitzung.Status.ABGESCHLOSSEN,
        Sitzung.Status.GESCHEITERT,
    ]

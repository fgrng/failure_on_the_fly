"""Tests der Exklusivität von konto-tragender und pseudonymer Bindung.

Sie liegen in `training`, weil nur diese App beide Seiten kennen darf: Die Kante
zeigt von `training` nach `erhebungen` und nie umgekehrt (ADR-0043).
"""

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from erhebungen.models import Erhebung, Erhebungsbindung, Stichprobe
from konten.models import Konto
from sitzungen.bindungen import UNVERTRAEGLICHE_BINDUNG
from sitzungen.models import Teilnahme
from training.models import Abschrift, Training, Trainingsbindung


def _stichprobe() -> Stichprobe:
    """Legt eine Stichprobe an, an der Erhebungsbindungen hängen können."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="forscherin"), name="Diagnose 2026"
    )
    return Stichprobe.objects.create(
        erhebung=erhebung, beginn=timezone.now(), ende=timezone.now()
    )


def _konto(username: str) -> Konto:
    """Liefert ein Konto, an dem eine Trainingsbindung hängen kann."""

    return Konto.objects.create_user(username=username)


@pytest.mark.django_db
def test_erhebungsteilnahme_nimmt_keine_trainingsbindung_an() -> None:
    """Die Trainingsbindung träfe sonst dieselbe Teilnahme wie das Token."""

    bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())
    konto: Konto = _konto("ada")

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        Trainingsbindung.objects.create(
            teilnahme=bindung.teilnahme,
            training=Training.objects.anlegen(konto, name="Bruchrechnung"),
            konto=konto,
        )


@pytest.mark.django_db
def test_erhebungsteilnahme_nimmt_keine_abschrift_an() -> None:
    """Die Abschrift bekommt eine eigene Teilnahme, nie die der Erhebung."""

    bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        Abschrift.objects.create(
            teilnahme=bindung.teilnahme,
            konto=_konto("ada"),
            erhebungsname="Diagnose 2026",
        )


@pytest.mark.django_db
def test_trainingsteilnahme_nimmt_keine_erhebungsbindung_an() -> None:
    """Auch die Gegenrichtung stellte den Join über zwei Kanten her."""

    konto: Konto = _konto("ada")
    teilnahme: Teilnahme = Teilnahme.objects.create()
    Trainingsbindung.objects.create(
        teilnahme=teilnahme,
        training=Training.objects.anlegen(konto, name="Bruchrechnung"),
        konto=konto,
    )

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        Erhebungsbindung.objects.create(
            teilnahme=teilnahme, stichprobe=_stichprobe(), token="ABCDEFGHJ"
        )


@pytest.mark.django_db
def test_abschriftsteilnahme_nimmt_keine_erhebungsbindung_an() -> None:
    """Die Abschrift ist konto-tragend, auch ohne Training dahinter."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    Abschrift.objects.create(
        teilnahme=teilnahme, konto=_konto("ada"), erhebungsname="Diagnose 2026"
    )

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        Erhebungsbindung.objects.create(
            teilnahme=teilnahme, stichprobe=_stichprobe(), token="ABCDEFGHJ"
        )


@pytest.mark.django_db
def test_bindungen_gleicher_art_bleiben_unberuehrt() -> None:
    """Die Prüfung trennt Konto und Token, sie zählt keine Bindungen."""

    konto: Konto = _konto("ada")
    teilnahme: Teilnahme = Teilnahme.objects.create()
    Trainingsbindung.objects.create(
        teilnahme=teilnahme,
        training=Training.objects.anlegen(konto, name="Bruchrechnung"),
        konto=konto,
    )

    Abschrift.objects.create(
        teilnahme=teilnahme, konto=konto, erhebungsname="Diagnose 2026"
    )

    assert Abschrift.objects.filter(teilnahme=teilnahme).exists()

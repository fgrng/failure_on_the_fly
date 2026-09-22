"""Tests der Exklusivität von konto-tragender und pseudonymer Bindung.

Sie liegen in `training`, weil nur diese App beide Seiten kennen darf: Die Kante
zeigt von `training` nach `erhebungen` und nie umgekehrt (ADR-0043).
"""

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from erhebungen.models import Erhebung, Erhebungsbindung, Stichprobe
from konten.models import Konto
from sitzungen.bindungen import UMHAENGEN_FEHLERMELDUNG, UNVERTRAEGLICHE_BINDUNG
from sitzungen.models import Teilnahme
from training.models import Abschrift, Training, Trainingsbindung

_ERHEBUNGSNAME: str = "Diagnose 2026"


def _teilnehmerin() -> Konto:
    """Liefert das Konto, an dem die konto-tragenden Bindungen hängen."""

    return Konto.objects.create_user(username="ada")


def _stichprobe() -> Stichprobe:
    """Legt eine Stichprobe an, an der Erhebungsbindungen hängen können."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="forscherin"), name=_ERHEBUNGSNAME
    )
    return Stichprobe.objects.create(
        erhebung=erhebung, beginn=timezone.now(), ende=timezone.now()
    )


def _trainingsbindung(teilnahme: Teilnahme, konto: Konto) -> Trainingsbindung:
    """Bindet eine Teilnahme an ein frisches Training und das Konto."""

    return Trainingsbindung.objects.create(
        teilnahme=teilnahme,
        training=Training.objects.anlegen(konto, name="Bruchrechnung"),
        konto=konto,
    )


def _abschrift(teilnahme: Teilnahme, konto: Konto) -> Abschrift:
    """Hängt eine Abschrift der Erhebung an Teilnahme und Konto."""

    return Abschrift.objects.create(
        teilnahme=teilnahme, konto=konto, erhebungsname=_ERHEBUNGSNAME
    )


def _erhebungsbindung(teilnahme: Teilnahme) -> Erhebungsbindung:
    """Bindet eine Teilnahme pseudonym an eine frische Stichprobe."""

    return Erhebungsbindung.objects.create(
        teilnahme=teilnahme, stichprobe=_stichprobe(), token="ABCDEFGHJ"
    )


@pytest.mark.django_db
def test_erhebungsteilnahme_nimmt_keine_trainingsbindung_an() -> None:
    """Die Trainingsbindung träfe sonst dieselbe Teilnahme wie das Token."""

    bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        _trainingsbindung(bindung.teilnahme, _teilnehmerin())


@pytest.mark.django_db
def test_erhebungsteilnahme_nimmt_keine_abschrift_an() -> None:
    """Die Abschrift bekommt eine eigene Teilnahme, nie die der Erhebung."""

    bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        _abschrift(bindung.teilnahme, _teilnehmerin())


@pytest.mark.django_db
def test_trainingsteilnahme_nimmt_keine_erhebungsbindung_an() -> None:
    """Auch die Gegenrichtung stellte den Join über zwei Kanten her."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    _trainingsbindung(teilnahme, _teilnehmerin())

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        _erhebungsbindung(teilnahme)


@pytest.mark.django_db
def test_abschriftsteilnahme_nimmt_keine_erhebungsbindung_an() -> None:
    """Die Abschrift ist konto-tragend, auch ohne Training dahinter."""

    teilnahme: Teilnahme = Teilnahme.objects.create()
    _abschrift(teilnahme, _teilnehmerin())

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        _erhebungsbindung(teilnahme)


@pytest.mark.django_db
def test_bindungen_gleicher_art_bleiben_unberuehrt() -> None:
    """Die Prüfung trennt Konto und Token, sie zählt keine Bindungen."""

    konto: Konto = _teilnehmerin()
    teilnahme: Teilnahme = Teilnahme.objects.create()
    _trainingsbindung(teilnahme, konto)

    _abschrift(teilnahme, konto)

    assert Abschrift.objects.filter(teilnahme=teilnahme).exists()


@pytest.mark.django_db
def test_bestehende_bindung_laesst_sich_nicht_umhaengen() -> None:
    """Das Umhängen schriebe denselben Join wie ein unverträgliches Anlegen."""

    abschrift: Abschrift = _abschrift(Teilnahme.objects.create(), _teilnehmerin())
    erhebungsbindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())

    abschrift.teilnahme = erhebungsbindung.teilnahme
    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        abschrift.save()


@pytest.mark.django_db
def test_mengen_update_haengt_keine_teilnahme_um() -> None:
    """Ein `update()` am Queryset liefe an der Prüfung der Einzelzeile vorbei."""

    _abschrift(Teilnahme.objects.create(), _teilnehmerin())
    erhebungsbindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())

    with pytest.raises(RuntimeError, match=UMHAENGEN_FEHLERMELDUNG):
        Abschrift.objects.update(teilnahme=erhebungsbindung.teilnahme)


@pytest.mark.django_db
def test_bulk_create_weist_die_unvertraegliche_bindung_ab() -> None:
    """Auch das Schreiben in Mengen läuft durch dieselbe Prüfung."""

    erhebungsbindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())

    with pytest.raises(ValidationError, match=UNVERTRAEGLICHE_BINDUNG):
        Abschrift.objects.bulk_create(
            [
                Abschrift(
                    teilnahme=erhebungsbindung.teilnahme,
                    konto=_teilnehmerin(),
                    erhebungsname=_ERHEBUNGSNAME,
                )
            ]
        )


@pytest.mark.django_db
def test_gewoehnliches_speichern_bleibt_moeglich() -> None:
    """Die schärfere Prüfung darf die eigene Zeile nicht selbst abweisen."""

    bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(_stichprobe())

    bindung.abgeschlossen_am = timezone.now()
    bindung.save(update_fields=["abgeschlossen_am"])

    bindung.refresh_from_db()
    assert bindung.abgeschlossen_am is not None

"""ORM-Tests für Erhebungen und Stichproben."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from erhebungen.models import Erhebung, Stichprobe
from konten.models import Konto
from simulation.models import ModellKonfiguration


@pytest.mark.django_db
def test_sichtbar_fuer_liefert_nur_eigene_erhebungen() -> None:
    """Forschende sehen ausschließlich ihre eigenen Erhebungen."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    eigene: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=ada)
    Erhebung.objects.create(name="Addition", eigentuemerin=grace)

    assert list(Erhebung.objects.sichtbar_fuer(ada)) == [eigene]


@pytest.mark.django_db
def test_finalisieren_pinnt_die_aktive_modell_konfiguration() -> None:
    """Finalisieren friert die aktive Modell-Konfiguration an der Erhebung ein."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)

    erhebung.finalisieren()

    assert erhebung.status == Erhebung.Status.FINAL
    assert erhebung.modell_konfiguration == konfiguration


@pytest.mark.django_db
def test_zurueckziehen_und_erneutes_finalisieren_pinnt_aktuelle_konfiguration() -> None:
    """Ein zulässiger Rückweg macht das Design wieder bearbeitbar und pinnt neu."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    erste: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erste"
    )
    zweite: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="zweite"
    )
    ModellKonfiguration.objects.aktivieren(erste)
    erhebung.finalisieren()

    erhebung.zurueckziehen()
    ModellKonfiguration.objects.aktivieren(zweite)
    erhebung.finalisieren()

    assert erhebung.status == Erhebung.Status.FINAL
    assert erhebung.modell_konfiguration == zweite


@pytest.mark.django_db
def test_zurueckziehen_ist_mit_nicht_archivierter_stichprobe_gesperrt() -> None:
    """Eine aktive Stichprobe hält die finale Erhebung fest."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)
    erhebung.finalisieren()
    Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    with pytest.raises(ValidationError, match="nicht archivierten Stichproben"):
        erhebung.zurueckziehen()


@pytest.mark.django_db
def test_archivieren_ist_waehrend_laufender_stichprobe_gesperrt() -> None:
    """Eine laufende Stichprobe verhindert das Archivieren ihrer Erhebung."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)
    erhebung.finalisieren()
    jetzt: datetime = timezone.now()
    Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=jetzt - timedelta(minutes=1),
        ende=jetzt + timedelta(minutes=1),
    )

    with pytest.raises(ValidationError, match="laufenden Stichproben"):
        erhebung.archivieren()


@pytest.mark.django_db
def test_archivieren_und_entarchivieren_bewahren_den_finalen_pin() -> None:
    """Eine archivierte Erhebung kann mit ihrem unveränderten Design zurückkehren."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)
    erhebung.finalisieren()

    erhebung.archivieren()
    erhebung.entarchivieren()

    assert erhebung.status == Erhebung.Status.FINAL
    assert erhebung.modell_konfiguration == konfiguration


@pytest.mark.django_db
def test_finale_erhebung_ist_eingefroren_und_nicht_physisch_loeschbar() -> None:
    """Finale Erhebungen können weder still geändert noch gelöscht werden."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)
    erhebung.finalisieren()

    erhebung.name = "Addition"
    with pytest.raises(ValidationError, match="eingefroren"):
        erhebung.save()
    with pytest.raises(ValidationError, match="Nur Entwürfe"):
        erhebung.delete()


@pytest.mark.django_db
def test_archivierte_erhebung_ist_auch_per_bulk_update_eingefroren() -> None:
    """Archivierte Erhebungen behalten ihr finales Design unverändert."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)
    erhebung.finalisieren()
    erhebung.archivieren()

    with pytest.raises(ValidationError, match="eingefroren"):
        Erhebung.objects.filter(pk=erhebung.pk).update(name="Addition")


@pytest.mark.django_db
def test_stichprobe_archivieren_schaltet_nur_ueber_ihre_lebenszyklus_methode() -> None:
    """Eine Stichprobe wird logisch statt physisch aus der Arbeit genommen."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    stichprobe.archivieren()

    assert stichprobe.archiviert is True


@pytest.mark.django_db
def test_stichprobe_laesst_sich_nicht_per_bulk_update_archivieren() -> None:
    """Die Archivierungs-Guards einer Stichprobe sind nicht umgehbar."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    with pytest.raises(ValidationError, match="Lebenszyklus-Methode"):
        Stichprobe.objects.filter(pk=stichprobe.pk).update(archiviert=True)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("zeitpunkt", "erwartete_phase"),
    [
        (datetime(2026, 7, 16, 8, 59), Stichprobe.Phase.VOR),
        (datetime(2026, 7, 16, 9), Stichprobe.Phase.LAUFEND),
        (datetime(2026, 7, 16, 17, 1), Stichprobe.Phase.NACH),
    ],
)
def test_phase_leitet_sich_aus_zeitraum_und_systemzeit_ab(
    zeitpunkt: datetime,
    erwartete_phase: str,
) -> None:
    """Eine Stichprobe ist vor, während oder nach ihrem Erhebungszeitraum."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.make_aware(datetime(2026, 7, 16, 9)),
        ende=timezone.make_aware(datetime(2026, 7, 16, 17)),
    )

    with patch(
        "erhebungen.models.timezone.now",
        return_value=timezone.make_aware(zeitpunkt),
    ):
        assert stichprobe.phase == erwartete_phase

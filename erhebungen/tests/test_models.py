"""ORM-Tests für Erhebungen und Stichproben."""

from datetime import datetime, timedelta
import re
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Stichprobe,
    Vignettenposition,
)
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Sitzung, Teilnahme
from vignetten.models import Vignette


def _erhebungsbindung_anlegen(
    konto: Konto, teilnahme: Teilnahme
) -> Erhebungsbindung:
    """Erstellt eine Erhebungsbindung mit der kleinsten gültigen Umgebung."""

    erhebung: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=konto)
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )
    return Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=teilnahme,
        token="2345-6789",
    )


@pytest.mark.django_db
def test_sichtbar_fuer_liefert_nur_eigene_erhebungen() -> None:
    """Forschende sehen ausschließlich ihre eigenen Erhebungen."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    eigene: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=ada)
    Erhebung.objects.create(name="Addition", eigentuemerin=grace)

    assert list(Erhebung.objects.sichtbar_fuer(ada)) == [eigene]


@pytest.mark.django_db
def test_vignettenpositionen_einer_teilnahme_sind_nach_position_geordnet() -> None:
    """Die Datenspur bewahrt die gezogene Vignetten-Reihenfolge je Teilnahme."""

    konto: Konto = Konto.objects.create_user(username="ada")
    teilnahme: Teilnahme = Teilnahme.objects.create()
    bindung: Erhebungsbindung = _erhebungsbindung_anlegen(konto, teilnahme)
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    erste_vignette: Vignette = Vignette.objects.anlegen(konto)
    zweite_vignette: Vignette = Vignette.objects.anlegen(konto)
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake"
    )
    erste_sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=teilnahme,
        vignette=erste_vignette,
        simulationskern=kern,
        modell_konfiguration=konfiguration,
    )
    zweite_sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=teilnahme,
        vignette=zweite_vignette,
        simulationskern=kern,
        modell_konfiguration=konfiguration,
    )

    Vignettenposition.objects.create(
        erhebungsbindung=bindung,
        sitzung=zweite_sitzung,
        position=2,
        vignette=zweite_vignette,
    )
    Vignettenposition.objects.create(
        erhebungsbindung=bindung,
        sitzung=erste_sitzung,
        position=1,
        vignette=erste_vignette,
    )

    assert list(
        bindung.vignettenpositionen.values_list("position", "sitzung", "vignette")
    ) == [
        (1, erste_sitzung.pk, erste_vignette.pk),
        (2, zweite_sitzung.pk, zweite_vignette.pk),
    ]


@pytest.mark.django_db
def test_vignettenposition_lehnt_sitzung_einer_anderen_teilnahme_ab() -> None:
    """Eine Vignettenposition bleibt bei ihrer eigenen Erhebungsbindung."""

    konto: Konto = Konto.objects.create_user(username="ada")
    bindung: Erhebungsbindung = _erhebungsbindung_anlegen(
        konto, Teilnahme.objects.create()
    )
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    vignette: Vignette = Vignette.objects.anlegen(konto)
    fremde_sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=Teilnahme.objects.create(),
        vignette=vignette,
        simulationskern=kern,
        modell_konfiguration=ModellKonfiguration.objects.create(sprachmodell="fake"),
    )

    with pytest.raises(ValidationError, match="anderen Teilnahme"):
        Vignettenposition.objects.create(
            erhebungsbindung=bindung,
            sitzung=fremde_sitzung,
            position=1,
            vignette=vignette,
        )


@pytest.mark.django_db
def test_vignettenposition_lehnt_vignette_aus_einer_anderen_sitzung_ab() -> None:
    """Die Datenspur bewahrt die tatsächlich in der Sitzung gezogene Fassung."""

    konto: Konto = Konto.objects.create_user(username="ada")
    teilnahme: Teilnahme = Teilnahme.objects.create()
    bindung: Erhebungsbindung = _erhebungsbindung_anlegen(konto, teilnahme)
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    sitzungs_vignette: Vignette = Vignette.objects.anlegen(konto)
    andere_vignette: Vignette = Vignette.objects.anlegen(konto)
    sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=teilnahme,
        vignette=sitzungs_vignette,
        simulationskern=kern,
        modell_konfiguration=ModellKonfiguration.objects.create(sprachmodell="fake"),
    )

    with pytest.raises(ValidationError, match="stimmt nicht mit der Sitzung"):
        Vignettenposition.objects.create(
            erhebungsbindung=bindung,
            sitzung=sitzung,
            position=1,
            vignette=andere_vignette,
        )


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
def test_erhebungsbindung_verbindet_stichprobe_mit_genau_einer_teilnahme() -> None:
    """Eine Erhebungsbindung ist die einzige Erhebungszuordnung einer Teilnahme."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )
    teilnahme: Teilnahme = Teilnahme.objects.create()

    bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=teilnahme,
        token="2345-6789",
    )

    assert (bindung.stichprobe, bindung.teilnahme) == (stichprobe, teilnahme)


@pytest.mark.django_db
def test_anlegen_vergibt_lesbare_eindeutige_teilnahme_tokens() -> None:
    """Neue Erhebungsteilnahmen erhalten unterscheidbare Tokens ohne 0, 1, I oder O."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    erste: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)
    zweite: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)

    assert re.fullmatch(
        r"[23456789ABCDEFGHJKMNPQRSTVWXYZ]{4}-[23456789ABCDEFGHJKMNPQRSTVWXYZ]{4}",
        erste.token,
    )
    assert erste.token != zweite.token


@pytest.mark.django_db
def test_anlegen_wiederholt_token_nach_kollision() -> None:
    """Eine vorhandene Tokenfolge wird nie einer zweiten Teilnahme zugeordnet."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )
    Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=Teilnahme.objects.create(),
        token="2345-6789",
    )

    with patch(
        "erhebungen.models.choice",
        side_effect=[*"23456789", *"ABCDEFGH"],
    ):
        bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)

    assert bindung.token == "ABCD-EFGH"


@pytest.mark.django_db
def test_unfertige_teilnahme_verfaellt_nach_ende_des_erhebungszeitraums() -> None:
    """Eine noch nicht beendete Teilnahme kann nach dem Fenster nicht fortgesetzt werden."""

    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche", eigentuemerin=Konto.objects.create_user(username="ada")
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.make_aware(datetime(2026, 7, 16, 9)),
        ende=timezone.make_aware(datetime(2026, 7, 16, 17)),
    )
    bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=Teilnahme.objects.create(),
        token="2345-6789",
    )

    with patch(
        "erhebungen.models.timezone.now",
        return_value=timezone.make_aware(datetime(2026, 7, 16, 17, 1)),
    ):
        assert bindung.verfallen


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

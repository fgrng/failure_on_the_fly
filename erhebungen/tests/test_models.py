"""ORM-Tests für Erhebungen und Stichproben."""

from datetime import datetime
import re
from unittest.mock import patch

import pytest
from django.utils import timezone

from erhebungen.models import Erhebung, Erhebungsbindung, Stichprobe
from konten.models import Konto
from sitzungen.models import Teilnahme


@pytest.mark.django_db
def test_sichtbar_fuer_liefert_nur_eigene_erhebungen() -> None:
    """Forschende sehen ausschließlich ihre eigenen Erhebungen."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    eigene: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=ada)
    Erhebung.objects.create(name="Addition", eigentuemerin=grace)

    assert list(Erhebung.objects.sichtbar_fuer(ada)) == [eigene]


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

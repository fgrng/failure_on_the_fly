"""Unit-Tests für den sequenzierten Erhebungsablauf."""

import pytest
from django.utils import timezone

from erhebungen.ablauf import naechster_schritt
from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsvignette,
    Stichprobe,
    Vignettenziehung,
)
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Sitzung, Teilnahme
from vignetten.models import Vignette


def _finale_vignette_anlegen(konto: Konto) -> Vignette:
    """Legt eine für die Erhebung einbindbare Vignetten-Fassung an."""

    vignette: Vignette = Vignette.objects.anlegen(konto)
    vignette.fehlermuster_beschreibung = "Zähler und Nenner addieren"
    vignette.lernauftrag = "Addiere die Brüche."
    vignette.arbeitsheft_beschreibung = "Falsche Bruchrechnung"
    vignette.arbeitsheft_text = "1/2 + 1/3 = 2/5"
    vignette.schuelerin_name = "Lea"
    vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.lehrperson_name = "Ada"
    vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.fach = "Mathematik"
    vignette.thema = "Bruchrechnung"
    vignette.klassenstufe = "6"
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 3
    vignette.save()
    vignette.finalisieren()
    return vignette


@pytest.mark.django_db
def test_feste_reihenfolge_setzt_mit_der_naechsten_ungespielten_vignette_fort() -> None:
    """Der Ablauf folgt der konfigurierten Ordnung und endet nach allen Sitzungen."""

    konto: Konto = Konto.objects.create_user(username="ada")
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    erhebung: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=konto)
    erste: Vignette = _finale_vignette_anlegen(konto)
    zweite: Vignette = _finale_vignette_anlegen(konto)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=erste, position=1)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=zweite, position=2)
    bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
        stichprobe=Stichprobe.objects.create(
            erhebung=erhebung, beginn=timezone.now(), ende=timezone.now()
        ),
        teilnahme=Teilnahme.objects.create(),
        token="2345-6789",
    )

    assert naechster_schritt(bindung.teilnahme) == erste

    Sitzung.objects.create(
        teilnahme=bindung.teilnahme,
        vignette=erste,
        simulationskern=kern,
        modell_konfiguration=ModellKonfiguration.objects.create(sprachmodell="fake"),
    )

    assert naechster_schritt(bindung.teilnahme) == zweite

    Sitzung.objects.create(
        teilnahme=bindung.teilnahme,
        vignette=zweite,
        simulationskern=kern,
        modell_konfiguration=ModellKonfiguration.objects.create(sprachmodell="fake"),
    )

    assert naechster_schritt(bindung.teilnahme) is None


@pytest.mark.django_db
def test_zufaellige_ziehung_ist_mit_gespeichertem_seed_reproduzierbar() -> None:
    """Die Datenspur hält die einmal gezogene Zufallsreihenfolge fest."""

    konto: Konto = Konto.objects.create_user(username="ada")
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    erhebung: Erhebung = Erhebung.objects.create(
        name="Brüche",
        eigentuemerin=konto,
        randomisierung=Erhebung.Randomisierung.ZUFAELLIG,
    )
    vignetten: list[Vignette] = [_finale_vignette_anlegen(konto) for _ in range(3)]
    for vignette in vignetten:
        Erhebungsvignette.objects.create(erhebung=erhebung, vignette=vignette)
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung, beginn=timezone.now(), ende=timezone.now()
    )
    erste_bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=Teilnahme.objects.create(),
        token="2345-6789",
        randomisierungs_seed=17,
    )
    zweite_bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=Teilnahme.objects.create(),
        token="3456-789A",
        randomisierungs_seed=17,
    )

    naechster_schritt(erste_bindung.teilnahme)
    naechster_schritt(zweite_bindung.teilnahme)

    assert list(
        erste_bindung.vignettenziehungen.values_list("vignette_id", flat=True)
    ) == list(zweite_bindung.vignettenziehungen.values_list("vignette_id", flat=True))
    assert Vignettenziehung.objects.filter(erhebungsbindung=erste_bindung).count() == 3

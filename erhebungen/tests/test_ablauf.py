"""Unit-Tests für den sequenzierten Erhebungsablauf."""

import pytest
from django.utils import timezone

from erhebungen.ablauf import (
    Ende,
    LaufendeSitzung,
    NaechsteVignette,
    NochNichtBegonnen,
    OffenerAbschlussblock,
    OffenerSitzungsblock,
    bindung_abschliessen,
    block_erledigen,
    block_vorlegen,
    naechster_schritt,
    vignette_beginnen,
    ziehung_festschreiben,
)
from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsitem,
    Erhebungsvignette,
    ItemAntwort,
    Itemblock,
    Stichprobe,
    Vignettenposition,
    Vignettenziehung,
)
from konten.models import Konto
from fragebogen_items.models import FragebogenItem
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Sitzung, Teilnahme
from vignetten.models import Vignette


def _finaler_kern() -> Simulationskern:
    """Liefert den finalen Simulationskern und legt ihn beim ersten Aufruf an."""

    vorhandener: Simulationskern | None = Simulationskern.objects.filter(
        zustand=Simulationskern.Zustand.FINAL
    ).first()
    if vorhandener is not None:
        return vorhandener
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    return kern


def _finale_vignette_anlegen(konto: Konto) -> Vignette:
    """Legt eine für die Erhebung einbindbare Vignetten-Fassung an."""

    _finaler_kern()  # Vignette.objects.anlegen pinnt den aktuellen finalen Kern.
    vignette: Vignette = Vignette.objects.anlegen(konto)
    vignette.fehlermuster_beschreibung = "Zähler und Nenner addieren"
    vignette.lernauftrag_text = "Addiere die Brüche."
    vignette.arbeitsheft_bildbeschreibung = "Falsche Bruchrechnung"
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


def _finales_item_anlegen(konto: Konto) -> FragebogenItem:
    """Legt eine einbindbare Freitext-Item-Fassung an."""

    item = FragebogenItem.objects.anlegen(konto, wortlaut="Wie war die Sitzung?")
    item.finalisieren()
    return item


def _spielbarer_entwurf_anlegen(konto: Konto) -> Erhebung:
    """Legt den Entwurf an, dessen Sitzungen sich nach dem Finalisieren starten lassen."""

    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    ModellKonfiguration.objects.aktivieren(
        ModellKonfiguration.objects.create(sprachmodell="fake")
    )
    return erhebung


def _bindung_anlegen(erhebung: Erhebung) -> Erhebungsbindung:
    """Bindet eine frische Teilnahme an eine eigene Stichprobe der Erhebung."""

    return Erhebungsbindung.objects.create(
        stichprobe=Stichprobe.objects.create(
            erhebung=erhebung, beginn=timezone.now(), ende=timezone.now()
        ),
        teilnahme=Teilnahme.objects.create(),
        token="2345-6789",
    )


def _sitzung_anlegen(
    bindung: Erhebungsbindung,
    vignette: Vignette,
    kern: Simulationskern,
    status: str = Sitzung.Status.ABGESCHLOSSEN,
) -> Sitzung:
    """Hält eine gespielte Vignettensitzung dieser Teilnahme fest."""

    return Sitzung.objects.create(
        teilnahme=bindung.teilnahme,
        vignette=vignette,
        simulationskern=kern,
        modell_konfiguration=ModellKonfiguration.objects.create(sprachmodell="fake"),
        status=status,
    )


@pytest.mark.django_db
def test_feste_reihenfolge_setzt_mit_der_naechsten_ungespielten_vignette_fort() -> None:
    """Der Ablauf folgt der konfigurierten Ordnung und endet nach allen Sitzungen."""

    konto: Konto = Konto.objects.create_user(username="ada")
    kern: Simulationskern = _finaler_kern()
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    erste: Vignette = _finale_vignette_anlegen(konto)
    zweite: Vignette = _finale_vignette_anlegen(konto)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=erste, position=1)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=zweite, position=2)
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)
    ziehung_festschreiben(bindung)

    assert naechster_schritt(bindung) == NochNichtBegonnen()

    _sitzung_anlegen(bindung, erste, kern)

    assert naechster_schritt(bindung) == NaechsteVignette(zweite)

    _sitzung_anlegen(bindung, zweite, kern)

    assert naechster_schritt(bindung) == Ende()


@pytest.mark.django_db
def test_ablauf_liefert_nach_den_vignetten_den_geordneten_abschluss_block() -> None:
    """Am Ende folgt ein Block aus den zugeordneten Abschluss-Items."""

    konto: Konto = Konto.objects.create_user(username="ada")
    kern: Simulationskern = _finaler_kern()
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    vignette: Vignette = _finale_vignette_anlegen(konto)
    item: FragebogenItem = _finales_item_anlegen(konto)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=vignette, position=1)
    zugehoerigkeit: Erhebungsitem = Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)
    ziehung_festschreiben(bindung)
    _sitzung_anlegen(bindung, vignette, kern)

    assert naechster_schritt(bindung) == OffenerAbschlussblock()

    erste_vorlage: Itemblock | None = block_vorlegen(
        bindung, Erhebungsitem.Andockpunkt.AM_ENDE
    )
    zweite_vorlage: Itemblock | None = block_vorlegen(
        bindung, Erhebungsitem.Andockpunkt.AM_ENDE
    )

    assert erste_vorlage is not None
    assert zweite_vorlage == erste_vorlage
    assert erste_vorlage.sitzung is None
    assert [antwort.erhebungsitem for antwort in erste_vorlage.antwortzeilen()] == [
        zugehoerigkeit
    ]
    assert ItemAntwort.objects.count() == 1


@pytest.mark.django_db
def test_zufaellige_ziehung_ist_mit_gespeichertem_seed_reproduzierbar() -> None:
    """Die Datenspur hält die einmal gezogene Zufallsreihenfolge fest."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(
        konto, name="Brüche", randomisierung=Erhebung.Randomisierung.ZUFAELLIG
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

    ziehung_festschreiben(erste_bindung)
    ziehung_festschreiben(zweite_bindung)

    assert list(
        erste_bindung.vignettenziehungen.values_list("vignette_id", flat=True)
    ) == list(zweite_bindung.vignettenziehungen.values_list("vignette_id", flat=True))
    assert Vignettenziehung.objects.filter(erhebungsbindung=erste_bindung).count() == 3


@pytest.mark.django_db
def test_kommandos_bleiben_beim_zweiten_aufruf_bei_ihrem_ergebnis() -> None:
    """Vorlegen, Erledigen und Abschließen sind wiederholbar ohne Nebenwirkung."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    item: FragebogenItem = _finales_item_anlegen(konto)
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)

    block: Itemblock | None = block_vorlegen(bindung, Erhebungsitem.Andockpunkt.AM_ENDE)
    assert block is not None
    block_vorlegen(bindung, Erhebungsitem.Andockpunkt.AM_ENDE)
    block_erledigen(block)
    erledigt_am = block.erledigt_am
    block_erledigen(block)
    bindung_abschliessen(bindung)
    abgeschlossen_am = bindung.abgeschlossen_am
    bindung_abschliessen(bindung)

    assert Itemblock.objects.count() == 1
    assert ItemAntwort.objects.count() == 1
    assert block.erledigt_am == erledigt_am
    assert bindung.abgeschlossen_am == abgeschlossen_am
    assert naechster_schritt(bindung) == Ende()


@pytest.mark.django_db
def test_block_ohne_items_am_andockpunkt_entsteht_nicht() -> None:
    """Ohne Items an einem Andockpunkt legt das Vorlegen nichts an."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)

    assert block_vorlegen(bindung, Erhebungsitem.Andockpunkt.AM_ENDE) is None
    assert Itemblock.objects.count() == 0
    assert naechster_schritt(bindung) == NochNichtBegonnen()


@pytest.mark.django_db
def test_beendete_sitzung_stellt_ihren_block_vor_die_naechste_vignette() -> None:
    """Der Block einer beendeten Sitzung bleibt offen, bis er erledigt ist."""

    konto: Konto = Konto.objects.create_user(username="ada")
    kern: Simulationskern = _finaler_kern()
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    erste: Vignette = _finale_vignette_anlegen(konto)
    zweite: Vignette = _finale_vignette_anlegen(konto)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=erste, position=1)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=zweite, position=2)
    item: FragebogenItem = _finales_item_anlegen(konto)
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=1,
    )
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)
    ziehung_festschreiben(bindung)
    sitzung: Sitzung = _sitzung_anlegen(
        bindung, erste, kern, status=Sitzung.Status.LAUFEND
    )

    assert naechster_schritt(bindung) == LaufendeSitzung(sitzung)

    sitzung.status = Sitzung.Status.ABGESCHLOSSEN
    sitzung.save(update_fields=["status"])

    assert naechster_schritt(bindung) == OffenerSitzungsblock(sitzung)

    block: Itemblock | None = block_vorlegen(
        bindung, Erhebungsitem.Andockpunkt.NACH_SITZUNG, sitzung
    )
    assert block is not None

    assert naechster_schritt(bindung) == OffenerSitzungsblock(sitzung)

    block_erledigen(block)

    assert naechster_schritt(bindung) == NaechsteVignette(zweite)


@pytest.mark.django_db
def test_abfrage_nach_dem_naechsten_schritt_schreibt_keine_zeile() -> None:
    """Die Frage nach der Position materialisiert keine Forschungsdaten."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(
        konto, name="Brüche", randomisierung=Erhebung.Randomisierung.ZUFAELLIG
    )
    vignette: Vignette = _finale_vignette_anlegen(konto)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=vignette)
    item: FragebogenItem = _finales_item_anlegen(konto)
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)

    assert naechster_schritt(bindung) == NochNichtBegonnen()

    bindung.refresh_from_db()
    assert bindung.randomisierungs_seed is None
    assert Vignettenziehung.objects.count() == 0
    assert Vignettenposition.objects.count() == 0
    assert Itemblock.objects.count() == 0
    assert ItemAntwort.objects.count() == 0
    assert Sitzung.objects.count() == 0


@pytest.mark.django_db
def test_vignette_beginnen_schreibt_ziehung_sitzung_und_position() -> None:
    """Das Kommando beginnt die nächste gezogene Vignette an ihrer Position."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = _spielbarer_entwurf_anlegen(konto)
    erste: Vignette = _finale_vignette_anlegen(konto)
    zweite: Vignette = _finale_vignette_anlegen(konto)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=erste, position=1)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=zweite, position=2)
    erhebung.finalisieren()
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)

    sitzung: Sitzung | None = vignette_beginnen(bindung)

    assert sitzung is not None
    assert sitzung.vignette == erste
    assert naechster_schritt(bindung) == LaufendeSitzung(sitzung)
    assert list(bindung.vignettenziehungen.values_list("vignette_id", "position")) == [
        (erste.pk, 1),
        (zweite.pk, 2),
    ]
    position: Vignettenposition = Vignettenposition.objects.get()
    assert (position.sitzung, position.vignette, position.position) == (
        sitzung,
        erste,
        1,
    )


@pytest.mark.django_db
def test_zwei_aufrufe_beginnen_keine_zweite_sitzung() -> None:
    """Der zweite Aufruf bleibt bei der laufenden Sitzung der Erhebungsbindung."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = _spielbarer_entwurf_anlegen(konto)
    erste: Vignette = _finale_vignette_anlegen(konto)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=erste, position=1)
    erhebung.finalisieren()
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)

    erste_sitzung: Sitzung | None = vignette_beginnen(bindung)
    zweite_sitzung: Sitzung | None = vignette_beginnen(bindung)

    assert erste_sitzung == zweite_sitzung
    assert Sitzung.objects.count() == 1
    assert Vignettenposition.objects.count() == 1


@pytest.mark.django_db
def test_ziehung_bleibt_nach_dem_ersten_festschreiben_unveraendert() -> None:
    """Die Randomisierungsreihenfolge entsteht genau einmal."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(
        konto, name="Brüche", randomisierung=Erhebung.Randomisierung.ZUFAELLIG
    )
    for _ in range(4):
        Erhebungsvignette.objects.create(
            erhebung=erhebung, vignette=_finale_vignette_anlegen(konto)
        )
    bindung: Erhebungsbindung = _bindung_anlegen(erhebung)

    ziehung_festschreiben(bindung)
    gezogen: list[tuple[int, int]] = list(
        bindung.vignettenziehungen.values_list("vignette_id", "position")
    )
    bindung.refresh_from_db()
    seed: int | None = bindung.randomisierungs_seed
    ziehung_festschreiben(bindung)

    bindung.refresh_from_db()
    assert bindung.randomisierungs_seed == seed
    assert (
        list(bindung.vignettenziehungen.values_list("vignette_id", "position"))
        == gezogen
    )
    assert Vignettenziehung.objects.count() == 4

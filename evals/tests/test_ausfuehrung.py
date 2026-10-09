"""Die Einstiegsfunktion „Evallauf ausführen“ mit drei Fake-Konfigurationen."""

import pytest

from config.tests.aufbau import (
    finale_vignette,
    finaler_kern,
    konto_mit_rollen,
    vignetten_entwurf,
)
from config.tests.sprachmodell import anfragen_aufzeichnen
from evals.ausfuehrung import evallauf_ausfuehren
from evals.models import Evallauf, Zelle
from evals.tests.aufbau import (
    aeusserungen,
    antworten,
    drei_fakes,
    finaler_katalog,
    gelenkt,
    urteile,
)
from sitzungen.models import Sitzung, Teilnahme
from vignetten.models import Vignette


def _ausgefuehrter_lauf(vignette: Vignette) -> Evallauf:
    # Löst den Lauf aus, führt ihn aus und liest ihn frisch.

    lauf: Evallauf = Evallauf.objects.ausloesen(vignette)
    evallauf_ausfuehren(lauf)
    return Evallauf.objects.get(pk=lauf.pk)


def _zellen(lauf: Evallauf) -> dict[str, tuple[int, int, bool]]:
    # Die Zellen des einzigen Evalinputs: Kriterium -> (erfüllt, k, bestanden).

    zellen: list[Zelle] = lauf.uebersicht()[0].zeilen[0].zellen
    return {
        zelle.kriterium: (zelle.erfuellt, zelle.k, zelle.bestanden) for zelle in zellen
    }


@pytest.mark.django_db
def test_voller_lauf_zeigt_quote_und_bestehen_je_kriterium() -> None:
    """2 von 3 besteht nicht, nur 3 von 3 besteht; Übergreifendes gilt mit."""

    finaler_katalog(k=3)
    drei_fakes(
        schuelerin=antworten(6),
        # Je Gespräch erst das Evalkriterium, dann das übergreifende.
        bewerter=urteile(True, True, False, True, True, True),
    )
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    lauf: Evallauf = _ausgefuehrter_lauf(vignette)

    assert _zellen(lauf) == {
        "Muster gezeigt": (2, 3, False),
        "Rollentreue": (3, 3, True),
    }


@pytest.mark.django_db
def test_je_wiederholung_ein_gespraech_mit_einem_wechsel_je_inputschritt() -> None:
    """Evalinputs mal k Gespräche, jedes so lang wie sein Evalinput."""

    finaler_katalog(k=2, schritte=("Eins", "Zwei", "Drei"))
    drei_fakes(schuelerin=antworten(6), bewerter=urteile(*[True] * 4))
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    lauf: Evallauf = _ausgefuehrter_lauf(vignette)

    assert [
        (
            gespraech.wiederholung,
            [w.lehrperson_aeusserung for w in gespraech.wechsel.all()],
        )
        for gespraech in lauf.gespraeche.order_by("wiederholung")
    ] == [(1, ["Eins", "Zwei", "Drei"]), (2, ["Eins", "Zwei", "Drei"])]


def _anfragetexte(vignette: Vignette) -> list[str]:
    # Führt einen Lauf aus; je Anbieter-Anfrage alle Nachrichten als ein Text.

    with anfragen_aufzeichnen() as anfragen:
        _ausgefuehrter_lauf(vignette)
    return [
        " ".join(nachricht["content"] for nachricht in anfrage) for anfrage in anfragen
    ]


@pytest.fixture
def zwei_schritte_ein_kriterium() -> None:
    """Ein Gespräch aus zwei festen Schritten, beurteilt nach einem Kriterium."""

    finaler_katalog(k=1, uebergreifende=())
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True))


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_schritte_ein_kriterium")
def test_schuelerin_sieht_ihre_fruehere_antwort_ohne_denkspur() -> None:
    """Der zweite Antwortversuch kennt die Äußerung, nicht die Denkspur."""

    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    _, zweite_schuelerin, _ = _anfragetexte(vignette)

    assert ("Antwort 1" in zweite_schuelerin, "Denkspur 1" in zweite_schuelerin) == (
        True,
        False,
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_schritte_ein_kriterium")
def test_bewerter_sieht_verlauf_samt_denkspur_und_kriterium() -> None:
    """Der Bewerter beurteilt das ganze Gespräch nach dem Kriteriumstext."""

    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    *_, bewerter = _anfragetexte(vignette)

    assert all(
        text in bewerter for text in ("Denkspur 1", "Denkspur 2", "Muster gezeigt")
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_schritte_ein_kriterium")
def test_referenzdiagnose_erreicht_keinen_modellaufruf() -> None:
    """Weder Schüler:in noch Bewerter sehen die Referenzdiagnose."""

    vignette: Vignette = finale_vignette(
        konto_mit_rollen("ada", "Autor:in"), referenzdiagnose="GEHEIME DIAGNOSE"
    )

    texte: list[str] = _anfragetexte(vignette)

    assert all("GEHEIME DIAGNOSE" not in text for text in texte)


@pytest.mark.django_db
def test_gescheiterte_schuelerin_macht_jedes_kriterium_nicht_erfuellt() -> None:
    """Das Gespräch endet am gescheiterten Schritt, ohne den Bewerter zu fragen."""

    finaler_katalog(k=1)
    drei_fakes(schuelerin=[{"fehler": "anbieterfehler"}] * 3)
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    lauf: Evallauf = _ausgefuehrter_lauf(vignette)

    gespraech = lauf.gespraeche.get()
    assert [(w.aeusserung, len(w.fehlversuche)) for w in gespraech.wechsel.all()] == [
        (None, 3)
    ]
    assert (
        sorted(
            (urteil.erfuellt, urteil.begruendung) for urteil in gespraech.urteile.all()
        )
        == [(False, "Antwortversuch gescheitert")] * 2
    )


@pytest.mark.django_db
def test_versagender_bewerter_laesst_das_kriterium_ohne_urteil() -> None:
    """Ohne Urteil zählt nicht als erfüllt und schließt das Bestehen aus."""

    finaler_katalog(k=1)
    drei_fakes(
        schuelerin=antworten(2),
        bewerter=[{"fehler": "formatbruch"}] * 3 + urteile(True),
    )
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    lauf: Evallauf = _ausgefuehrter_lauf(vignette)

    zellen: list[Zelle] = lauf.uebersicht()[0].zeilen[0].zellen
    assert [(z.erfuellt, z.ohne_urteil, z.bestanden) for z in zellen] == [
        (0, 1, False),
        (1, 0, True),
    ]


@pytest.mark.django_db
def test_gemischter_evalinput_laeuft_mit_wiederholungen_vollstaendig_durch() -> None:
    """Feste Schritte wörtlich, gelenkte von der Lehrperson, in Inputreihenfolge."""

    finaler_katalog(k=2, schritte=("Fest eins", gelenkt("Frag nach"), "Fest zwei"))
    drei_fakes(
        schuelerin=antworten(6),
        bewerter=urteile(*[True] * 4),
        lehrperson=aeusserungen(2),
    )
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    lauf: Evallauf = _ausgefuehrter_lauf(vignette)

    assert [
        [w.lehrperson_aeusserung for w in gespraech.wechsel.all()]
        for gespraech in lauf.gespraeche.order_by("wiederholung")
    ] == [
        ["Fest eins", "Gelenkte Frage 1", "Fest zwei"],
        ["Fest eins", "Gelenkte Frage 2", "Fest zwei"],
    ]
    assert _zellen(lauf) == {
        "Muster gezeigt": (2, 2, True),
        "Rollentreue": (2, 2, True),
    }


@pytest.fixture
def gelenkt_nach_festem_schritt() -> None:
    """Ein fester, dann ein gelenkter Schritt, beurteilt nach einem Kriterium."""

    finaler_katalog(
        k=1,
        schritte=("Wie hast du gerechnet?", gelenkt("Frag nach $schuelerin_name")),
        uebergreifende=(),
    )
    drei_fakes(
        schuelerin=antworten(2), bewerter=urteile(True), lehrperson=aeusserungen(1)
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("gelenkt_nach_festem_schritt")
def test_lehrperson_sieht_den_bisherigen_verlauf_ohne_denkspur() -> None:
    """Die Lehrperson kennt Frage und Antwort, nicht die Denkspur."""

    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    _, lehrperson, _, _ = _anfragetexte(vignette)

    assert (
        "Wie hast du gerechnet?" in lehrperson,
        "Antwort 1" in lehrperson,
        "Denkspur 1" in lehrperson,
    ) == (True, True, False)


@pytest.mark.django_db
@pytest.mark.usefixtures("gelenkt_nach_festem_schritt")
def test_lehrperson_erhaelt_ihre_vorlage_mit_strategie_als_reinem_text() -> None:
    """Die Vorlage wird gerendert, die Strategie darin nicht noch einmal."""

    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    _, lehrperson, _, _ = _anfragetexte(vignette)

    assert "Sprich mit Lea nach Frag nach $schuelerin_name." in lehrperson


@pytest.mark.django_db
@pytest.mark.usefixtures("gelenkt_nach_festem_schritt")
def test_schuelerin_und_bewerter_sehen_die_gelenkte_aeusserung() -> None:
    """Die formulierte Äußerung ist die Eingabe der Schüler:in und Teil des Verlaufs."""

    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    _, _, zweite_schuelerin, bewerter = _anfragetexte(vignette)

    assert all("Gelenkte Frage 1" in text for text in (zweite_schuelerin, bewerter))


@pytest.mark.django_db
@pytest.mark.usefixtures("gelenkt_nach_festem_schritt")
def test_referenzdiagnose_erreicht_auch_die_lehrperson_nicht() -> None:
    """Keine der drei Rollen sieht die Referenzdiagnose."""

    vignette: Vignette = finale_vignette(
        konto_mit_rollen("ada", "Autor:in"), referenzdiagnose="GEHEIME DIAGNOSE"
    )

    texte: list[str] = _anfragetexte(vignette)

    assert all("GEHEIME DIAGNOSE" not in text for text in texte)


@pytest.mark.django_db
def test_gelenkter_erster_schritt_eroeffnet_das_gespraech() -> None:
    """Auch ganz vorn spricht die Lehrperson zuerst."""

    finaler_katalog(k=1, schritte=(gelenkt("Begrüße"),), uebergreifende=())
    drei_fakes(
        schuelerin=antworten(1), bewerter=urteile(True), lehrperson=aeusserungen(1)
    )
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    lauf: Evallauf = _ausgefuehrter_lauf(vignette)

    assert [
        (w.lehrperson_aeusserung, w.aeusserung)
        for w in lauf.gespraeche.get().wechsel.all()
    ] == [("Gelenkte Frage 1", "Antwort 1")]


@pytest.mark.django_db
def test_versagende_lehrperson_beendet_das_gespraech_ohne_urteil() -> None:
    """Ein Infrastrukturfehler ist weder Erfolg noch Befund über die Vignette."""

    finaler_katalog(k=1, schritte=("Fest", gelenkt("Frag nach"), "Danach"))
    drei_fakes(schuelerin=antworten(1), lehrperson=[{"fehler": "anbieterfehler"}] * 3)
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    lauf: Evallauf = _ausgefuehrter_lauf(vignette)

    gespraech = lauf.gespraeche.get()
    assert gespraech.wechsel.count() == 1
    assert {urteil.erfuellt for urteil in gespraech.urteile.all()} == {None}


@pytest.mark.django_db
def test_nach_dem_ausloesen_gespeicherter_entwurf_aendert_den_lauf_nicht() -> None:
    """Der Lauf spielt den Stand, der beim Auslösen galt."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    finaler_kern()
    entwurf: Vignette = vignetten_entwurf(konto_mit_rollen("ada", "Autor:in"))
    entwurf.fehlermuster_beschreibung = "Alter Stand"
    entwurf.save()
    lauf: Evallauf = Evallauf.objects.ausloesen(entwurf)
    entwurf.fehlermuster_beschreibung = "Neuer Stand"
    entwurf.save()

    with anfragen_aufzeichnen() as anfragen:
        evallauf_ausfuehren(lauf)

    texte: str = " ".join(n["content"] for anfrage in anfragen for n in anfrage)
    assert "Alter Stand" in texte
    assert "Neuer Stand" not in texte


@pytest.mark.django_db
def test_evallauf_erzeugt_weder_teilnahme_noch_sitzung() -> None:
    """Evalgespräche sind keine Teilnahmedaten und erreichen keinen Export."""

    finaler_katalog(k=1)
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, True))
    vignette: Vignette = finale_vignette(konto_mit_rollen("ada", "Autor:in"))

    _ausgefuehrter_lauf(vignette)

    assert (Teilnahme.objects.count(), Sitzung.objects.count()) == (0, 0)

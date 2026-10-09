"""HTTP-Tests für Auslösen und Ansicht eines Evallaufs."""

from collections.abc import Callable

import pytest
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from config.tests.aufbau import (
    finale_vignette,
    konto_mit_rollen,
    vignetten_entwurf,
)
from config.tests.formular import submit_knoepfe, text_ohne_tags
from evals.ausfuehrung import evallauf_ausfuehren
from evals.models import Evallauf
from evals.tests.aufbau import (
    aeusserungen,
    antworten,
    drei_fakes,
    fake_aktivieren,
    finaler_katalog,
    gelenkt,
    urteile,
)
from konten.models import Konto
from simulation.models import Evalinput, Inputschritt, Verwendung
from vignetten.models import Vignette

_STARTEN: str = "Evallauf starten"


def _client(konto: Konto) -> Client:
    # Ein angemeldeter Testclient.

    client: Client = Client()
    client.force_login(konto)
    return client


def _knoepfe(antwort: HttpResponse) -> list[str]:
    # Die Beschriftungen aller Absendeknöpfe der Seite.

    return [beschriftung for beschriftung, _ in submit_knoepfe(antwort)]


def _ansicht(vignette: Vignette) -> str:
    # Die URL der Evallauf-Ansicht einer Fassung.

    return reverse("evals:evallauf", args=[vignette.pk])


def _starten(client: Client, vignette: Vignette) -> HttpResponse:
    # Startet per POST und folgt der Weiterleitung auf die Ansicht.

    return client.post(reverse("evals:starten", args=[vignette.pk]), follow=True)


@pytest.fixture
def ada() -> Konto:
    """Eine Autor:in mit eigener Vignette."""

    return konto_mit_rollen("ada", "Autor:in")


@pytest.fixture
def evals_bereit() -> None:
    """Finaler Katalog mit 3 Wiederholungen und drei belegte Verwendungen."""

    finaler_katalog(k=3)
    drei_fakes(
        schuelerin=antworten(6), bewerter=urteile(True, True, False, True, True, True)
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_ohne_lauf_bietet_die_ansicht_den_start_an(ada: Konto) -> None:
    """Eine ungeprüfte Fassung zeigt den Startknopf."""

    vignette: Vignette = vignetten_entwurf(ada)

    antwort: HttpResponse = _client(ada).get(_ansicht(vignette))

    assert _STARTEN in _knoepfe(antwort)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_start_stellt_einen_wartenden_lauf_ohne_zweite_startaktion_ein(
    ada: Konto,
) -> None:
    """Nach dem Start zeigt die Ansicht den Zustand und keinen Startknopf."""

    vignette: Vignette = vignetten_entwurf(ada)

    antwort: HttpResponse = _starten(_client(ada), vignette)

    assert Evallauf.objects.get(vignette=vignette).zustand == Evallauf.Zustand.WARTET
    assert "Wartet" in antwort.content.decode()
    assert _STARTEN not in _knoepfe(antwort)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_wartender_lauf_bietet_neuladen_statt_start(ada: Konto) -> None:
    """Aktualisiert wird durch Neuladen; die Seite darf geschlossen werden."""

    vignette: Vignette = vignetten_entwurf(ada)

    seite: str = _starten(_client(ada), vignette).content.decode()

    assert "Stand neu laden" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_konto_ohne_autorinnenrolle_erhaelt_keinen_zugriff(ada: Konto) -> None:
    """Ansicht und Start ergeben 403 für Konten ohne Autor:innen-Rolle."""

    vignette: Vignette = vignetten_entwurf(ada)
    client: Client = _client(konto_mit_rollen("tom"))

    assert (
        client.get(_ansicht(vignette)).status_code,
        client.post(reverse("evals:starten", args=[vignette.pk])).status_code,
    ) == (403, 403)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_fertiger_lauf_zeigt_quote_und_bestehen(ada: Konto) -> None:
    """Die Übersicht nennt je Zelle Quote und Bestehen zusammen."""

    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _client(ada).get(_ansicht(vignette)).content.decode()

    assert "Fertig" in seite
    assert "2 von 3 · nicht bestanden" in seite
    assert "3 von 3 · bestanden" in seite


@pytest.mark.django_db
def test_gemischter_lauf_zeigt_seine_ergebnisse(ada: Konto) -> None:
    """Feste und gelenkte Schritte laufen über den Hintergrundprozess durch."""

    finaler_katalog(k=3, schritte=("Fest", gelenkt("Frag nach"), "Danach"))
    drei_fakes(
        schuelerin=antworten(9),
        bewerter=urteile(*[True] * 6),
        lehrperson=aeusserungen(3),
    )
    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _client(ada).get(_ansicht(vignette)).content.decode()

    assert "FGF" in seite
    assert seite.count("3 von 3 · bestanden") == 2


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_ko_autorin_und_administration_duerfen_starten(ada: Konto) -> None:
    """Der Eigentümer-Kreis und die Administration, jeweils über den Startknopf."""

    grace: Konto = konto_mit_rollen("grace", "Autor:in")
    admin: Konto = konto_mit_rollen("admin", is_superuser=True)
    eigene: Vignette = vignetten_entwurf(ada)
    eigene.historie.eigentuemerinnen.add(grace)
    andere: Vignette = finale_vignette(konto_mit_rollen("lin", "Autor:in"))

    _starten(_client(grace), eigene)
    _starten(_client(admin), andere)

    assert Evallauf.objects.filter(vignette__in=[eigene, andere]).count() == 2


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_fremde_vignette_bleibt_unlesbar_und_unstartbar(ada: Konto) -> None:
    """Fremde Fassungen ergeben 404, ein Start legt nichts an."""

    fremde: Vignette = finale_vignette(konto_mit_rollen("lin", "Autor:in"))
    client: Client = _client(ada)

    assert client.get(_ansicht(fremde)).status_code == 404
    assert client.post(reverse("evals:starten", args=[fremde.pk])).status_code == 404
    assert not Evallauf.objects.exists()


@pytest.mark.django_db
def test_ohne_dritte_verwendung_gibt_es_keine_evals(ada: Konto) -> None:
    """Fehlt eine Verwendung, sind Ansicht, Start und Verlinkung weg."""

    finaler_katalog()
    fake_aktivieren(Verwendung.SCHUELERIN)
    fake_aktivieren(Verwendung.LEHRPERSON)
    vignette: Vignette = finale_vignette(ada)
    client: Client = _client(ada)

    assert client.get(_ansicht(vignette)).status_code == 404
    assert client.post(reverse("evals:starten", args=[vignette.pk])).status_code == 404
    detail: str = client.get(
        reverse("vignetten:detail", args=[vignette.pk])
    ).content.decode()
    assert _ansicht(vignette) not in detail


@pytest.mark.django_db
def test_ohne_finalen_katalog_gibt_es_keine_evals(ada: Konto) -> None:
    """Ohne finalen Evalkatalog ist die Ansicht nicht erreichbar."""

    drei_fakes()
    vignette: Vignette = finale_vignette(ada)

    assert _client(ada).get(_ansicht(vignette)).status_code == 404


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_vignettenansicht_verlinkt_den_evallauf(ada: Konto) -> None:
    """Die Vignette verlinkt ihre Evals-Ansicht samt Zustand."""

    vignette: Vignette = vignetten_entwurf(ada)
    _starten(_client(ada), vignette)

    detail: str = (
        _client(ada)
        .get(reverse("vignetten:detail", args=[vignette.pk]))
        .content.decode()
    )

    assert _ansicht(vignette) in detail
    assert "Wartet" in detail


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_zweiter_start_ersetzt_keinen_wartenden_lauf(ada: Konto) -> None:
    """Auch ein veralteter Browserstand legt keinen zweiten Lauf an."""

    vignette: Vignette = vignetten_entwurf(ada)
    client: Client = _client(ada)
    _starten(client, vignette)
    erster: Evallauf = Evallauf.objects.get()

    antwort: HttpResponse = _starten(client, vignette)

    assert list(Evallauf.objects.all()) == [erster]
    assert "wartet oder läuft bereits" in antwort.content.decode()


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_neuer_start_ersetzt_den_fertigen_lauf(ada: Konto) -> None:
    """Ein fertiger Vorgänger weicht samt seinen Gesprächen dem neuen Lauf."""

    vignette: Vignette = finale_vignette(ada)
    client: Client = _client(ada)
    _starten(client, vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    alter: Evallauf = Evallauf.objects.get()

    antwort: HttpResponse = _starten(client, vignette)

    neuer: Evallauf = Evallauf.objects.get()
    assert neuer.pk != alter.pk
    assert (neuer.zustand, neuer.gespraeche.count()) == (Evallauf.Zustand.WARTET, 0)
    assert _STARTEN not in _knoepfe(antwort)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_archivierte_fassung_ist_nicht_startbar_und_behaelt_ihren_lauf(
    ada: Konto,
) -> None:
    """Die abgewiesene Startprüfung lässt den bisherigen Lauf unberührt."""

    vignette: Vignette = finale_vignette(ada)
    client: Client = _client(ada)
    _starten(client, vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    bisheriger: Evallauf = Evallauf.objects.get()
    vignette.archivieren()

    antwort: HttpResponse = _starten(client, vignette)

    assert list(Evallauf.objects.all()) == [bisheriger]
    assert _STARTEN not in _knoepfe(antwort)
    assert "Archivierte Fassungen" in antwort.content.decode()


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_finalisieren_behaelt_den_lauf_an_derselben_fassung(ada: Konto) -> None:
    """Der Lauf des Entwurfs gilt nach dem Finalisieren für die finale Fassung."""

    entwurf: Vignette = finale_vignette(ada).bearbeiten()
    _starten(_client(ada), entwurf)
    lauf: Evallauf = Evallauf.objects.get()

    entwurf.finalisieren()

    assert Vignette.objects.get(evallauf=lauf).zustand == Vignette.Zustand.FINAL


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_loeschen_des_entwurfs_entfernt_seinen_lauf(ada: Konto) -> None:
    """Nichts verwaist, wenn der Entwurf verschwindet."""

    entwurf: Vignette = vignetten_entwurf(ada)
    _starten(_client(ada), entwurf)

    entwurf.delete()

    assert not Evallauf.objects.exists()


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_start_nur_per_post(ada: Konto) -> None:
    """Ein GET auf die Startroute legt nichts an."""

    vignette: Vignette = vignetten_entwurf(ada)

    antwort: HttpResponse = _client(ada).get(
        reverse("evals:starten", args=[vignette.pk])
    )

    assert antwort.status_code == 405
    assert not Evallauf.objects.exists()


def _abgearbeitete_ansicht(ada: Konto) -> str:
    # Startet über einer finalen Fassung, arbeitet ab und liest die Ansicht.

    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    return _client(ada).get(_ansicht(vignette)).content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("schritte", "fakes"),
    [
        (
            ("Eins", "Zwei"),
            {"schuelerin": antworten(2), "bewerter": [{"fehler": "formatbruch"}] * 3},
        ),
        (
            ("Eins", gelenkt("Frag nach")),
            {"schuelerin": antworten(1), "lehrperson": [{"fehler": "formatbruch"}] * 3},
        ),
    ],
    ids=["bewerter", "lehrperson"],
)
def test_fertiger_lauf_mit_fehlendem_urteil_ist_unvollstaendig_und_nicht_bestanden(
    ada: Konto,
    schritte: tuple[str | tuple[Inputschritt.Art, str], ...],
    fakes: dict[str, list[dict[str, object]]],
) -> None:
    """Fehlende Urteile stehen gezählt in der Zelle und schließen das Bestehen aus."""

    finaler_katalog(k=1, schritte=schritte, uebergreifende=())
    drei_fakes(**fakes)

    seite: str = _abgearbeitete_ansicht(ada)

    assert "Fertig" in seite
    assert "1 ohne Urteil" in seite
    assert "Unvollständig" in seite
    assert "Fertig · Nicht bestanden" in seite


@pytest.mark.django_db
def test_fertiger_lauf_mit_allen_urteilen_erfuellt_besteht_insgesamt(
    ada: Konto,
) -> None:
    """Nur ein vollständiger fertiger Lauf erscheint als bestanden."""

    finaler_katalog(k=1, uebergreifende=())
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True))

    seite: str = _abgearbeitete_ansicht(ada)

    assert "Fertig · Bestanden" in seite
    assert "Unvollständig" not in seite


@pytest.mark.django_db
def test_abgebrochener_lauf_zeigt_das_fertige_und_das_ausstehende(ada: Konto) -> None:
    """Erfüllte Urteile machen einen Teilstand nicht bestanden; Ausstehendes zählt."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    # Das Skript reicht nur für das erste Gespräch; das zweite bricht ab.
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))

    seite: str = _abgearbeitete_ansicht(ada)

    assert "Der Evallauf wurde abgebrochen." in seite
    assert "1 von 2" in seite
    assert "1 noch nicht ausgeführt" in seite
    assert "Fertig ·" not in seite
    assert "Unvollständig" not in seite


@pytest.mark.django_db
def test_gescheiterte_schuelerin_ist_nicht_erfuellt_statt_unvollstaendig(
    ada: Konto,
) -> None:
    """Ein endgültig gescheiterter Antwortversuch ist ein Befund, kein fehlendes Urteil."""

    finaler_katalog(k=1, uebergreifende=())
    drei_fakes(schuelerin=[{"fehler": "anbieterfehler"}] * 3)

    seite: str = _abgearbeitete_ansicht(ada)

    assert "0 von 1" in seite
    assert "Fertig · Nicht bestanden" in seite
    assert "Unvollständig" not in seite


@pytest.mark.django_db
def test_neustart_zeigt_den_verwaisten_lauf_abgebrochen_mit_dem_fertigen(
    ada: Konto,
) -> None:
    """Der Hintergrundprozess räumt beim Start auf; das Geschriebene bleibt lesbar."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    lauf: Evallauf = Evallauf.objects.get(vignette=vignette)
    # Der Prozess stirbt nach dem ersten Gespräch und lässt „Läuft“ stehen.
    with pytest.raises(IndexError):
        evallauf_ausfuehren(lauf)
    Evallauf.objects.filter(pk=lauf.pk).update(zustand=Evallauf.Zustand.LAEUFT)

    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _client(ada).get(_ansicht(vignette)).content.decode()
    assert "Der Evallauf wurde abgebrochen." in seite
    assert "1 von 2" in seite and "1 noch nicht ausgeführt" in seite


# Einsicht in die Evalgespräche: links Evalinputs, rechts das gewählte Gespräch.


def _einsicht(ada: Konto, vignette: Vignette, **auswahl: object) -> str:
    # Liest die Ansicht mit einer Auswahl aus Evalinput und Wiederholung.

    return _client(ada).get(_ansicht(vignette), auswahl).content.decode()


def _abgearbeitet(ada: Konto) -> Vignette:
    # Startet über einer finalen Fassung und arbeitet den Lauf ab.

    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    return vignette


def _evalinputs() -> list[int]:
    # Die Evalinputs des einzigen finalen Katalogs in Katalogreihenfolge.

    return list(
        Evalinput.objects.order_by("eval__position", "position").values_list(
            "pk", flat=True
        )
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_ohne_auswahl_zeigt_die_einsicht_das_erste_gespraech(ada: Konto) -> None:
    """Verlauf, Denkspur und begründete Urteile der ersten Wiederholung."""

    vignette: Vignette = _abgearbeitet(ada)

    seite: str = _einsicht(ada, vignette)

    assert "Wie hast du gerechnet?" in seite and "Warum so?" in seite
    assert "Antwort 1" in seite and "Denkspur 1" in seite
    assert "Antwort 3" not in seite
    assert "Begründung 1" in seite and "Begründung 2" in seite
    assert 'aria-current="page"' in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_gewaehlte_wiederholung_zeigt_ihr_gespraech_und_urteil(ada: Konto) -> None:
    """Die zweite Wiederholung mit ihrem nicht erfüllten Urteil samt Begründung."""

    vignette: Vignette = _abgearbeitet(ada)

    seite: str = _einsicht(ada, vignette, input=_evalinputs()[0], wiederholung=2)

    assert "Antwort 3" in seite and "Antwort 1" not in seite
    assert "Muster gezeigt · nicht erfüllt" in seite
    assert "Begründung 3" in seite
    assert '<option value="2" selected>' in seite


@pytest.mark.django_db
def test_wechsel_des_evalinputs_bleibt_in_derselben_ansicht(ada: Konto) -> None:
    """Der zweite Evalinput ist verlinkt und zeigt seine eigenen Gespräche."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=(), inputs=2)
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, False))
    vignette: Vignette = _abgearbeitet(ada)
    zweiter: int = _evalinputs()[1]

    seite: str = _einsicht(ada, vignette, input=zweiter)

    assert f'href="{_ansicht(vignette)}?input={zweiter}" aria-current="page"' in seite
    assert "Antwort 2" in seite and "Antwort 1" not in seite
    assert "Begründung 2" in seite


@pytest.mark.django_db
def test_gescheiterte_schuelerin_zeigt_fehlversuche_im_gespraech(ada: Konto) -> None:
    """Ein Wechsel ohne Antwort nennt das Scheitern und jeden Fehlversuch."""

    finaler_katalog(k=1, uebergreifende=())
    drei_fakes(schuelerin=[{"fehler": "anbieterfehler"}] * 3)
    vignette: Vignette = _abgearbeitet(ada)

    seite: str = _einsicht(ada, vignette)

    assert "Antwortversuch endgültig gescheitert" in seite
    assert "Fehlversuche · 3" in seite
    assert "Muster gezeigt · nicht erfüllt" in seite


@pytest.mark.django_db
def test_unvollstaendiger_lauf_zeigt_das_fehlende_urteil_im_gespraech(
    ada: Konto,
) -> None:
    """Ein Kriterium ohne Urteil steht als solches im Gespräch."""

    finaler_katalog(k=1, uebergreifende=())
    drei_fakes(schuelerin=antworten(2), bewerter=[{"fehler": "formatbruch"}] * 3)
    vignette: Vignette = _abgearbeitet(ada)

    seite: str = _einsicht(ada, vignette)

    assert "Muster gezeigt · ohne Urteil" in seite
    assert "Unvollständig" in seite


@pytest.mark.django_db
def test_abgebrochener_lauf_nennt_die_nicht_ausgefuehrte_wiederholung(
    ada: Konto,
) -> None:
    """Die erste Wiederholung bleibt lesbar, die zweite gibt es nicht."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    vignette: Vignette = _abgearbeitet(ada)
    evalinput: int = _evalinputs()[0]

    erste: str = _einsicht(ada, vignette, input=evalinput, wiederholung=1)
    zweite: str = _einsicht(ada, vignette, input=evalinput, wiederholung=2)

    assert "Antwort 1" in erste
    assert "Muster gezeigt · erfüllt" in erste
    assert "Antwort 1" not in zweite
    assert "Diese Wiederholung wurde nicht ausgeführt." in zweite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
@pytest.mark.parametrize(
    "auswahl",
    [{"input": "x", "wiederholung": "y"}, {"wiederholung": 99}, {"input": 0}],
    ids=["unlesbar", "wiederholung-ausserhalb", "fremder-input"],
)
def test_ungueltige_auswahl_zeigt_die_erste_wiederholung(
    ada: Konto, auswahl: dict[str, object]
) -> None:
    """Was nicht zu diesem Lauf passt, weicht der Vorgabe statt zu scheitern."""

    vignette: Vignette = _abgearbeitet(ada)

    seite: str = _einsicht(ada, vignette, **auswahl)

    assert "Antwort 1" in seite


def _neue_antworten() -> None:
    # Belegt die Verwendungen neu, sodass der nächste Lauf „Neu 1“ … antwortet.

    drei_fakes(
        schuelerin=[
            {"denkspur": f"Neue Denkspur {nummer}", "aeusserung": f"Neu {nummer}"}
            for nummer in range(1, 7)
        ],
        bewerter=urteile(*[True] * 6),
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_auswahl_erreicht_keine_gespraeche_einer_anderen_fassung(ada: Konto) -> None:
    """Derselbe Evalinput zeigt an jeder Fassung nur die Gespräche ihres Laufs."""

    _abgearbeitet(ada)
    _neue_antworten()
    andere: Vignette = vignetten_entwurf(ada)
    _starten(_client(ada), andere)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _einsicht(ada, andere, input=_evalinputs()[0], wiederholung=2)

    assert "Neu 3" in seite
    assert "Antwort 3" not in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_ersetzter_lauf_zeigt_den_aktuellen_stand(ada: Konto) -> None:
    """Eine alte Auswahl nach erneutem Prüfen zeigt das Gespräch des neuen Laufs."""

    vignette: Vignette = _abgearbeitet(ada)
    evalinput: int = _evalinputs()[0]
    _neue_antworten()
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _einsicht(ada, vignette, input=evalinput, wiederholung=2)

    assert "Neu 3" in seite
    assert "Antwort 3" not in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_abgeschlossener_lauf_steht_als_fusszeile_unter_den_ergebnissen(
    ada: Konto,
) -> None:
    """Zustand, Erneut prüfen und eingeklappte Angaben folgen dem Gespräch."""

    seite: str = _einsicht(ada, _abgearbeitet(ada))

    fuss: int = seite.index('<footer class="evallauf-fuss"')
    assert seite.index("Antwort 1") < fuss
    assert seite.index("Erneut prüfen") > fuss
    assert seite.index("<summary>Angaben zum Lauf</summary>") > fuss


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_offener_lauf_steht_oben_ohne_fusszeile(ada: Konto) -> None:
    """Wartet ein Lauf, stehen Zustand und Neuladen über den Ergebnissen."""

    vignette: Vignette = vignetten_entwurf(ada)

    seite: str = _starten(_client(ada), vignette).content.decode()

    assert '<footer class="evallauf-fuss"' not in seite
    assert "Erneut prüfen" not in seite


def _mitten_im_lauf(ada: Konto) -> Vignette:
    # Der Prozess stirbt, sobald das Skript endet, und lässt „Läuft“ stehen.

    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    lauf: Evallauf = Evallauf.objects.get(vignette=vignette)
    with pytest.raises(IndexError):
        evallauf_ausfuehren(lauf)
    Evallauf.objects.filter(pk=lauf.pk).update(zustand=Evallauf.Zustand.LAEUFT)
    return vignette


@pytest.mark.django_db
def test_abgebrochener_lauf_ohne_urteil_heisst_unvollstaendig(ada: Konto) -> None:
    """Abbruch und fehlendes Urteil stehen beide als Hinweis da."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    # Das Skript reicht nur für das erste Gespräch, dessen Urteil ausfällt.
    drei_fakes(schuelerin=antworten(1), bewerter=[{"fehler": "formatbruch"}] * 3)

    seite: str = _abgearbeitete_ansicht(ada)

    assert "Der Evallauf wurde abgebrochen." in seite
    assert "Unvollständig: Mindestens ein Kriterium blieb ohne Urteil" in seite


@pytest.mark.django_db
def test_stand_neu_laden_behaelt_die_auswahl(ada: Konto) -> None:
    """Neuladen eines laufenden Laufs bleibt beim gewählten Gespräch."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    vignette: Vignette = _mitten_im_lauf(ada)
    evalinput: int = _evalinputs()[0]

    seite: str = _einsicht(ada, vignette, input=evalinput, wiederholung=2)

    assert (
        f'href="{_ansicht(vignette)}?input={evalinput}&amp;wiederholung=2">'
        "Stand neu laden</a>"
    ) in seite


@pytest.mark.django_db
def test_gespraech_nennt_schrittart_und_art_des_kriteriums(ada: Konto) -> None:
    """Feste und gelenkte Schritte, Eval- und übergreifende Kriterien sind benannt."""

    finaler_katalog(k=1, schritte=("Eins", gelenkt("Nachfragen")))
    drei_fakes(
        schuelerin=antworten(2),
        lehrperson=aeusserungen(1),
        bewerter=urteile(True, True),
    )

    seite: str = _einsicht(ada, _abgearbeitet(ada))

    assert "Schritt 1 (fest)" in seite and "Schritt 2 (gelenkt)" in seite
    assert "Gelenkte Frage 1" in seite
    assert "Evalkriterium" in seite and "Übergreifendes Kriterium" in seite


@pytest.mark.django_db
def test_fehlversuch_zeigt_seine_rohantwort(ada: Konto) -> None:
    """Was das Modell beim Fehlversuch lieferte, steht im Gespräch."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(
        schuelerin=[
            {"fehler": "formatbruch", "rohantwort": "kein JSON"},
            *antworten(1),
        ],
        bewerter=urteile(True),
    )

    seite: str = _einsicht(ada, _abgearbeitet(ada))

    assert "Fehlversuche · 1" in seite
    assert "<pre>kein JSON</pre>" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_angaben_zum_lauf_nennen_die_drei_konfigurationen(ada: Konto) -> None:
    """Die eingeklappten Angaben nennen, womit der Lauf geprüft hat."""

    seite: str = _einsicht(ada, _abgearbeitet(ada))

    assert "<dt>Schüler:in</dt><dd>Fake Schüler:in</dd>" in seite
    assert "<dt>Lehrperson</dt><dd>Fake Lehrperson</dd>" in seite
    assert "<dt>Bewerter</dt><dd>Fake Bewerter</dd>" in seite


@pytest.mark.django_db
def test_abgebrochener_lauf_bietet_erneut_pruefen(ada: Konto) -> None:
    """Auch ein abgebrochener Lauf lässt sich von vorn prüfen."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))

    seite: str = _abgearbeitete_ansicht(ada)

    assert "Erneut prüfen" in seite


@pytest.mark.django_db
def test_laufender_lauf_nennt_die_noch_offene_wiederholung(ada: Konto) -> None:
    """Die zweite Wiederholung ist im Auswahlfeld und im Gespräch noch offen."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(True))
    vignette: Vignette = _mitten_im_lauf(ada)

    seite: str = _einsicht(ada, vignette, input=_evalinputs()[0], wiederholung=2)

    assert "Wiederholung 2 · nicht ausgeführt" in seite
    assert "Diese Wiederholung wurde noch nicht ausgeführt." in seite


@pytest.mark.django_db
def test_laufendes_gespraech_ohne_urteile_ist_noch_nicht_beurteilt(
    ada: Konto,
) -> None:
    """Ein Gespräch mitten im Lauf zeigt seine Wechsel, die Urteile stehen aus."""

    finaler_katalog(k=1, schritte=("Eins", "Zwei"), uebergreifende=())
    # Das Skript reicht nur für den ersten Schritt.
    drei_fakes(schuelerin=antworten(1))
    vignette: Vignette = _mitten_im_lauf(ada)

    seite: str = _einsicht(ada, vignette)

    assert "Antwort 1" in seite
    assert "Muster gezeigt · noch nicht beurteilt" in seite


# Veraltet und der Hinweis beim Finalisieren.


def _detail(ada: Konto, vignette: Vignette) -> str:
    # Die gerenderte Vignettenansicht der Fassung.

    return text_ohne_tags(
        _client(ada).get(reverse("vignetten:detail", args=[vignette.pk]))
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_wartender_lauf_nach_bearbeiten_heisst_veraltet_mit_grund(ada: Konto) -> None:
    """Auch ein noch offener Lauf zeigt, dass der Entwurf seitdem bearbeitet wurde."""

    vignette: Vignette = vignetten_entwurf(ada)
    _starten(_client(ada), vignette)
    vignette.thema = "Neues Thema"
    vignette.save()

    seite: str = text_ohne_tags(_client(ada).get(_ansicht(vignette)))

    assert "Evallauf Wartet · Veraltet" in seite
    assert "Seit dem Start: Vignette bearbeitet." in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_fertiger_lauf_nach_konfigurationswechsel_heisst_veraltet(ada: Konto) -> None:
    """Das Gesamtergebnis bleibt lesbar und ist als veraltet markiert."""

    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    fake_aktivieren(Verwendung.BEWERTER)

    seite: str = text_ohne_tags(_client(ada).get(_ansicht(vignette)))

    assert "Fertig · Nicht bestanden · Veraltet" in seite
    assert "Seit dem Start: Konfiguration Bewerter gewechselt." in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_unveraenderter_lauf_heisst_nicht_veraltet_und_nennt_seinen_stand(
    ada: Konto,
) -> None:
    """Die Angaben zum Lauf nennen den geprüften Stand der Vignette."""

    vignette: Vignette = finale_vignette(ada)
    _starten(_client(ada), vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = text_ohne_tags(_client(ada).get(_ansicht(vignette)))

    assert "Veraltet" not in seite
    assert "Geprüfter Stand der Vignette" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_finalisieren_hinweis_ohne_lauf(ada: Konto) -> None:
    """Ohne Lauf nennt der Hinweis das und lässt das Finalisieren stehen."""

    vignette: Vignette = vignetten_entwurf(ada)

    antwort: HttpResponse = _client(ada).get(
        reverse("vignetten:detail", args=[vignette.pk])
    )

    assert "Vor dem Finalisieren: Noch kein Evallauf." in text_ohne_tags(antwort)
    assert "Finalisieren" in _knoepfe(antwort)


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_finalisieren_hinweis_nennt_ergebnis_und_quoten(ada: Konto) -> None:
    """Ein fertiger Lauf erscheint mit Gesamtergebnis und den Quoten je Kriterium."""

    entwurf: Vignette = finale_vignette(ada).bearbeiten()
    _starten(_client(ada), entwurf)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _detail(ada, entwurf)

    assert "Vor dem Finalisieren: Evallauf Fertig · Nicht bestanden." in seite
    assert "Muster · Evalinput 1: Muster gezeigt 2 von 3, Rollentreue 3 von 3" in seite


@pytest.mark.django_db
def test_finalisieren_hinweis_nennt_bestanden(ada: Konto) -> None:
    """Erfüllt jedes Urteil, nennt der Hinweis den Lauf bestanden."""

    finaler_katalog(k=1)
    drei_fakes(schuelerin=antworten(2), bewerter=urteile(True, True))
    entwurf: Vignette = finale_vignette(ada).bearbeiten()
    _starten(_client(ada), entwurf)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _detail(ada, entwurf)

    assert "Vor dem Finalisieren: Evallauf Fertig · Bestanden." in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_vignettenansicht_nennt_den_veralteten_lauf(ada: Konto) -> None:
    """Auch die Zustandszeile der Vignette ergänzt den Zustand um veraltet."""

    vignette: Vignette = vignetten_entwurf(ada)
    _starten(_client(ada), vignette)
    vignette.save()

    seite: str = _detail(ada, vignette)

    assert "Evallauf: Wartet · veraltet · Evals ansehen" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("evals_bereit")
def test_finalisieren_hinweis_nennt_veraltet(ada: Konto) -> None:
    """Ein nach dem Start bearbeiteter Entwurf zeigt den veralteten Lauf."""

    entwurf: Vignette = finale_vignette(ada).bearbeiten()
    _starten(_client(ada), entwurf)
    call_command("evallaeufe_abarbeiten", "--einmal")
    entwurf.thema = "Neues Thema"
    entwurf.save()

    seite: str = _detail(ada, entwurf)

    assert "· Veraltet (Vignette bearbeitet)." in seite


@pytest.mark.django_db
def test_finalisieren_hinweis_nennt_teil_und_fehlerzustaende(ada: Konto) -> None:
    """Abbruch, fehlende Urteile und nicht Ausgeführtes bleiben erkennbar."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    # Das zweite Gespräch bricht ab; das erste bleibt ohne Urteil.
    drei_fakes(schuelerin=antworten(1), bewerter=[{"fehler": "formatbruch"}] * 3)
    entwurf: Vignette = finale_vignette(ada).bearbeiten()
    _starten(_client(ada), entwurf)
    call_command("evallaeufe_abarbeiten", "--einmal")

    seite: str = _detail(ada, entwurf)

    assert "Vor dem Finalisieren: Evallauf Abgebrochen · Unvollständig." in seite
    assert "Muster gezeigt 0 von 2 (1 ohne Urteil, 1 noch nicht ausgeführt)" in seite


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ausgang", ["wartet", "laeuft", "abgebrochen", "veraltet", "fertig"]
)
@pytest.mark.usefixtures("evals_bereit")
def test_finalisieren_bleibt_in_jedem_laufzustand_erlaubt(
    ada: Konto, ausgang: str
) -> None:
    """Der Hinweis sperrt nicht: Der Entwurf wird über die Route final."""

    entwurf: Vignette = finale_vignette(ada).bearbeiten()
    _starten(_client(ada), entwurf)
    if ausgang in ("laeuft", "abgebrochen"):
        # Ein stehengebliebenes „Läuft“ bricht der nächste Prozessstart ab.
        Evallauf.objects.filter(vignette=entwurf).update(
            zustand=Evallauf.Zustand.LAEUFT
        )
    if ausgang in ("abgebrochen", "veraltet", "fertig"):
        call_command("evallaeufe_abarbeiten", "--einmal")
    if ausgang == "veraltet":
        entwurf.save()

    _client(ada).post(reverse("vignetten:finalisieren", args=[entwurf.pk]))

    lauf: Evallauf = Evallauf.objects.get(vignette=entwurf)
    assert lauf.vignette.zustand == Vignette.Zustand.FINAL
    assert lauf.veraltet == (ausgang == "veraltet")


def _ohne_dritte_verwendung() -> None:
    # Finaler Katalog, aber der Bewerter ist nicht belegt.

    finaler_katalog()
    fake_aktivieren(Verwendung.SCHUELERIN)
    fake_aktivieren(Verwendung.LEHRPERSON)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "einrichten",
    [_ohne_dritte_verwendung, drei_fakes],
    ids=["ohne_verwendung", "ohne_finalen_katalog"],
)
def test_ohne_evals_fehlt_der_finalisieren_hinweis(
    ada: Konto, einrichten: Callable[[], object]
) -> None:
    """Ohne finalen Katalog oder alle drei Verwendungen fehlen Evals und Hinweis."""

    einrichten()

    seite: str = _detail(ada, vignetten_entwurf(ada))

    assert "Vor dem Finalisieren" not in seite
    assert "Evallauf" not in seite

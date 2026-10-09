"""Manuelle Korrektur von Bewerterurteilen: Rechte, Grenzen und Ergebnisse."""

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen
from config.tests.formular import submit_knoepfe, text_ohne_tags
from evals.ausfuehrung import evallauf_ausfuehren
from evals.models import Evallauf, Urteil
from evals.tests.aufbau import antworten, drei_fakes, finaler_katalog, urteile
from konten.models import Konto
from vignetten.models import Vignette


def _client(konto: Konto) -> Client:
    # Ein angemeldeter Testclient.

    client: Client = Client()
    client.force_login(konto)
    return client


def _abgearbeitet(konto: Konto, vignette: Vignette | None = None) -> Vignette:
    # Löst über einer Fassung (Vorgabe: neuer finaler Entwurf) aus und arbeitet ab.

    vignette = vignette or finale_vignette(konto).bearbeiten()
    Evallauf.objects.ausloesen(vignette)
    call_command("evallaeufe_abarbeiten", "--einmal")
    return vignette


def _urteil(wiederholung: int) -> Urteil:
    # Das einzige Urteil einer Wiederholung des einzigen Evalinputs.

    return Urteil.objects.get(gespraech__wiederholung=wiederholung)


def _korrigieren(
    client: Client, vignette: Vignette, urteil: Urteil, begruendung: str = "Falsch"
) -> HttpResponse:
    # Korrigiert per POST und folgt der Weiterleitung auf die Ansicht.

    return client.post(
        reverse("evals:urteil_korrigieren", args=[vignette.pk, urteil.pk]),
        {"begruendung": begruendung},
        follow=True,
    )


def _zuruecknehmen(client: Client, vignette: Vignette, urteil: Urteil) -> HttpResponse:
    # Nimmt die Korrektur per POST zurück und folgt der Weiterleitung.

    return client.post(
        reverse("evals:korrektur_zuruecknehmen", args=[vignette.pk, urteil.pk]),
        follow=True,
    )


def _detail(konto: Konto, vignette: Vignette) -> str:
    # Die Vignettenansicht ohne Tags, mit dem Hinweis beim Finalisieren.

    return text_ohne_tags(
        _client(konto).get(reverse("vignetten:detail", args=[vignette.pk]))
    )


@pytest.fixture
def ada() -> Konto:
    """Eine Autor:in mit eigener Vignette."""

    return konto_mit_rollen("ada", "Autor:in")


@pytest.fixture
def zwei_von_drei() -> None:
    """Ein Kriterium, k = 3, die zweite Wiederholung urteilt nicht erfüllt."""

    finaler_katalog(k=3, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(3), bewerter=urteile(True, False, True))


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_korrektur_macht_aus_zwei_von_drei_bestanden(ada: Konto) -> None:
    """Quote, Bestehen und Finalisierungs-Hinweis folgen dem wirksamen Urteil."""

    vignette: Vignette = _abgearbeitet(ada)

    korrigiert: str = text_ohne_tags(_korrigieren(_client(ada), vignette, _urteil(2)))
    hinweis_korrigiert: str = _detail(ada, vignette)

    assert "3 von 3 · bestanden" in korrigiert
    assert "Fertig · Bestanden" in korrigiert
    assert "Evallauf Fertig · Bestanden." in hinweis_korrigiert
    assert "Muster gezeigt 3 von 3" in hinweis_korrigiert


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_ruecknahme_stellt_zwei_von_drei_nicht_bestanden_wieder_her(
    ada: Konto,
) -> None:
    """Nach der Rücknahme bestimmen wieder die Bewerterurteile Quote und Hinweis."""

    vignette: Vignette = _abgearbeitet(ada)
    client: Client = _client(ada)
    _korrigieren(client, vignette, _urteil(2))

    zurueck: str = text_ohne_tags(_zuruecknehmen(client, vignette, _urteil(2)))
    hinweis_zurueck: str = _detail(ada, vignette)

    assert "2 von 3 · nicht bestanden" in zurueck
    assert "Fertig · Nicht bestanden" in zurueck
    assert "Evallauf Fertig · Nicht bestanden." in hinweis_zurueck
    assert "Muster gezeigt 2 von 3" in hinweis_zurueck


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_korrektur_haelt_original_person_und_zeitpunkt_getrennt_fest(
    ada: Konto,
) -> None:
    """Originalurteil und -begründung bleiben; die Korrektur steht daneben."""

    vignette: Vignette = _abgearbeitet(ada)

    _korrigieren(_client(ada), vignette, _urteil(2), "  Das Muster ist da.  ")

    urteil: Urteil = _urteil(2)
    assert (urteil.erfuellt, urteil.begruendung) == (False, "Begründung 2")
    assert urteil.korrektur_begruendung == "Das Muster ist da."
    assert urteil.korrigiert_von == ada
    assert urteil.korrigiert_am is not None
    assert urteil.wirksam is True


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_gespraech_zeigt_korrektur_als_manuell_neben_dem_original(ada: Konto) -> None:
    """Das gewählte Gespräch nennt wirksames Urteil, Korrektur und Bewerterurteil."""

    vignette: Vignette = _abgearbeitet(ada)
    urteil: Urteil = _urteil(2)

    seite: str = text_ohne_tags(
        _korrigieren(_client(ada), vignette, urteil, "Das Muster ist da.")
    )

    assert "Muster gezeigt · erfüllt · manuell korrigiert" in seite
    assert "Korrektur von ada" in seite and "Das Muster ist da." in seite
    assert "Bewerter: nicht erfüllt · Begründung 2" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_bestehende_korrektur_laesst_sich_aendern_ohne_historie(ada: Konto) -> None:
    """Eine zweite Korrektur ersetzt Begründung, Person und Zeitpunkt."""

    vignette: Vignette = _abgearbeitet(ada)
    grace: Konto = konto_mit_rollen("grace", "Autor:in")
    vignette.historie.eigentuemerinnen.add(grace)
    _korrigieren(_client(ada), vignette, _urteil(2), "Erste")

    seite: str = _korrigieren(_client(grace), vignette, _urteil(2), "Zweite").content
    urteil: Urteil = _urteil(2)

    assert (urteil.korrektur_begruendung, urteil.korrigiert_von) == ("Zweite", grace)
    assert urteil.wirksam is True
    assert "Korrektur ändern" in [text for text, _ in submit_knoepfe(seite.decode())]


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_ruecknahme_stellt_das_bewerterurteil_wieder_her(ada: Konto) -> None:
    """Nach der Rücknahme gibt es keine Spur der Korrektur mehr."""

    vignette: Vignette = _abgearbeitet(ada)
    _korrigieren(_client(ada), vignette, _urteil(2))

    _zuruecknehmen(_client(ada), vignette, _urteil(2))

    urteil: Urteil = _urteil(2)
    assert not urteil.korrigiert
    assert (urteil.wirksam, urteil.korrektur_begruendung) == (False, "")
    assert (urteil.korrigiert_von, urteil.korrigiert_am) == (None, None)


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_erfuelltes_urteil_laesst_sich_zu_nicht_erfuellt_korrigieren(
    ada: Konto,
) -> None:
    """Die Korrektur kehrt das Bewerterurteil in beide Richtungen um."""

    vignette: Vignette = _abgearbeitet(ada)

    seite: str = text_ohne_tags(_korrigieren(_client(ada), vignette, _urteil(1)))

    assert _urteil(1).wirksam is False
    assert "1 von 3 · nicht bestanden" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
@pytest.mark.parametrize("begruendung", ["", "   "])
def test_korrektur_ohne_begruendung_wird_abgewiesen(
    ada: Konto, begruendung: str
) -> None:
    """Ohne eigene Begründung bleibt das Urteil unkorrigiert, mit Meldung."""

    vignette: Vignette = _abgearbeitet(ada)

    seite: str = text_ohne_tags(
        _korrigieren(_client(ada), vignette, _urteil(2), begruendung)
    )

    assert not _urteil(2).korrigiert
    assert "Eine Korrektur braucht eine Begründung." in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_gespraech_bietet_die_korrektur_als_formular_an(ada: Konto) -> None:
    """Ein beurteiltes Kriterium eines abgeschlossenen Laufs hat ein Korrekturformular."""

    vignette: Vignette = _abgearbeitet(ada)

    antwort: HttpResponse = _client(ada).get(
        reverse("evals:evallauf", args=[vignette.pk]), {"wiederholung": 2}
    )

    assert "Als erfüllt werten" in [text for text, _ in submit_knoepfe(antwort)]
    assert (
        reverse("evals:urteil_korrigieren", args=[vignette.pk, _urteil(2).pk])
        in antwort.content.decode()
    )


@pytest.mark.django_db
def test_ohne_urteil_und_gescheiterte_schuelerin_sind_nicht_korrigierbar(
    ada: Konto,
) -> None:
    """Fehlende und automatisch gesetzte Urteile werden nicht umetikettiert."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    drei_fakes(
        schuelerin=[*antworten(1), *[{"fehler": "anbieterfehler"}] * 3],
        bewerter=[{"fehler": "formatbruch"}] * 3,
    )
    vignette: Vignette = _abgearbeitet(ada)
    client: Client = _client(ada)

    ohne_urteil: str = text_ohne_tags(_korrigieren(client, vignette, _urteil(1)))
    gescheitert: str = text_ohne_tags(_korrigieren(client, vignette, _urteil(2)))
    antwort: HttpResponse = client.get(
        reverse("evals:evallauf", args=[vignette.pk]), {"wiederholung": 2}
    )

    assert not Urteil.objects.exclude(korrigiert_am=None).exists()
    assert "Nur Bewerterurteile lassen sich korrigieren." in ohne_urteil
    assert "Nur Bewerterurteile lassen sich korrigieren." in gescheitert
    assert "Als erfüllt werten" not in [text for text, _ in submit_knoepfe(antwort)]


@pytest.mark.django_db
@pytest.mark.parametrize("zustand", [Evallauf.Zustand.WARTET, Evallauf.Zustand.LAEUFT])
@pytest.mark.usefixtures("zwei_von_drei")
def test_offener_lauf_bleibt_schreibgeschuetzt(
    ada: Konto, zustand: Evallauf.Zustand
) -> None:
    """Solange ein Lauf wartet oder läuft, gibt es weder Formular noch Korrektur."""

    vignette: Vignette = _abgearbeitet(ada)
    Evallauf.objects.filter(vignette=vignette).update(zustand=zustand)

    client: Client = _client(ada)

    seite: str = text_ohne_tags(_korrigieren(client, vignette, _urteil(2)))
    antwort: HttpResponse = client.get(
        reverse("evals:evallauf", args=[vignette.pk]), {"wiederholung": 2}
    )

    assert not _urteil(2).korrigiert
    assert "Nur abgeschlossene Evalläufe lassen sich korrigieren." in seite
    assert "Als erfüllt werten" not in [text for text, _ in submit_knoepfe(antwort)]


@pytest.mark.django_db
def test_abgebrochener_lauf_bleibt_nach_korrektur_abgebrochen(ada: Konto) -> None:
    """Vorhandene Urteile sind korrigierbar; insgesamt besteht der Teilstand nie."""

    finaler_katalog(k=2, schritte=("Eins",), uebergreifende=())
    # Das Skript reicht nur für das erste Gespräch; das zweite bricht ab.
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(False))
    vignette: Vignette = _abgearbeitet(ada)

    seite: str = text_ohne_tags(_korrigieren(_client(ada), vignette, _urteil(1)))

    lauf: Evallauf = Evallauf.objects.get(vignette=vignette)
    assert lauf.zustand == Evallauf.Zustand.ABGEBROCHEN
    assert not lauf.bestanden
    assert "1 von 2 · nicht bestanden" in seite
    assert "1 noch nicht ausgeführt" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_korrektur_aendert_weder_veraltet_noch_die_fassung(ada: Konto) -> None:
    """Ein veralteter Lauf bleibt veraltet; die Fassung behält ihren Stand."""

    vignette: Vignette = _abgearbeitet(ada, finale_vignette(ada))
    vignette.refresh_from_db()
    stand = vignette.geaendert_am
    Evallauf.objects.filter(vignette=vignette).update(
        vignette_geaendert_am=stand.replace(year=2000)
    )

    _korrigieren(_client(ada), vignette, _urteil(2))

    vignette.refresh_from_db()
    assert vignette.geaendert_am == stand
    assert vignette.zustand == Vignette.Zustand.FINAL
    assert Evallauf.objects.get(vignette=vignette).veraltet


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_neuer_lauf_ersetzt_den_alten_samt_korrekturen(ada: Konto) -> None:
    """Ein alter Browserstand ändert den neuen Lauf nicht; Korrekturen wandern nicht."""

    vignette: Vignette = _abgearbeitet(ada)
    altes: Urteil = _urteil(2)
    _korrigieren(_client(ada), vignette, altes)
    drei_fakes(schuelerin=antworten(3), bewerter=urteile(True, False, True))
    _abgearbeitet(ada, vignette)

    seite: str = text_ohne_tags(_korrigieren(_client(ada), vignette, altes))

    assert not Urteil.objects.exclude(korrigiert_am=None).exists()
    assert "Dieses Urteil gehört nicht zum aktuellen Evallauf." in seite
    assert "2 von 3 · nicht bestanden" in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_urteil_einer_anderen_fassung_laesst_sich_nicht_ueber_diese_aendern(
    ada: Konto,
) -> None:
    """Die Urteilszuordnung wird gegen die Fassung der Adresse geprüft."""

    eigene: Vignette = _abgearbeitet(ada)
    andere: Vignette = finale_vignette(ada, name="Andere")
    drei_fakes(schuelerin=antworten(3), bewerter=urteile(True, False, True))
    _abgearbeitet(ada, andere)
    fremdes: Urteil = Urteil.objects.get(
        gespraech__evallauf__vignette=andere, gespraech__wiederholung=2
    )

    seite: str = text_ohne_tags(_korrigieren(_client(ada), eigene, fremdes))

    assert not Urteil.objects.exclude(korrigiert_am=None).exists()
    assert "Dieses Urteil gehört nicht zum aktuellen Evallauf." in seite


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_fremde_und_teilnehmende_duerfen_nicht_korrigieren(ada: Konto) -> None:
    """Fremde Autor:innen erhalten 404, Konten ohne Autor:innen-Rolle 403."""

    vignette: Vignette = _abgearbeitet(ada)
    urteil: Urteil = _urteil(2)
    lin: Client = _client(konto_mit_rollen("lin", "Autor:in"))
    tom: Client = _client(konto_mit_rollen("tom"))
    adresse: str = reverse("evals:urteil_korrigieren", args=[vignette.pk, urteil.pk])
    ruecknahme: str = reverse(
        "evals:korrektur_zuruecknehmen", args=[vignette.pk, urteil.pk]
    )

    assert lin.post(adresse, {"begruendung": "x"}).status_code == 404
    assert lin.post(ruecknahme).status_code == 404
    assert tom.post(adresse, {"begruendung": "x"}).status_code == 403
    assert tom.get(reverse("evals:evallauf", args=[vignette.pk])).status_code == 403
    assert not _urteil(2).korrigiert


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_administration_darf_korrigieren(ada: Konto) -> None:
    """Die Administration korrigiert auch fremde Fassungen."""

    vignette: Vignette = _abgearbeitet(ada)
    admin: Konto = konto_mit_rollen("admin", is_superuser=True)

    _korrigieren(_client(admin), vignette, _urteil(2))

    assert _urteil(2).korrigiert_von == admin


@pytest.mark.django_db
@pytest.mark.usefixtures("zwei_von_drei")
def test_korrektur_nur_per_post_mit_csrf(ada: Konto) -> None:
    """GET ändert nichts, ein POST ohne CSRF-Token wird abgewiesen."""

    vignette: Vignette = _abgearbeitet(ada)
    adresse: str = reverse(
        "evals:urteil_korrigieren", args=[vignette.pk, _urteil(2).pk]
    )
    ohne_token: Client = Client(enforce_csrf_checks=True)
    ohne_token.force_login(ada)

    assert _client(ada).get(adresse).status_code == 405
    assert ohne_token.post(adresse, {"begruendung": "x"}).status_code == 403
    assert not _urteil(2).korrigiert


@pytest.mark.django_db
def test_korrigieren_am_modell_prueft_den_laufzustand(ada: Konto) -> None:
    """Auch ohne View ist ein laufender Lauf geschützt."""

    finaler_katalog(k=1, schritte=("Eins",), uebergreifende=())
    drei_fakes(schuelerin=antworten(1), bewerter=urteile(False))
    lauf: Evallauf = Evallauf.objects.ausloesen(finale_vignette(ada))
    evallauf_ausfuehren(lauf)
    Evallauf.objects.filter(pk=lauf.pk).update(zustand=Evallauf.Zustand.LAEUFT)

    with pytest.raises(ValidationError):
        _urteil(1).korrigieren("Falsch", ada)

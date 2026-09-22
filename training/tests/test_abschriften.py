"""Tests des Import-Kommandos und der Token-Eingabe für Abschriften."""

import pytest
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsitem,
    Erhebungsvignette,
    ItemAntwort,
    Itemblock,
    Stichprobe,
)
from fragebogen_items.models import FragebogenItem
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
    Vignettenposition,
)
from training.abschriften import ABLEHNUNG, abschrift_holen
from training.models import Abschrift
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


def _erhebung_anlegen(konto: Konto, name: str = "Brüche") -> Erhebung:
    """Legt eine Erhebung mit einer eingebundenen Vignette und aktivem Modell an."""

    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name=name)
    ModellKonfiguration.objects.aktivieren(
        ModellKonfiguration.objects.create(sprachmodell="fake")
    )
    Erhebungsvignette.objects.create(
        erhebung=erhebung, vignette=_finale_vignette_anlegen(konto), position=1
    )
    return erhebung


def _stichprobe_anlegen(erhebung: Erhebung) -> Stichprobe:
    """Legt eine Stichprobe an, deren Erhebungsfenster bereits vorüber ist."""

    return Stichprobe.objects.create(
        erhebung=erhebung, beginn=timezone.now(), ende=timezone.now()
    )


def _gespielte_teilnahme(
    erhebung: Erhebung,
    *,
    stichprobe: Stichprobe | None = None,
    token: str = "2345-6789",
    abgeschlossen: bool = True,
) -> Erhebungsbindung:
    """Legt eine Erhebungsteilnahme mit einer vollständig gespielten Sitzung an."""

    bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
        stichprobe=stichprobe or _stichprobe_anlegen(erhebung),
        teilnahme=Teilnahme.objects.create(einwilligung_erteilt=True),
        token=token,
        abgeschlossen_am=timezone.now() if abgeschlossen else None,
    )
    vignette: Vignette = erhebung.vignetten.get()
    sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=bindung.teilnahme,
        vignette=vignette,
        simulationskern=_finaler_kern(),
        modell_konfiguration=ModellKonfiguration.objects.aktive(),
        status=Sitzung.Status.ABGESCHLOSSEN,
    )
    schritt: Gespraechsschritt = Gespraechsschritt.objects.create(
        sitzung=sitzung,
        eingabe="Wie hast du gerechnet?",
        denkspur="Ich addiere Zähler und Nenner.",
        aeusserung="Ich habe oben und unten zusammengezählt.",
        reihenfolge=1,
    )
    Fehlversuch.objects.create(
        gespraechsschritt=schritt, grund="Format", rohantwort="{kaputt"
    )
    Diagnose.objects.create(sitzung=sitzung, text="Zähler und Nenner addiert.")
    Vignettenposition.objects.create(
        teilnahme=bindung.teilnahme, sitzung=sitzung, vignette=vignette, position=1
    )
    return bindung


def _gespielte_teilnahme_in_neuer_erhebung(name: str = "Brüche") -> Erhebungsbindung:
    """Legt eine gespielte Teilnahme samt Erhebung und deren Forschender an.

    Für Tests, die nur das Token brauchen und denen die Erhebungsseite selbst
    gleichgültig ist.
    """

    return _gespielte_teilnahme(
        _erhebung_anlegen(Konto.objects.create_user(username="ada"), name=name)
    )


@pytest.mark.django_db
def test_holt_die_sitzungen_einer_abgeschlossenen_teilnahme_ins_konto() -> None:
    """Der Import kopiert die Datenspur vollständig unter eine eigene Teilnahme."""

    forschende: Konto = Konto.objects.create_user(username="ada")
    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = _erhebung_anlegen(forschende)
    bindung: Erhebungsbindung = _gespielte_teilnahme(erhebung)

    abschrift: Abschrift = abschrift_holen(teilnehmerin, bindung.token)

    assert abschrift.konto == teilnehmerin
    assert abschrift.erhebungsname == erhebung.name
    assert abschrift.teilnahme != bindung.teilnahme
    kopie: Sitzung = Sitzung.objects.get(teilnahme=abschrift.teilnahme)
    original: Sitzung = Sitzung.objects.get(teilnahme=bindung.teilnahme)
    assert kopie.vignette == original.vignette
    assert kopie.simulationskern == original.simulationskern
    assert kopie.modell_konfiguration == original.modell_konfiguration
    assert kopie.status == original.status
    kopierter_schritt: Gespraechsschritt = kopie.gespraechsschritte.get()
    originalschritt: Gespraechsschritt = original.gespraechsschritte.get()
    assert kopierter_schritt.eingabe == originalschritt.eingabe
    assert kopierter_schritt.denkspur == originalschritt.denkspur
    assert kopierter_schritt.aeusserung == originalschritt.aeusserung
    assert kopierter_schritt.reihenfolge == originalschritt.reihenfolge
    assert [
        fehlversuch.rohantwort
        for fehlversuch in kopierter_schritt.fehlversuch_set.all()
    ] == ["{kaputt"]
    assert kopie.diagnose.text == original.diagnose.text
    position: Vignettenposition = abschrift.teilnahme.vignettenpositionen.get()
    assert (position.position, position.sitzung) == (1, kopie)


@pytest.mark.django_db
def test_laesst_die_erhebungsseite_unberuehrt() -> None:
    """Weder Bindung noch Teilnahme noch Sitzungen der Erhebung ändern sich."""

    forschende: Konto = Konto.objects.create_user(username="ada")
    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = _erhebung_anlegen(forschende)
    bindung: Erhebungsbindung = _gespielte_teilnahme(erhebung)
    vorher: dict[str, object] = Erhebungsbindung.objects.values().get(pk=bindung.pk)

    abschrift: Abschrift = abschrift_holen(teilnehmerin, bindung.token)

    assert Erhebungsbindung.objects.values().get(pk=bindung.pk) == vorher
    assert Erhebungsbindung.objects.count() == 1
    assert Sitzung.objects.filter(teilnahme=bindung.teilnahme).count() == 1
    assert (
        Gespraechsschritt.objects.filter(sitzung__teilnahme=bindung.teilnahme).count()
        == 1
    )
    assert abschrift.teilnahme.pk != bindung.teilnahme.pk


@pytest.mark.django_db
def test_kopiert_keine_fragebogen_antworten() -> None:
    """Die Item-Antworten bleiben Messinstrument der Erhebung."""

    forschende: Konto = Konto.objects.create_user(username="ada")
    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = _erhebung_anlegen(forschende)
    bindung: Erhebungsbindung = _gespielte_teilnahme(erhebung)
    item: FragebogenItem = FragebogenItem.objects.anlegen(
        forschende, wortlaut="Wie war die Sitzung?"
    )
    item.finalisieren()
    erhebungsitem: Erhebungsitem = Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=1,
    )
    sitzung: Sitzung = Sitzung.objects.get(teilnahme=bindung.teilnahme)
    block: Itemblock = Itemblock.objects.create(
        erhebungsbindung=bindung,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        sitzung=sitzung,
    )
    ItemAntwort.objects.create(
        itemblock=block,
        erhebungsbindung=bindung,
        erhebungsitem=erhebungsitem,
        sitzung=sitzung,
        freitext="Anstrengend.",
    )

    abschrift: Abschrift = abschrift_holen(teilnehmerin, bindung.token)

    assert ItemAntwort.objects.count() == 1
    assert not ItemAntwort.objects.filter(
        sitzung__teilnahme=abschrift.teilnahme
    ).exists()
    assert not Itemblock.objects.filter(sitzung__teilnahme=abschrift.teilnahme).exists()


@pytest.mark.django_db
def test_kopierte_sitzungen_tragen_die_importzeit() -> None:
    """Die Zeitstempel der Abschrift gehören ihr selbst, nicht der Erhebung."""

    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    bindung: Erhebungsbindung = _gespielte_teilnahme_in_neuer_erhebung()
    original: Sitzung = Sitzung.objects.get(teilnahme=bindung.teilnahme)

    abschrift: Abschrift = abschrift_holen(teilnehmerin, bindung.token)

    kopie: Sitzung = Sitzung.objects.get(teilnahme=abschrift.teilnahme)
    assert kopie.erstellt_am >= abschrift.importiert_am
    assert kopie.erstellt_am > original.erstellt_am


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fall",
    [
        "unbekannt",
        "nicht_abgeschlossen",
        "stichprobe_archiviert",
        "erhebung_archiviert",
    ],
)
def test_weist_unbrauchbare_tokens_mit_derselben_meldung_ab(fall: str) -> None:
    """Der Import verrät nie, woran er sich gestoßen hat."""

    forschende: Konto = Konto.objects.create_user(username="ada")
    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = _erhebung_anlegen(forschende)
    token: str = "2345-6789"
    match fall:
        case "unbekannt":
            _gespielte_teilnahme(erhebung)
            token = "9999-9999"
        case "nicht_abgeschlossen":
            _gespielte_teilnahme(erhebung, abgeschlossen=False)
        case "stichprobe_archiviert":
            stichprobe: Stichprobe = _stichprobe_anlegen(erhebung)
            stichprobe.archivieren()
            _gespielte_teilnahme(erhebung, stichprobe=stichprobe)
        case "erhebung_archiviert":
            _gespielte_teilnahme(erhebung)
            erhebung.finalisieren()
            erhebung.archivieren()

    with pytest.raises(ValidationError) as abgelehnt:
        abschrift_holen(teilnehmerin, token)

    assert abgelehnt.value.messages == [ABLEHNUNG]
    assert not Abschrift.objects.exists()
    assert not Teilnahme.objects.filter(erhebungsbindung__isnull=True).exists()


@pytest.mark.django_db
def test_import_nach_dem_erhebungsfenster_gelingt() -> None:
    """Der Hebel der Forschenden ist das Archivieren, nicht die Phase."""

    forschende: Konto = Konto.objects.create_user(username="ada")
    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = _erhebung_anlegen(forschende)
    bindung: Erhebungsbindung = _gespielte_teilnahme(erhebung)

    assert bindung.stichprobe.phase == Stichprobe.Phase.NACH
    assert abschrift_holen(teilnehmerin, bindung.token).pk is not None


@pytest.mark.django_db
def test_zweiter_import_erzeugt_eine_eigenstaendige_zweite_abschrift() -> None:
    """Es gibt keine Deduplizierung; sie verlangte die verbotene Verknüpfung."""

    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    bindung: Erhebungsbindung = _gespielte_teilnahme_in_neuer_erhebung()

    erste: Abschrift = abschrift_holen(teilnehmerin, bindung.token)
    zweite: Abschrift = abschrift_holen(teilnehmerin, bindung.token)

    assert erste.teilnahme != zweite.teilnahme
    assert Abschrift.objects.count() == 2
    assert Sitzung.objects.filter(teilnahme=zweite.teilnahme).count() == 1


def test_abschrift_haelt_weder_token_noch_verweis_auf_die_erhebung() -> None:
    """Nach dem Import sind beide Seiten wieder entkoppelt."""

    felder: set[str] = {feld.name for feld in Abschrift._meta.get_fields()}

    assert felder.isdisjoint({"token", "erhebung", "stichprobe", "erhebungsbindung"})


@pytest.mark.django_db
def test_token_eingabe_ist_jedem_eingeloggten_konto_zugaenglich(client: Client) -> None:
    """Anonyme Aufrufe landen beim Login, eingeloggte bei der Token-Eingabe."""

    url: str = reverse("training:abschriften")

    assert client.get(url).status_code == 302

    client.force_login(Konto.objects.create_user(username="grace"))

    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_eingegebenes_token_erzeugt_die_abschrift_und_listet_sie(
    client: Client,
) -> None:
    """Nach dem Import erscheint die Abschrift mit Erhebungsname und Importzeit."""

    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    bindung: Erhebungsbindung = _gespielte_teilnahme_in_neuer_erhebung(
        name="Brüche im Herbst"
    )
    client.force_login(teilnehmerin)
    url: str = reverse("training:abschriften")

    antwort: HttpResponse = client.post(
        url, {"token": bindung.token.lower()}, follow=True
    )

    abschrift: Abschrift = Abschrift.objects.get(konto=teilnehmerin)
    assert abschrift.erhebungsname == "Brüche im Herbst"
    inhalt: str = antwort.content.decode()
    assert "Brüche im Herbst" in inhalt
    assert str(abschrift.importiert_am.year) in inhalt


@pytest.mark.django_db
def test_abgelehntes_token_meldet_den_grundlosen_hinweis(client: Client) -> None:
    """Die View gibt die eine Meldung des Kommandos weiter."""

    client.force_login(Konto.objects.create_user(username="grace"))

    antwort: HttpResponse = client.post(
        reverse("training:abschriften"), {"token": "9999-9999"}, follow=True
    )

    assert ABLEHNUNG in antwort.content.decode()
    assert not Abschrift.objects.exists()


@pytest.mark.django_db
def test_abschriften_fremder_konten_bleiben_aus_der_liste(client: Client) -> None:
    """Die Liste zeigt ausschließlich die eigenen Abschriften."""

    fremde: Konto = Konto.objects.create_user(username="linus")
    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    bindung: Erhebungsbindung = _gespielte_teilnahme_in_neuer_erhebung(
        name="Fremde Erhebung"
    )
    abschrift_holen(fremde, bindung.token)
    client.force_login(teilnehmerin)

    antwort: HttpResponse = client.get(reverse("training:abschriften"))

    assert "Fremde Erhebung" not in antwort.content.decode()


@pytest.mark.django_db
def test_abschrift_zaehlt_nicht_zur_trainingshistorie(client: Client) -> None:
    """Die Historie zählt weiterhin nur über die Trainingsbindung."""

    teilnehmerin: Konto = Konto.objects.create_user(username="grace")
    bindung: Erhebungsbindung = _gespielte_teilnahme_in_neuer_erhebung(
        name="Brüche im Herbst"
    )
    abschrift_holen(teilnehmerin, bindung.token)
    client.force_login(teilnehmerin)

    antwort: HttpResponse = client.get(reverse("training:historie"))

    assert "Brüche im Herbst" not in antwort.content.decode()

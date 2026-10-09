"""ORM-Tests für Vignetten und ihre Historien."""

from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from config.tests.aufbau import (
    finale_vignette,
    finaler_kern,
    konto_mit_rollen,
    vignetten_entwurf,
)
from konten.models import Konto
from simulation.models import Simulationskern
from vignetten.models import (
    Aufgabenkontextteil,
    Vignette,
    Vignettenhistorie,
    prompt_platzhalter,
    rahmen_platzhalter,
)


def test_prompt_platzhalter_ordnet_arbeitsheft_text_und_bildbeschreibung() -> None:
    """Der zusammengesetzte Arbeitsheftwert folgt dem ersten Positionsmarker."""

    vignette: Vignette = Vignette(
        zustand=Vignette.Zustand.FINAL,
        fehlermuster_beschreibung="Brüche <werden> addiert.",
        lernauftrag_text="Addiere zwei Brüche.",
        arbeitsheft_text="8 + 4 = 12\n  [BILD] \nAlso ist die Lösung 7.\n[bild]",
        arbeitsheft_bild="vignettenbilder/heft.gif",
        arbeitsheft_bildbeschreibung="Heftseite mit durchgestrichener 12.",
        schuelerin_name="Mia",
        schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
        fach="Mathematik",
        thema="Brüche",
        klassenstufe="5",
    )

    assert prompt_platzhalter(vignette) == {
        "fehlermuster_beschreibung": (
            "<fehlermuster_beschreibung>\n"
            "Brüche <werden> addiert.\n"
            "</fehlermuster_beschreibung>"
        ),
        "lernauftrag": (
            "<lernauftrag>\n"
            "<lernauftrag_text>Addiere zwei Brüche.</lernauftrag_text>\n"
            "</lernauftrag>"
        ),
        "arbeitsheft": (
            "<arbeitsheft>\n"
            "<arbeitsheft_text>8 + 4 = 12\n</arbeitsheft_text>\n"
            "<arbeitsheft_bildbeschreibung>Heftseite mit durchgestrichener 12."
            "</arbeitsheft_bildbeschreibung>\n"
            "<arbeitsheft_text>Also ist die Lösung 7.\n</arbeitsheft_text>\n"
            "</arbeitsheft>"
        ),
        "lernauftrag_simulationshinweise": "",
        "arbeitsheft_simulationshinweise": "",
        "schuelerin_name": "Mia",
        "schuelerin_geschlecht": "weiblich",
        "fach": "Mathematik",
        "thema": "Brüche",
        "klassenstufe": "5",
    }


def test_prompt_platzhalter_ordnet_lernauftrag_text_und_bildbeschreibung() -> None:
    """Der komponierte Lernauftrag folgt dem ersten Positionsmarker."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            lernauftrag_text="Rechne zuerst.\r\n\t[Bild]\r\nBegründe danach.",
            lernauftrag_bild="vignettenbilder/auftrag.gif",
            lernauftrag_bildbeschreibung="Arbeitsblatt mit einer Zahlenreihe.",
        )
    )

    assert platzhalter["lernauftrag"] == (
        "<lernauftrag>\n"
        "<lernauftrag_text>Rechne zuerst.\r\n</lernauftrag_text>\n"
        "<lernauftrag_bildbeschreibung>Arbeitsblatt mit einer Zahlenreihe."
        "</lernauftrag_bildbeschreibung>\n"
        "<lernauftrag_text>Begründe danach.</lernauftrag_text>\n"
        "</lernauftrag>"
    )


def test_prompt_platzhalter_fasst_simulationshinweise_in_umgebungen() -> None:
    """Simulationshinweise werden in benannte Umgebungen gefasst."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            lernauftrag_simulationshinweise="Klasse hat Brüche mit Pizza geübt.",
            arbeitsheft_simulationshinweise="Mia hat zuvor mit Plättchen probiert.",
        )
    )

    assert platzhalter["lernauftrag_simulationshinweise"] == (
        "<lernauftrag_simulationshinweise>\n"
        "Klasse hat Brüche mit Pizza geübt.\n"
        "</lernauftrag_simulationshinweise>"
    )
    assert platzhalter["arbeitsheft_simulationshinweise"] == (
        "<arbeitsheft_simulationshinweise>\n"
        "Mia hat zuvor mit Plättchen probiert.\n"
        "</arbeitsheft_simulationshinweise>"
    )


def test_prompt_platzhalter_reicht_spitze_klammern_unveraendert_durch() -> None:
    """Nutzereingaben gehen roh in den Prompt — kein HTML-Escaping."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            fehlermuster_beschreibung="a < b & b > c",
            lernauftrag_text="Vergleiche <a> mit &amp;.",
            arbeitsheft_simulationshinweise='Mia schreibt "5 < 7".',
            schuelerin_name="Mia & Tom",
        )
    )

    assert platzhalter["fehlermuster_beschreibung"] == (
        "<fehlermuster_beschreibung>\na < b & b > c\n</fehlermuster_beschreibung>"
    )
    assert platzhalter["lernauftrag"] == (
        "<lernauftrag>\n"
        "<lernauftrag_text>Vergleiche <a> mit &amp;.</lernauftrag_text>\n"
        "</lernauftrag>"
    )
    assert platzhalter["arbeitsheft_simulationshinweise"] == (
        "<arbeitsheft_simulationshinweise>\n"
        'Mia schreibt "5 < 7".\n'
        "</arbeitsheft_simulationshinweise>"
    )
    assert platzhalter["schuelerin_name"] == "Mia & Tom"


def test_prompt_platzhalter_reicht_markdown_unveraendert_durch() -> None:
    """Das Sprachmodell liest die Markdown-Quelle, nicht das Gerenderte (ADR-0044)."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(lernauftrag_text="Addiere **zwei** Brüche.\n[Tipp](https://x.org)")
    )

    assert platzhalter["lernauftrag"] == (
        "<lernauftrag>\n"
        "<lernauftrag_text>Addiere **zwei** Brüche.\n[Tipp](https://x.org)"
        "</lernauftrag_text>\n"
        "</lernauftrag>"
    )


def test_prompt_platzhalter_laesst_leere_lange_werte_ungefasst() -> None:
    """Leere lange Prompt-Inhalte werden nicht mit einer Umgebung versehen."""

    platzhalter: dict[str, str] = prompt_platzhalter(Vignette())

    assert (
        platzhalter["fehlermuster_beschreibung"],
        platzhalter["lernauftrag"],
        platzhalter["arbeitsheft"],
        platzhalter["lernauftrag_simulationshinweise"],
        platzhalter["arbeitsheft_simulationshinweise"],
    ) == ("", "", "", "", "")


@pytest.mark.parametrize("teil", ["lernauftrag", "arbeitsheft"])
def test_prompt_platzhalter_entfernt_marker_ohne_bild(teil: str) -> None:
    """Ein Teil ohne Bild gibt den Marker nie an das Modell weiter."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(**{f"{teil}_text": "Oben\n[BILD]\nunten\n[bild]"})
    )

    assert platzhalter[teil] == (
        f"<{teil}>\n<{teil}_text>Oben\nunten\n</{teil}_text>\n</{teil}>"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Setze [bild] ein.",
        "Setze ein:\n[bild](https://example.org/bild.png)\nFertig.",
        "Setze ein: [BILD]\nFertig.",
    ],
)
def test_positionsmarker_zaehlt_nur_allein_auf_einer_zeile(text: str) -> None:
    """Mitten in einer Zeile oder als Linktext bleibt [bild] gewöhnlicher Text."""

    vignette: Vignette = Vignette(
        lernauftrag_text=text,
        lernauftrag_bild="vignettenbilder/auftrag.gif",
        lernauftrag_bildbeschreibung="Arbeitsblatt",
    )

    assert (
        vignette.lernauftrag.text_vor_bild,
        vignette.lernauftrag.text_nach_bild,
    ) == (text, "")
    assert prompt_platzhalter(vignette)["lernauftrag"] == (
        "<lernauftrag>\n"
        f"<lernauftrag_text>{text}</lernauftrag_text>\n"
        "<lernauftrag_bildbeschreibung>Arbeitsblatt</lernauftrag_bildbeschreibung>\n"
        "</lernauftrag>"
    )


def test_positionsmarker_auf_eigener_zeile_zerlegt_den_text() -> None:
    """Allein auf einer Zeile zerlegt der erste Marker den Text; alle verschwinden."""

    teil: Aufgabenkontextteil = Vignette(
        arbeitsheft_text="Oben\n   [Bild]\t\nMitte\n[bild]\nunten",
        arbeitsheft_bild="vignettenbilder/heft.gif",
    ).arbeitsheft

    assert (teil.text_vor_bild, teil.text_nach_bild) == ("Oben\n", "Mitte\nunten")


@pytest.mark.parametrize("teil", ["lernauftrag", "arbeitsheft"])
def test_prompt_platzhalter_ordnet_bild_ohne_marker_nach_dem_text(teil: str) -> None:
    """Ohne Marker steht die Bildbeschreibung im Prompt nach dem Text."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            **{
                f"{teil}_text": "Aufgabe oben",
                f"{teil}_bild": "vignettenbilder/blatt.gif",
                f"{teil}_bildbeschreibung": "Blatt mit Skizze",
            }
        )
    )

    assert platzhalter[teil] == (
        f"<{teil}>\n"
        f"<{teil}_text>Aufgabe oben</{teil}_text>\n"
        f"<{teil}_bildbeschreibung>Blatt mit Skizze</{teil}_bildbeschreibung>\n"
        f"</{teil}>"
    )


@pytest.mark.parametrize("teil", ["lernauftrag", "arbeitsheft"])
def test_prompt_platzhalter_laesst_leere_textstuecke_weg(teil: str) -> None:
    """Ein Teil nur mit Bild erzeugt keine leere Textumgebung."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            **{
                f"{teil}_bild": "vignettenbilder/blatt.gif",
                f"{teil}_bildbeschreibung": "Blatt mit Skizze",
            }
        )
    )

    assert platzhalter[teil] == (
        f"<{teil}>\n"
        f"<{teil}_bildbeschreibung>Blatt mit Skizze</{teil}_bildbeschreibung>\n"
        f"</{teil}>"
    )


def test_rahmen_platzhalter_enthaelt_alle_weiblichen_werte() -> None:
    """Die Rahmenhandlung erhält rohe und abgeleitete Werte der Vignette."""
    vignette: Vignette = Vignette(
        schuelerin_name="Mia",
        schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
        lehrperson_name="Koch",
        lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
        fach="Mathematik",
        thema="Brüche",
        klassenstufe="5",
    )

    assert rahmen_platzhalter(vignette) == {
        "schuelerin_name": "Mia",
        "schuelerin_geschlecht": "weiblich",
        "lehrperson_name": "Koch",
        "lehrperson_geschlecht": "weiblich",
        "fach": "Mathematik",
        "thema": "Brüche",
        "klassenstufe": "5",
        "schuelerin_pronomen": "sie",
        "schuelerin_possessiv": "ihr",
        "lehrperson_pronomen": "sie",
        "lehrperson_possessiv": "ihr",
        "lehrperson_anrede": "Frau",
    }


def test_rahmen_platzhalter_leitet_maennliche_formen_beider_akteure_ab() -> None:
    """Die kanonischen männlichen Formen gelten für beide Akteure."""
    vignette: Vignette = Vignette(
        schuelerin_geschlecht=Vignette.Geschlecht.MAENNLICH,
        lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
    )

    platzhalter: dict[str, str] = rahmen_platzhalter(vignette)

    assert platzhalter["schuelerin_pronomen"] == "er"
    assert platzhalter["schuelerin_possessiv"] == "sein"
    assert platzhalter["lehrperson_pronomen"] == "er"
    assert platzhalter["lehrperson_possessiv"] == "sein"
    assert platzhalter["lehrperson_anrede"] == "Herr"


def test_bildkuerzel_mappt_geschlecht_auf_w_oder_m() -> None:
    """Die Bildkürzel übersetzen MAENNLICH zu 'm', ansonsten immer 'w'."""
    vignette_m: Vignette = Vignette(
        schuelerin_geschlecht=Vignette.Geschlecht.MAENNLICH,
        lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
    )
    assert vignette_m.schuelerin_bildkuerzel == "m"
    assert vignette_m.lehrperson_bildkuerzel == "m"

    vignette_w: Vignette = Vignette(
        schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
        lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
    )
    assert vignette_w.schuelerin_bildkuerzel == "w"
    assert vignette_w.lehrperson_bildkuerzel == "w"


class VignetteAnlegenTests(TestCase):
    """Die Manager-Methode erzeugt eine vollständige neue Vignettenlinie."""

    def test_oeffentliches_create_umgeht_den_lebenszyklus_nicht(self) -> None:
        """Neue Fassungen entstehen ausschließlich über die Anlege-Naht."""
        with self.assertRaises(RuntimeError):
            Vignette.objects.create(historie=Vignettenhistorie.objects.create())

    def test_bulk_create_umgeht_den_lebenszyklus_nicht(self) -> None:
        """Auch Masseneinfügen erzeugt keine Fassung neben der Anlege-Naht."""
        with self.assertRaises(RuntimeError):
            Vignette.objects.bulk_create(
                [Vignette(historie=Vignettenhistorie.objects.create())]
            )

    def _vignette_mit_zwei_finalen_kernen_anlegen(
        self,
    ) -> tuple[Vignette, Konto, Simulationskern]:
        # Zwei finale Fassungen machen die Auswahl der neuesten Fassung prüfbar.
        konto: Konto = get_user_model().objects.create_user(username="ada")
        erster_kern: Simulationskern = Simulationskern.objects.anlegen()
        erster_kern.finalisieren()
        neuester_kern: Simulationskern = erster_kern.bearbeiten()
        neuester_kern.finalisieren()
        vignette: Vignette = Vignette.objects.anlegen(konto)

        return vignette, konto, neuester_kern

    def test_anlegen_erstellt_entwurf(self) -> None:
        """Eine neue Vignette beginnt als Entwurf."""
        vignette: Vignette
        vignette, _, _ = self._vignette_mit_zwei_finalen_kernen_anlegen()

        self.assertEqual(vignette.zustand, Vignette.Zustand.ENTWURF)

    def test_anlegen_pinnt_neuesten_finalen_kern(self) -> None:
        """Eine neue Vignette pinnt den neuesten finalen Simulationskern."""
        vignette: Vignette
        neuester_kern: Simulationskern
        vignette, _, neuester_kern = self._vignette_mit_zwei_finalen_kernen_anlegen()

        self.assertEqual(vignette.gepinnter_kern, neuester_kern)

    def test_anlegen_traegt_konto_als_eigentuemerin_ein(self) -> None:
        """Die anlegende Person gehört zur neuen Vignettenhistorie."""
        vignette: Vignette
        konto: Konto
        vignette, konto, _ = self._vignette_mit_zwei_finalen_kernen_anlegen()

        self.assertEqual(list(vignette.historie.eigentuemerinnen.all()), [konto])

    def test_anlegen_ohne_finalen_kern_meldet_den_grund(self) -> None:
        """Ohne finalen Kern scheitert das Anlegen mit einem Modellfehler."""
        konto: Konto = get_user_model().objects.create_user(username="ada")
        Simulationskern.objects.anlegen()

        with self.assertRaisesMessage(
            ValidationError, "Es gibt noch keinen finalen Simulationskern."
        ):
            Vignette.objects.anlegen(konto)
        self.assertFalse(Vignettenhistorie.objects.exists())

    def test_anlegen_vergibt_akteure(self) -> None:
        """Ein neuer Entwurf trägt ohne Formular beide Akteure."""
        vignette: Vignette
        vignette, _, _ = self._vignette_mit_zwei_finalen_kernen_anlegen()

        self.assertTrue(vignette.schuelerin_name)
        self.assertIn(vignette.schuelerin_geschlecht, {"weiblich", "männlich"})
        self.assertTrue(vignette.lehrperson_name)
        self.assertIn(vignette.lehrperson_geschlecht, {"weiblich", "männlich"})


class VignetteConstraintTests(TestCase):
    """Die Datenbank schützt die gemeinsame Lebenszyklus-Form."""

    def test_fassung_braucht_beide_geschlechter(self) -> None:
        """Auch ein Entwurf darf keines der Geschlechter leer lassen."""
        for feldname in ("schuelerin_geschlecht", "lehrperson_geschlecht"):
            with self.subTest(feldname=feldname):
                werte: dict[str, str] = {
                    "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
                    "lehrperson_geschlecht": Vignette.Geschlecht.WEIBLICH,
                    feldname: "",
                }
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Vignette.objects._erstellen(  # noqa: SLF001
                        historie=Vignettenhistorie.objects.create(), **werte
                    )

    def test_historie_hat_hoechstens_einen_entwurf(self) -> None:
        """Ein zweiter Entwurf derselben Historie scheitert am Unique-Index."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        Vignette.objects._erstellen(historie=historie)  # noqa: SLF001

        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects._erstellen(historie=historie)  # noqa: SLF001

    def test_finalisiert_am_muss_genau_dem_zustand_entsprechen(self) -> None:
        """Eine finale Fassung darf keinen leeren Finalisierungszeitpunkt haben."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects._erstellen(  # noqa: SLF001
                historie=Vignettenhistorie.objects.create(),
                zustand=Vignette.Zustand.FINAL,
                lernauftrag_text="Lernauftrag",
                arbeitsheft_text="Bearbeitung",
            )

    def test_entwurf_darf_keinen_finalisierungszeitpunkt_haben(self) -> None:
        """Ein Entwurf kann keinen bereits gesetzten Finalisierungszeitpunkt tragen."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects._erstellen(  # noqa: SLF001
                historie=Vignettenhistorie.objects.create(),
                finalisiert_am=timezone.now(),
            )

    def test_entarchivieren_zu_einer_schwester_wird_verhindert(self) -> None:
        """Eine archivierte Schwester kann nicht erneut final werden."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        finalisiert_am: datetime = timezone.now()
        vorgaengerin: Vignette = Vignette.objects._erstellen(  # noqa: SLF001
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        Vignette.objects._erstellen(  # noqa: SLF001
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        archivierte_schwester: Vignette = Vignette.objects._erstellen(  # noqa: SLF001
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=finalisiert_am,
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            archivierte_schwester.entarchivieren()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("teil", "anderer_teil"),
    [("lernauftrag", "arbeitsheft"), ("arbeitsheft", "lernauftrag")],
)
def test_finale_fassung_braucht_text_oder_bild_im_teil(
    teil: str, anderer_teil: str
) -> None:
    """Die Text-oder-Bild-Constraint jedes Teils schützt finale Fassungen."""

    with pytest.raises(IntegrityError), transaction.atomic():
        Vignette.objects._erstellen(  # noqa: SLF001
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            **{f"{teil}_text": "", f"{anderer_teil}_text": "Inhalt"},
        )


class VignetteSichtbarFuerQuerySetTests(TestCase):
    """Die Sichtbarkeitsabfrage über Vignettenfassungen."""

    def setUp(self) -> None:
        """Erzeugt Fassungen für verschiedene Sichtbarkeitsrollen."""
        self.ada: Konto = konto_mit_rollen("ada")
        grace: Konto = konto_mit_rollen("grace")
        linus: Konto = konto_mit_rollen("linus")
        self.dijkstra: Konto = konto_mit_rollen("dijkstra")
        self.administratorin: Konto = konto_mit_rollen("admin", is_superuser=True)

        self.eigene_fassung: Vignette = vignetten_entwurf(self.ada)
        self.geteilte_finale: Vignette = finale_vignette(self.ada)
        self.geteilte_finale.historie.eigentuemerinnen.add(grace)
        self.fremde_fassung: Vignette = vignetten_entwurf(linus)

    def test_sichtbar_fuer_liefert_eigene_und_geteilte_fassungen(self) -> None:
        """Eine Eigentümerin sieht eigene und geteilte Fassungen."""
        self.assertEqual(
            list(Vignette.objects.sichtbar_fuer(self.ada)),
            [self.eigene_fassung, self.geteilte_finale],
        )

    def test_sichtbar_fuer_liefert_unbeteiligter_keine_fassung(self) -> None:
        """Eine Person außerhalb aller Eigentümer-Kreise sieht keine Fassung."""
        self.assertEqual(list(Vignette.objects.sichtbar_fuer(self.dijkstra)), [])

    def test_sichtbar_fuer_liefert_administration_alle_fassungen(self) -> None:
        """Die Administration sieht alle Fassungen."""
        self.assertEqual(
            list(Vignette.objects.sichtbar_fuer(self.administratorin)),
            [self.eigene_fassung, self.geteilte_finale, self.fremde_fassung],
        )

    def test_sichtbar_fuer_laesst_sich_vor_einbindbar_verketten(self) -> None:
        """Sichtbarkeit vor Einbindbarkeit liefert sichtbare finale Fassungen."""
        self.assertEqual(
            list(Vignette.objects.sichtbar_fuer(self.ada).einbindbar()),
            [self.geteilte_finale],
        )

    def test_sichtbar_fuer_laesst_sich_nach_einbindbar_verketten(self) -> None:
        """Einbindbarkeit vor Sichtbarkeit liefert sichtbare finale Fassungen."""
        self.assertEqual(
            list(Vignette.objects.einbindbar().sichtbar_fuer(self.ada)),
            [self.geteilte_finale],
        )


class VignetteQuerySetTests(TestCase):
    """Die QuerySet-Methoden filtern Vignetten."""

    def test_einbindbar_liefert_nur_finale_fassungen(self) -> None:
        """Entwürfe und archivierte Fassungen sind nicht einbindbar."""
        ada: Konto = konto_mit_rollen("ada")
        vignetten_entwurf(ada)
        finale: Vignette = finale_vignette(ada)
        finale_vignette(ada).archivieren()

        self.assertEqual(list(Vignette.objects.einbindbar()), [finale])


def _vollstaendiger_entwurf(konto: Konto) -> Vignette:
    """Legt einen finalisierbaren Entwurf an, gepinnt auf den finalen Kern."""
    vignette: Vignette = vignetten_entwurf(konto)
    vignette.fehlermuster_beschreibung = "Zählt die Stellenwerte einzeln."
    vignette.lernauftrag_text = "Addiere 27 und 15."
    vignette.arbeitsheft_bildbeschreibung = "27 + 15 = 312"
    vignette.arbeitsheft_text = "27 + 15 = 312"
    vignette.schuelerin_name = "Mia"
    vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.lehrperson_name = "Frau Weber"
    vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.fach = "Mathematik"
    vignette.thema = "Addition"
    vignette.klassenstufe = "5"
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 5
    vignette.save()
    return vignette


class VignetteFinalisierenTests(TestCase):
    """Das Finalisieren prüft die Vignette über ihre öffentliche Modell-API."""

    def setUp(self) -> None:
        """Legt die Autorin der Entwürfe an."""
        self.ada: Konto = konto_mit_rollen("ada")

    def test_finalisieren_ueberfuehrt_vollstaendigen_entwurf_nach_final(self) -> None:
        """Eine vollständige Fassung wird final und erhält einen Zeitpunkt."""
        vignette: Vignette = _vollstaendiger_entwurf(self.ada)

        vignette.finalisieren()

        vignette.refresh_from_db()
        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)
        self.assertIsNotNone(vignette.finalisiert_am)

    def test_finale_fassung_ist_unveraenderlich(self) -> None:
        """Inhalte einer finalen Fassung lassen sich nicht mehr überschreiben."""
        vignette: Vignette = _vollstaendiger_entwurf(self.ada)
        vignette.finalisieren()
        vignette.lernauftrag_text = "Addiere 28 und 15."

        with self.assertRaises(ValidationError):
            vignette.save()

    def test_finalisiert_am_wird_nie_zurueckgesetzt(self) -> None:
        """Der Finalisierungszeitpunkt überlebt jede spätere Zustandsänderung."""
        vignette: Vignette = _vollstaendiger_entwurf(self.ada)
        vignette.finalisieren()
        vignette.finalisiert_am = None

        with self.assertRaises(ValidationError):
            vignette.save()

    def test_finale_fassung_laesst_keine_massenmutation_zu(self) -> None:
        """Auch der QuerySet-Zugang kann eine finale Fassung nicht verändern."""
        vignette: Vignette = _vollstaendiger_entwurf(self.ada)
        vignette.finalisieren()

        with self.assertRaises(RuntimeError):
            Vignette.objects.filter(pk=vignette.pk).update(lernauftrag_text="Verändert")

    def test_finalisieren_lehnt_nichtentwuerfe_ab(self) -> None:
        """Finalisieren ist ausschließlich die Kante vom Entwurf nach final."""
        finale: Vignette = finale_vignette(self.ada)
        archivierte: Vignette = finale_vignette(self.ada)
        archivierte.archivieren()

        for vignette in (finale, archivierte):
            with self.subTest(zustand=vignette.zustand):
                with self.assertRaisesMessage(ValidationError, "Entwürfe"):
                    vignette.finalisieren()

    def test_finalisieren_in_zweitem_tab_lehnt_den_uebergang_ab(self) -> None:
        """Eine inzwischen finalisierte Fassung meldet den abgelehnten Übergang."""
        erster_tab: Vignette = _vollstaendiger_entwurf(self.ada)
        zweiter_tab: Vignette = Vignette.objects.get(pk=erster_tab.pk)
        erster_tab.finalisieren()

        with self.assertRaisesMessage(
            ValidationError, "Nur Entwürfe können finalisiert werden."
        ):
            zweiter_tab.finalisieren()

    def test_archivieren_in_zweitem_tab_lehnt_den_uebergang_ab(self) -> None:
        """Eine inzwischen archivierte Fassung meldet den abgelehnten Übergang."""
        erster_tab: Vignette = finale_vignette(self.ada)
        zweiter_tab: Vignette = Vignette.objects.get(pk=erster_tab.pk)
        erster_tab.archivieren()

        with self.assertRaisesMessage(
            ValidationError, "Nur finale Fassungen können archiviert werden."
        ):
            zweiter_tab.archivieren()

    def test_entarchivieren_in_zweitem_tab_lehnt_den_uebergang_ab(self) -> None:
        """Eine inzwischen entarchivierte Fassung meldet den abgelehnten Übergang."""
        erster_tab: Vignette = finale_vignette(self.ada)
        erster_tab.archivieren()
        zweiter_tab: Vignette = Vignette.objects.get(pk=erster_tab.pk)
        erster_tab.entarchivieren()

        with self.assertRaisesMessage(
            ValidationError, "Nur archivierte Fassungen können entarchiviert werden."
        ):
            zweiter_tab.entarchivieren()

    def test_finalisieren_lehnt_nichtpositives_budget_ab(self) -> None:
        """Ein Gesprächsbudget muss mindestens einen Schritt oder eine Zeit tragen."""
        vignette: Vignette = _vollstaendiger_entwurf(self.ada)
        vignette.budget_wert = 0

        with self.assertRaisesMessage(ValidationError, "größer als 0"):
            vignette.finalisieren()

    def test_finalisieren_laesst_ueberholten_kern_pin_zu(self) -> None:
        """Ein überholter Pin hält niemanden auf; Vorspulen ist eine Wahl."""
        vignette: Vignette = _vollstaendiger_entwurf(self.ada)
        vignette.gepinnter_kern.bearbeiten().finalisieren()

        vignette.finalisieren()

        vignette.refresh_from_db()
        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)
        self.assertEqual(
            vignette.gepinnter_kern.zustand, Simulationskern.Zustand.ARCHIVIERT
        )

    def test_finalisieren_lehnt_fehlenden_kern_pin_ab(self) -> None:
        """Ohne gepinnten Kern gäbe es zur Spielzeit kein Gesprächsverhalten."""
        vignette: Vignette = _vollstaendiger_entwurf(self.ada)
        vignette.gepinnter_kern = None
        vignette.save()

        with self.assertRaisesMessage(ValidationError, "fehlt ein gepinnter"):
            vignette.finalisieren()


_TEILE: list[tuple[str, str]] = [
    ("lernauftrag", "Lernauftrag"),
    ("arbeitsheft", "Arbeitsheft"),
]


@pytest.mark.django_db
@pytest.mark.parametrize(("teil", "label"), _TEILE)
def test_finalisieren_lehnt_leeren_teil_ab(teil: str, label: str) -> None:
    """Jeder Teil des Aufgabenkontexts braucht sichtbar Text oder ein Bild."""

    vignette: Vignette = _vollstaendiger_entwurf(konto_mit_rollen("ada"))
    setattr(vignette, f"{teil}_text", "")

    with pytest.raises(ValidationError, match=f"{label} Text oder ein Bild"):
        vignette.finalisieren()


@pytest.mark.django_db
@pytest.mark.parametrize("teil", ["lernauftrag", "arbeitsheft"])
def test_finalisieren_nimmt_teil_nur_mit_bild_an(teil: str) -> None:
    """Ein Bild mit Beschreibung erfüllt die Alternative ohne Text."""

    vignette: Vignette = _vollstaendiger_entwurf(konto_mit_rollen("ada"))
    setattr(vignette, f"{teil}_text", "")
    setattr(vignette, f"{teil}_bild", "vignettenbilder/blatt.gif")
    setattr(vignette, f"{teil}_bildbeschreibung", "Blatt mit Zahlenreihe")

    vignette.finalisieren()

    assert vignette.zustand == Vignette.Zustand.FINAL


@pytest.mark.django_db
@pytest.mark.parametrize("teil", ["lernauftrag", "arbeitsheft"])
def test_finalisieren_erlaubt_leere_bildbeschreibung_ohne_bild(teil: str) -> None:
    """Eine Bildbeschreibung ist nur zusammen mit einem Bild erforderlich."""

    vignette: Vignette = _vollstaendiger_entwurf(konto_mit_rollen("ada"))
    setattr(vignette, f"{teil}_bildbeschreibung", "")

    vignette.finalisieren()

    assert vignette.zustand == Vignette.Zustand.FINAL


@pytest.mark.django_db
@pytest.mark.parametrize(("teil", "label"), _TEILE)
def test_finalisieren_braucht_bildbeschreibung_mit_bild(teil: str, label: str) -> None:
    """Ein sichtbares Bild ist ohne seinen Alt-Text nicht finalisierbar."""

    vignette: Vignette = _vollstaendiger_entwurf(konto_mit_rollen("ada"))
    setattr(vignette, f"{teil}_bild", "vignettenbilder/blatt.gif")
    setattr(vignette, f"{teil}_bildbeschreibung", "")

    with pytest.raises(ValidationError, match=f"{label}-Bild"):
        vignette.finalisieren()


class VignetteBearbeitenTests(TestCase):
    """Das Bearbeiten erzeugt eine neue, unveränderte Entwurfsfassung."""

    def setUp(self) -> None:
        """Legt die Autorin der Fassungen an."""
        self.ada: Konto = konto_mit_rollen("ada")

    def test_bearbeiten_erbt_pin_und_akteure_ohne_finale_zu_mutieren(self) -> None:
        """Der Folgeentwurf übernimmt alle Inhalte; die Quelle bleibt final."""
        finale: Vignette = finale_vignette(
            self.ada,
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            lernauftrag_bild="vignettenbilder/auftrag.gif",
            lernauftrag_bildbeschreibung="Arbeitsblatt mit Addition",
            lernauftrag_simulationshinweise="Zusatzhinweis zum Lernauftrag",
            arbeitsheft_text="27 + 15 = 312",
            arbeitsheft_bild="vignettenbilder/heft.gif",
            arbeitsheft_bildbeschreibung="Heftseite mit 312",
            arbeitsheft_simulationshinweise="Zusatzhinweis zum Arbeitsheft",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Herr Koch",
            lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            referenzdiagnose="Stellenwerte werden nicht ausgerichtet.",
            budget_typ=Vignette.BudgetTyp.ZEIT,
            budget_wert=5,
        )
        finale.schuelerin_name = "Nicht gespeicherter Name"

        entwurf: Vignette = finale.bearbeiten()

        self.assertEqual(
            {
                "zustand": entwurf.zustand,
                "historie": entwurf.historie,
                "vorgaengerin": entwurf.vorgaengerin,
                "gepinnter_kern": entwurf.gepinnter_kern,
                "fehlermuster_beschreibung": entwurf.fehlermuster_beschreibung,
                "lernauftrag_text": entwurf.lernauftrag_text,
                "lernauftrag_bild": entwurf.lernauftrag_bild.name,
                "lernauftrag_bildbeschreibung": entwurf.lernauftrag_bildbeschreibung,
                "lernauftrag_simulationshinweise": (
                    entwurf.lernauftrag_simulationshinweise
                ),
                "arbeitsheft_text": entwurf.arbeitsheft_text,
                "arbeitsheft_bild": entwurf.arbeitsheft_bild.name,
                "arbeitsheft_bildbeschreibung": entwurf.arbeitsheft_bildbeschreibung,
                "arbeitsheft_simulationshinweise": (
                    entwurf.arbeitsheft_simulationshinweise
                ),
                "schuelerin_name": entwurf.schuelerin_name,
                "schuelerin_geschlecht": entwurf.schuelerin_geschlecht,
                "lehrperson_name": entwurf.lehrperson_name,
                "lehrperson_geschlecht": entwurf.lehrperson_geschlecht,
                "fach": entwurf.fach,
                "thema": entwurf.thema,
                "klassenstufe": entwurf.klassenstufe,
                "referenzdiagnose": entwurf.referenzdiagnose,
                "budget_typ": entwurf.budget_typ,
                "budget_wert": entwurf.budget_wert,
            },
            {
                "zustand": "entwurf",
                "historie": finale.historie,
                "vorgaengerin": finale,
                "gepinnter_kern": finaler_kern(),
                "fehlermuster_beschreibung": "Zählt die Stellenwerte einzeln.",
                "lernauftrag_text": "Addiere 27 und 15.",
                "lernauftrag_bild": "vignettenbilder/auftrag.gif",
                "lernauftrag_bildbeschreibung": "Arbeitsblatt mit Addition",
                "lernauftrag_simulationshinweise": "Zusatzhinweis zum Lernauftrag",
                "arbeitsheft_text": "27 + 15 = 312",
                "arbeitsheft_bild": "vignettenbilder/heft.gif",
                "arbeitsheft_bildbeschreibung": "Heftseite mit 312",
                "arbeitsheft_simulationshinweise": "Zusatzhinweis zum Arbeitsheft",
                "schuelerin_name": "Mia",
                "schuelerin_geschlecht": "weiblich",
                "lehrperson_name": "Herr Koch",
                "lehrperson_geschlecht": "männlich",
                "fach": "Mathematik",
                "thema": "Addition",
                "klassenstufe": "5",
                "referenzdiagnose": "Stellenwerte werden nicht ausgerichtet.",
                "budget_typ": "zeit",
                "budget_wert": 5,
            },
        )
        finale.refresh_from_db()
        self.assertEqual(finale.zustand, Vignette.Zustand.FINAL)

    def test_bearbeiten_lehnt_finale_fassung_mit_nicht_archivierter_nachfolgerin_ab(
        self,
    ) -> None:
        """Eine Historie bleibt linear, statt den Datenbank-Constraint auszulösen."""
        finale: Vignette = finale_vignette(self.ada)
        finale.bearbeiten().finalisieren()

        with self.assertRaisesMessage(ValidationError, "Nachfolgerin"):
            finale.bearbeiten()

    def test_bearbeiten_lehnt_fassung_mit_aktiver_spaeterer_fassung_ab(
        self,
    ) -> None:
        """Eine archivierte Zwischenspitze gibt ältere Fassungen nicht frei."""
        erste: Vignette = finale_vignette(self.ada)
        zweite: Vignette = erste.bearbeiten()
        zweite.finalisieren()
        zweite.bearbeiten().finalisieren()
        zweite.archivieren()

        with self.assertRaisesMessage(ValidationError, "Nachfolgerin"):
            erste.bearbeiten()

    def test_vorspulen_aktualisiert_nur_den_pin_eines_entwurfs(self) -> None:
        """Der Kern-Pin wechselt ausschließlich auf ausdrücklichen Aufruf im Entwurf."""
        entwurf: Vignette = vignetten_entwurf(self.ada)
        neuester_kern: Simulationskern = entwurf.gepinnter_kern.bearbeiten()
        neuester_kern.finalisieren()

        entwurf.vorspulen()

        entwurf.refresh_from_db()
        self.assertEqual(entwurf.gepinnter_kern, neuester_kern)

    def test_finale_fassung_kann_archiviert_und_entarchiviert_werden(self) -> None:
        """Die beiden Archiv-Kanten ändern nur den Zustand der finalen Fassung."""
        vignette: Vignette = finale_vignette(self.ada)

        with self.assertRaisesMessage(ValidationError, "Entwürfe"):
            vignette.vorspulen()

        vignette.archivieren()

        self.assertEqual(vignette.zustand, Vignette.Zustand.ARCHIVIERT)
        with self.assertRaisesMessage(ValidationError, "Entwürfe"):
            vignette.vorspulen()
        vignette.entarchivieren()
        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)

    def test_nur_entwuerfe_duerfen_physisch_geloescht_werden(self) -> None:
        """Finale und archivierte Fassungen bleiben als Datenspur erhalten."""
        finale: Vignette = finale_vignette(self.ada)
        entwurf: Vignette = finale.bearbeiten()

        entwurf.delete()
        with self.assertRaises(ValidationError):
            finale.delete()
        finale.archivieren()
        with self.assertRaises(ValidationError):
            finale.delete()
        with self.assertRaises(ValidationError):
            Vignette.objects.filter(pk=finale.pk).delete()

    def test_letzte_fassung_nimmt_ihre_historie_mit(self) -> None:
        """Eine Historie ohne Fassung trägt nichts mehr und bleibt nicht zurück."""
        entwurf: Vignette = vignetten_entwurf(self.ada)
        historie: Vignettenhistorie = entwurf.historie

        entwurf.delete()

        self.assertFalse(Vignettenhistorie.objects.filter(pk=historie.pk).exists())

    def test_historie_mit_weiterer_fassung_bleibt_bestehen(self) -> None:
        """Nur die leer gewordene Historie wird abgeräumt, keine belegte."""
        finale: Vignette = finale_vignette(self.ada)
        entwurf: Vignette = finale.bearbeiten()

        entwurf.delete()

        self.assertTrue(
            Vignettenhistorie.objects.filter(pk=finale.historie.pk).exists()
        )

    def test_massenloeschung_raeumt_leer_gewordene_historien_ab(self) -> None:
        """Auch der QuerySet-Weg hinterlässt keine fassungslose Historie."""
        historien: list[Vignettenhistorie] = [
            vignetten_entwurf(self.ada).historie for _ in range(2)
        ]

        Vignette.objects.filter(zustand=Vignette.Zustand.ENTWURF).delete()

        self.assertFalse(
            Vignettenhistorie.objects.filter(
                pk__in=[historie.pk for historie in historien]
            ).exists()
        )

    def test_zustandswechsel_sind_auf_lebenszyklus_methoden_beschraenkt(self) -> None:
        """Direkte ORM-Saves dürfen keine Kante des Automaten umgehen."""
        entwurf: Vignette = vignetten_entwurf(self.ada)
        entwurf.zustand = Vignette.Zustand.ARCHIVIERT

        with self.assertRaisesMessage(ValidationError, "Zustandswechsel"):
            entwurf.save(update_fields=["zustand"])


class VignetteGespraechsbudgetTests(TestCase):
    """Die Vignette sagt, ob ihr Gesprächsbudget eine Uhr trägt."""

    def test_zeitbudget_traegt_eine_uhr(self) -> None:
        """Bei Zeitbegrenzung misst die Uhr den Zug der Teilnehmer:in."""
        vignette: Vignette = Vignette(budget_typ=Vignette.BudgetTyp.ZEIT)

        self.assertTrue(vignette.uhr_laeuft)

    def test_schrittbudget_traegt_keine_uhr(self) -> None:
        """Ein schrittbasiertes Budget zählt Schritte, es misst keine Zeit."""
        vignette: Vignette = Vignette(budget_typ=Vignette.BudgetTyp.SCHRITTE)

        self.assertFalse(vignette.uhr_laeuft)

    def test_entwurf_ohne_budget_typ_traegt_eine_uhr(self) -> None:
        """Erst das schrittbasierte Maß hält die Uhr an, nicht schon sein Fehlen."""
        vignette: Vignette = Vignette()

        self.assertTrue(vignette.uhr_laeuft)

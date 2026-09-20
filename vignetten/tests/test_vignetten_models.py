"""ORM-Tests für Vignetten und ihre Historien."""

from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase
from django.utils import timezone

from konten.models import Konto
from simulation.models import Simulationskern
from vignetten.models import (
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
        arbeitsheft_text="8 + 4 = 12 [BILD] Also ist die Lösung 7. [bild]",
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
            "<arbeitsheft_text>8 + 4 = 12 </arbeitsheft_text>\n"
            "<arbeitsheft_bildbeschreibung>Heftseite mit durchgestrichener 12."
            "</arbeitsheft_bildbeschreibung>\n"
            "<arbeitsheft_text> Also ist die Lösung 7. </arbeitsheft_text>\n"
            "</arbeitsheft>"
        ),
        "lernauftrag_simulationshinweise": "",
        "arbeitsheft_simulationshinweise": "",
        "schuelerin_name": "Mia",
        "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "fach": "Mathematik",
        "thema": "Brüche",
        "klassenstufe": "5",
    }


def test_prompt_platzhalter_ordnet_lernauftrag_text_und_bildbeschreibung() -> None:
    """Der komponierte Lernauftrag folgt dem ersten Positionsmarker."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            lernauftrag_text="Rechne zuerst. [BILD] Begründe danach. [bild]",
            lernauftrag_bild="vignettenbilder/auftrag.gif",
            lernauftrag_bildbeschreibung="Arbeitsblatt mit einer Zahlenreihe.",
        )
    )

    assert platzhalter["lernauftrag"] == (
        "<lernauftrag>\n"
        "<lernauftrag_text>Rechne zuerst. </lernauftrag_text>\n"
        "<lernauftrag_bildbeschreibung>Arbeitsblatt mit einer Zahlenreihe."
        "</lernauftrag_bildbeschreibung>\n"
        "<lernauftrag_text> Begründe danach. </lernauftrag_text>\n"
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


def test_prompt_platzhalter_entfernt_marker_ohne_bild() -> None:
    """Ein unvollständiger Entwurf gibt den Marker nie an das Modell weiter."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(arbeitsheft_text="Oben [BILD] unten [bild]")
    )

    assert platzhalter["arbeitsheft"] == (
        "<arbeitsheft>\n"
        "<arbeitsheft_text>Oben  unten </arbeitsheft_text>\n"
        "</arbeitsheft>"
    )


def test_prompt_platzhalter_entfernt_lernauftrag_marker_ohne_bild() -> None:
    """Ein Lernauftrag ohne Bild gibt den Marker nie an das Modell weiter."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(lernauftrag_text="Oben [BILD] unten [bild]")
    )

    assert platzhalter["lernauftrag"] == (
        "<lernauftrag>\n"
        "<lernauftrag_text>Oben  unten </lernauftrag_text>\n"
        "</lernauftrag>"
    )


def test_prompt_platzhalter_ordnet_bild_ohne_marker_nach_dem_text() -> None:
    """Ohne Marker steht die Bildbeschreibung im Prompt nach dem Text."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            arbeitsheft_text="Rechnung oben",
            arbeitsheft_bild="vignettenbilder/heft.gif",
            arbeitsheft_bildbeschreibung="Durchgestrichene Rechnung",
        )
    )

    assert platzhalter["arbeitsheft"] == (
        "<arbeitsheft>\n"
        "<arbeitsheft_text>Rechnung oben</arbeitsheft_text>\n"
        "<arbeitsheft_bildbeschreibung>Durchgestrichene Rechnung"
        "</arbeitsheft_bildbeschreibung>\n"
        "</arbeitsheft>"
    )


def test_prompt_platzhalter_ordnet_lernauftrag_bild_ohne_marker_nach_dem_text() -> None:
    """Ohne Marker steht die Lernauftrag-Bildbeschreibung im Prompt nach dem Text."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            lernauftrag_text="Aufgabe oben",
            lernauftrag_bild="vignettenbilder/auftrag.gif",
            lernauftrag_bildbeschreibung="Arbeitsblatt mit Skizze",
        )
    )

    assert platzhalter["lernauftrag"] == (
        "<lernauftrag>\n"
        "<lernauftrag_text>Aufgabe oben</lernauftrag_text>\n"
        "<lernauftrag_bildbeschreibung>Arbeitsblatt mit Skizze"
        "</lernauftrag_bildbeschreibung>\n"
        "</lernauftrag>"
    )


def test_prompt_platzhalter_laesst_leere_textstuecke_weg() -> None:
    """Ein Arbeitsheft nur mit Bild erzeugt keine leere Textumgebung."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            arbeitsheft_bild="vignettenbilder/heft.gif",
            arbeitsheft_bildbeschreibung="Durchgestrichene Rechnung",
        )
    )

    assert platzhalter["arbeitsheft"] == (
        "<arbeitsheft>\n"
        "<arbeitsheft_bildbeschreibung>Durchgestrichene Rechnung"
        "</arbeitsheft_bildbeschreibung>\n"
        "</arbeitsheft>"
    )


def test_prompt_platzhalter_laesst_leere_lernauftrag_textstuecke_weg() -> None:
    """Ein Lernauftrag nur mit Bild erzeugt keine leere Textumgebung."""

    platzhalter: dict[str, str] = prompt_platzhalter(
        Vignette(
            lernauftrag_bild="vignettenbilder/auftrag.gif",
            lernauftrag_bildbeschreibung="Arbeitsblatt mit Skizze",
        )
    )

    assert platzhalter["lernauftrag"] == (
        "<lernauftrag>\n"
        "<lernauftrag_bildbeschreibung>Arbeitsblatt mit Skizze"
        "</lernauftrag_bildbeschreibung>\n"
        "</lernauftrag>"
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
        "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "lehrperson_name": "Koch",
        "lehrperson_geschlecht": Vignette.Geschlecht.WEIBLICH,
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
        lehrperson_geschlecht="",
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

    def test_anlegen_vergibt_akteure(self) -> None:
        """Ein neuer Entwurf trägt ohne Formular beide Akteure."""
        vignette: Vignette
        vignette, _, _ = self._vignette_mit_zwei_finalen_kernen_anlegen()

        self.assertTrue(vignette.schuelerin_name)
        self.assertIn(vignette.schuelerin_geschlecht, Vignette.Geschlecht.values)
        self.assertTrue(vignette.lehrperson_name)
        self.assertIn(vignette.lehrperson_geschlecht, Vignette.Geschlecht.values)


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
                    Vignette.objects._erstellen(
                        historie=Vignettenhistorie.objects.create(), **werte
                    )

    def test_historie_hat_hoechstens_einen_entwurf(self) -> None:
        """Ein zweiter Entwurf derselben Historie scheitert am Unique-Index."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        Vignette.objects._erstellen(historie=historie)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects._erstellen(historie=historie)

    def test_finalisiert_am_muss_genau_dem_zustand_entsprechen(self) -> None:
        """Eine finale Fassung darf keinen leeren Finalisierungszeitpunkt haben."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects._erstellen(
                historie=Vignettenhistorie.objects.create(),
                zustand=Vignette.Zustand.FINAL,
                arbeitsheft_text="Bearbeitung",
            )

    def test_entwurf_darf_keinen_finalisierungszeitpunkt_haben(self) -> None:
        """Ein Entwurf kann keinen bereits gesetzten Finalisierungszeitpunkt tragen."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects._erstellen(
                historie=Vignettenhistorie.objects.create(),
                finalisiert_am=timezone.now(),
            )

    def test_entarchivieren_zu_einer_schwester_wird_verhindert(self) -> None:
        """Eine archivierte Schwester kann nicht erneut final werden."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        finalisiert_am: datetime = timezone.now()
        vorgaengerin: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        Vignette.objects._erstellen(
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        archivierte_schwester: Vignette = Vignette.objects._erstellen(
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=finalisiert_am,
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            archivierte_schwester.entarchivieren()

    def test_finale_fassung_braucht_arbeitsheft_text_oder_bild(self) -> None:
        """Die Arbeitsheft-OR-Constraint schützt finale Fassungen."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects._erstellen(
                historie=Vignettenhistorie.objects.create(),
                zustand=Vignette.Zustand.FINAL,
                finalisiert_am=timezone.now(),
            )


@pytest.mark.django_db(transaction=True)
def test_geschlechter_migration_fuellt_leere_bestandswerte_auf() -> None:
    """Die Pflicht-Constraint-Migration bleibt für alte Entwürfe installierbar."""

    vorher: list[tuple[str, str]] = [
        ("vignetten", "0006_vignette_arbeitsheft_simulationshinweise_and_more")
    ]
    nachher: list[tuple[str, str]] = MigrationExecutor(
        connection
    ).loader.graph.leaf_nodes()
    executor = MigrationExecutor(connection)
    executor.migrate(vorher)
    try:
        apps = executor.loader.project_state(vorher).apps
        Historie = apps.get_model("vignetten", "Vignettenhistorie")
        VignetteVorher = apps.get_model("vignetten", "Vignette")
        alte_fassung = VignetteVorher.objects.create(
            historie=Historie.objects.create(),
            schuelerin_geschlecht="",
            lehrperson_geschlecht="",
        )

        executor = MigrationExecutor(connection)
        executor.migrate([("vignetten", "0007_geschlechter_nicht_leer")])
        apps = executor.loader.project_state(
            [("vignetten", "0007_geschlechter_nicht_leer")]
        ).apps
        VignetteNachher = apps.get_model("vignetten", "Vignette")
        migrierte_fassung = VignetteNachher.objects.get(pk=alte_fassung.pk)
    finally:
        MigrationExecutor(connection).migrate(nachher)

    assert migrierte_fassung.schuelerin_geschlecht == Vignette.Geschlecht.WEIBLICH
    assert migrierte_fassung.lehrperson_geschlecht == Vignette.Geschlecht.WEIBLICH


class VignetteSichtbarFuerQuerySetTests(TestCase):
    """Die Sichtbarkeitsabfrage über Vignettenfassungen."""

    def setUp(self) -> None:
        """Erzeugt Fassungen für verschiedene Sichtbarkeitsrollen."""
        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.grace: Konto = get_user_model().objects.create_user(username="grace")
        self.linus: Konto = get_user_model().objects.create_user(username="linus")
        self.dijkstra: Konto = get_user_model().objects.create_user(username="dijkstra")
        self.administratorin: Konto = get_user_model().objects.create_user(
            username="admin"
        )
        self.administratorin.is_superuser = True
        self.administratorin.save()

        eigene_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        eigene_historie.eigentuemerinnen.add(self.ada)
        self.eigene_fassung: Vignette = Vignette.objects._erstellen(
            historie=eigene_historie
        )
        geteilte_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        geteilte_historie.eigentuemerinnen.add(self.ada, self.grace)
        self.geteilte_finale: Vignette = Vignette.objects._erstellen(
            historie=geteilte_historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(self.linus)
        self.fremde_fassung: Vignette = Vignette.objects._erstellen(
            historie=fremde_historie
        )

    def test_sichtbar_fuer_liefert_eigene_und_geteilte_fassungen(self) -> None:
        """Eine Eigentümerin sieht eigene und geteilte Fassungen."""
        self.assertEqual(
            list(Vignette.objects.sichtbar_fuer(self.ada)),
            [self.eigene_fassung, self.geteilte_finale],
        )

    def test_sichtbar_fuer_liefert_koeigentuemerin_geteilte_fassung(self) -> None:
        """Eine Ko-Eigentümerin sieht die geteilte Fassung."""
        self.assertEqual(
            list(Vignette.objects.sichtbar_fuer(self.grace)), [self.geteilte_finale]
        )

    def test_sichtbar_fuer_liefert_dritter_ihre_fassung(self) -> None:
        """Eine nicht beteiligte Person sieht nur ihre eigene Fassung."""
        self.assertEqual(
            list(Vignette.objects.sichtbar_fuer(self.linus)), [self.fremde_fassung]
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
    """Die QuerySet-Methoden filtern Vignetten und ihre Historien."""

    def test_sichtbar_fuer_liefert_nur_den_eigentuemer_kreis(self) -> None:
        """Ko-Eigentümerinnen sehen dieselbe Historie, fremde Konten nicht."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        linus: Konto = get_user_model().objects.create_user(username="linus")
        geteilte_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        geteilte_historie.eigentuemerinnen.add(ada, grace)
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(linus)

        self.assertEqual(
            list(Vignettenhistorie.objects.sichtbar_fuer(grace)), [geteilte_historie]
        )

    def test_sichtbar_fuer_liefert_alle_historien_fuer_administration(self) -> None:
        """Die Administration sieht auch fremde Vignettenhistorien."""
        administratorin: Konto = get_user_model().objects.create_user(username="admin")
        administratorin.is_superuser = True
        administratorin.save()
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(
            get_user_model().objects.create_user(username="linus")
        )

        self.assertEqual(
            list(Vignettenhistorie.objects.sichtbar_fuer(administratorin)),
            [fremde_historie],
        )

    def test_einbindbar_liefert_nur_finale_fassungen(self) -> None:
        """Entwürfe und archivierte Fassungen sind nicht einbindbar."""
        Vignette.objects._erstellen(historie=Vignettenhistorie.objects.create())
        finale: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )
        Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
        )

        self.assertEqual(list(Vignette.objects.einbindbar()), [finale])

    def test_historie_archivieren_beruehrt_keine_fassung(self) -> None:
        """Das Archiv-Flag der Historie ist unabhängig vom Fassungslifecycle."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        vignette: Vignette = Vignette.objects._erstellen(historie=historie)

        historie.archiviert = True
        historie.save(update_fields=["archiviert"])

        vignette.refresh_from_db()
        self.assertTrue(historie.archiviert)
        self.assertEqual(vignette.zustand, Vignette.Zustand.ENTWURF)


class VignetteFinalisierenTests(TestCase):
    """Das Finalisieren prüft die Vignette über ihre öffentliche Modell-API."""

    def _vollstaendigen_entwurf_anlegen(
        self, kern_ueberholen: bool = False
    ) -> Vignette:
        # Erstellt einen vollständigen Entwurf, auf Wunsch mit überholtem Kern-Pin.
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        if kern_ueberholen:
            kern.bearbeiten().finalisieren()
        return Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            arbeitsheft_bildbeschreibung="27 + 15 = 312",
            arbeitsheft_text="27 + 15 = 312",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Frau Weber",
            lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=5,
            gepinnter_kern=kern,
        )

    def test_finalisieren_ueberfuehrt_vollstaendigen_entwurf_nach_final(self) -> None:
        """Eine vollständige Fassung wird final und erhält einen Zeitpunkt."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()

        vignette.finalisieren()

        vignette.refresh_from_db()
        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)
        self.assertIsNotNone(vignette.finalisiert_am)

    def test_finale_fassung_ist_unveraenderlich(self) -> None:
        """Inhalte einer finalen Fassung lassen sich nicht mehr überschreiben."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.finalisieren()
        vignette.lernauftrag_text = "Addiere 28 und 15."

        with self.assertRaises(ValidationError):
            vignette.save()

    def test_finalisiert_am_wird_nie_zurueckgesetzt(self) -> None:
        """Der Finalisierungszeitpunkt überlebt jede spätere Zustandsänderung."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.finalisieren()
        vignette.finalisiert_am = None

        with self.assertRaises(ValidationError):
            vignette.save()

    def test_finale_fassung_laesst_keine_massenmutation_zu(self) -> None:
        """Auch der QuerySet-Zugang kann eine finale Fassung nicht verändern."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.finalisieren()

        with self.assertRaises(RuntimeError):
            Vignette.objects.filter(pk=vignette.pk).update(lernauftrag_text="Verändert")

    def test_finalisieren_lehnt_nichtentwuerfe_ab(self) -> None:
        """Finalisieren ist ausschließlich die Kante vom Entwurf nach final."""
        finale: Vignette = self._vollstaendigen_entwurf_anlegen()
        finale.finalisieren()
        kern2: Simulationskern = finale.gepinnter_kern.bearbeiten()
        kern2.finalisieren()
        archivierte: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            arbeitsheft_bildbeschreibung="27 + 15 = 312",
            arbeitsheft_text="27 + 15 = 312",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Frau Weber",
            lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=5,
            gepinnter_kern=kern2,
        )
        archivierte.finalisieren()
        archivierte.archivieren()

        for vignette in (finale, archivierte):
            with self.subTest(zustand=vignette.zustand):
                with self.assertRaisesMessage(ValidationError, "Entwürfe"):
                    vignette.finalisieren()

    def test_finalisieren_lehnt_leeren_lernauftrag_ab(self) -> None:
        """Der Lernauftrag braucht sichtbar Text oder ein Bild."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.lernauftrag_text = ""

        with self.assertRaisesMessage(ValidationError, "Lernauftrag"):
            vignette.finalisieren()

    def test_finalisieren_nimmt_lernauftrag_nur_mit_bild_an(self) -> None:
        """Ein Bild allein erfüllt die Lernauftrag-Alternative."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.lernauftrag_text = ""
        vignette.lernauftrag_bild = "vignettenbilder/auftrag.gif"
        vignette.lernauftrag_bildbeschreibung = "Arbeitsblatt mit Zahlenreihe"

        vignette.finalisieren()

        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)

    def test_finalisieren_erlaubt_leere_lernauftrag_bildbeschreibung_ohne_bild(
        self,
    ) -> None:
        """Eine Lernauftrag-Bildbeschreibung ist ohne Bild nicht erforderlich."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.lernauftrag_bildbeschreibung = ""

        vignette.finalisieren()

        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)

    def test_finalisieren_braucht_lernauftrag_bildbeschreibung_mit_bild(self) -> None:
        """Ein Lernauftrag-Bild braucht beim Finalisieren seinen Alt-Text."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.lernauftrag_bild = "vignettenbilder/auftrag.gif"

        with self.assertRaisesMessage(ValidationError, "Lernauftrag-Bild"):
            vignette.finalisieren()

    def test_finalisieren_lehnt_leeres_arbeitsheft_ab(self) -> None:
        """Das Arbeitsheft braucht sichtbar Text oder ein Bild."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.arbeitsheft_text = ""

        with self.assertRaisesMessage(ValidationError, "Arbeitsheft"):
            vignette.finalisieren()

    def test_finalisieren_nimmt_arbeitsheft_nur_mit_bild_an(self) -> None:
        """Ein Bild allein erfüllt die Arbeitsheft-Alternative."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.arbeitsheft_text = ""
        vignette.arbeitsheft_bild = SimpleUploadedFile(
            "arbeitsheft.png", b"bild", content_type="image/png"
        )

        vignette.finalisieren()

        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)

    def test_finalisieren_erlaubt_leere_bildbeschreibung_ohne_bild(self) -> None:
        """Eine Beschreibung ist nur zusammen mit einem Bild erforderlich."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.arbeitsheft_bildbeschreibung = ""

        vignette.finalisieren()

        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)

    def test_finalisieren_braucht_bildbeschreibung_mit_bild(self) -> None:
        """Ein sichtbares Bild ist ohne seinen Alt-Text nicht finalisierbar."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.arbeitsheft_bild = "vignettenbilder/heft.gif"
        vignette.arbeitsheft_bildbeschreibung = ""

        with self.assertRaisesMessage(ValidationError, "Bildbeschreibung"):
            vignette.finalisieren()

    def test_finalisieren_lehnt_nichtpositives_budget_ab(self) -> None:
        """Ein Gesprächsbudget muss mindestens einen Schritt oder eine Zeit tragen."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.budget_wert = 0

        with self.assertRaisesMessage(ValidationError, "größer als 0"):
            vignette.finalisieren()

    def test_finalisieren_laesst_ueberholten_kern_pin_zu(self) -> None:
        """Ein überholter Pin hält niemanden auf; Vorspulen ist eine Wahl."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen(kern_ueberholen=True)

        vignette.finalisieren()

        vignette.refresh_from_db()
        self.assertEqual(vignette.zustand, Vignette.Zustand.FINAL)
        self.assertEqual(
            vignette.gepinnter_kern.zustand, Simulationskern.Zustand.ARCHIVIERT
        )

    def test_finalisieren_lehnt_fehlenden_kern_pin_ab(self) -> None:
        """Ohne gepinnten Kern gäbe es zur Spielzeit kein Gesprächsverhalten."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.gepinnter_kern = None
        vignette.save()

        with self.assertRaisesMessage(ValidationError, "fehlt ein gepinnter"):
            vignette.finalisieren()


class VignetteBearbeitenTests(TestCase):
    """Das Bearbeiten erzeugt eine neue, unveränderte Entwurfsfassung."""

    def test_bearbeiten_erbt_pin_und_akteure_ohne_finale_zu_mutieren(self) -> None:
        """Eine finale Fassung bleibt beim Anlegen ihres Nachfolgeentwurfs erhalten."""
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        finale: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            lernauftrag_bild="vignettenbilder/auftrag.gif",
            lernauftrag_bildbeschreibung="Arbeitsblatt mit Addition",
            lernauftrag_simulationshinweise="Zusatzhinweis zum Lernauftrag",
            arbeitsheft_bildbeschreibung="27 + 15 = 312",
            arbeitsheft_text="27 + 15 = 312",
            arbeitsheft_bild="vignettenbilder/heft.gif",
            arbeitsheft_simulationshinweise="Zusatzhinweis zum Arbeitsheft",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Herr Koch",
            lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=5,
            gepinnter_kern=kern,
        )
        finale.finalisieren()
        finale.schuelerin_name = "Nicht gespeicherter Name"

        entwurf: Vignette = finale.bearbeiten()

        self.assertEqual(entwurf.zustand, Vignette.Zustand.ENTWURF)
        self.assertEqual(entwurf.historie, finale.historie)
        self.assertEqual(entwurf.vorgaengerin, finale)
        self.assertEqual(entwurf.gepinnter_kern, kern)
        self.assertEqual(entwurf.lernauftrag_bild.name, "vignettenbilder/auftrag.gif")
        self.assertEqual(
            entwurf.lernauftrag_bildbeschreibung, "Arbeitsblatt mit Addition"
        )
        self.assertEqual(
            entwurf.lernauftrag_simulationshinweise, "Zusatzhinweis zum Lernauftrag"
        )
        self.assertEqual(entwurf.arbeitsheft_bild.name, "vignettenbilder/heft.gif")
        self.assertEqual(entwurf.arbeitsheft_bildbeschreibung, "27 + 15 = 312")
        self.assertEqual(
            entwurf.arbeitsheft_simulationshinweise, "Zusatzhinweis zum Arbeitsheft"
        )
        self.assertEqual(entwurf.schuelerin_name, "Mia")
        self.assertEqual(entwurf.schuelerin_geschlecht, Vignette.Geschlecht.WEIBLICH)
        self.assertEqual(entwurf.lehrperson_name, "Herr Koch")
        self.assertEqual(entwurf.lehrperson_geschlecht, Vignette.Geschlecht.MAENNLICH)
        finale.refresh_from_db()
        self.assertEqual(finale.zustand, Vignette.Zustand.FINAL)

    def test_bearbeiten_lehnt_finale_fassung_mit_nicht_archivierter_nachfolgerin_ab(
        self,
    ) -> None:
        """Eine Historie bleibt linear, statt den Datenbank-Constraint auszulösen."""
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        finale: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
            gepinnter_kern=kern,
        )
        Vignette.objects._erstellen(
            historie=finale.historie,
            vorgaengerin=finale,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
            gepinnter_kern=kern,
        )

        with self.assertRaisesMessage(ValidationError, "Nachfolgerin"):
            finale.bearbeiten()

    def test_bearbeiten_lehnt_fassung_mit_aktiver_spaeterer_fassung_ab(
        self,
    ) -> None:
        """Eine archivierte Zwischenspitze gibt ältere Fassungen nicht frei."""
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        erste: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
            gepinnter_kern=kern,
        )
        zweite: Vignette = Vignette.objects._erstellen(
            historie=erste.historie,
            vorgaengerin=erste,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
            gepinnter_kern=kern,
        )
        Vignette.objects._erstellen(
            historie=erste.historie,
            vorgaengerin=zweite,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Lernauftrag",
            arbeitsheft_text="Bearbeitung",
            gepinnter_kern=kern,
        )
        zweite.archivieren()

        with self.assertRaisesMessage(ValidationError, "Nachfolgerin"):
            erste.bearbeiten()

    def test_vorspulen_aktualisiert_nur_den_pin_eines_entwurfs(self) -> None:
        """Der Kern-Pin wechselt ausschließlich auf ausdrücklichen Aufruf im Entwurf."""
        erster_kern: Simulationskern = Simulationskern.objects.anlegen()
        erster_kern.finalisieren()
        neuester_kern: Simulationskern = erster_kern.bearbeiten()
        neuester_kern.finalisieren()
        entwurf: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            gepinnter_kern=erster_kern,
        )

        entwurf.vorspulen()

        entwurf.refresh_from_db()
        self.assertEqual(entwurf.gepinnter_kern, neuester_kern)

    def test_finale_fassung_kann_archiviert_und_entarchiviert_werden(self) -> None:
        """Die beiden Archiv-Kanten ändern nur den Zustand der finalen Fassung."""
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        vignette: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            arbeitsheft_bildbeschreibung="27 + 15 = 312",
            arbeitsheft_text="27 + 15 = 312",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Herr Koch",
            lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=5,
            gepinnter_kern=kern,
        )
        vignette.finalisieren()

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
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        finale: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            arbeitsheft_bildbeschreibung="27 + 15 = 312",
            arbeitsheft_text="27 + 15 = 312",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Herr Koch",
            lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=5,
            gepinnter_kern=kern,
        )
        finale.finalisieren()
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
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        entwurf: Vignette = Vignette.objects._erstellen(historie=historie)

        entwurf.delete()

        self.assertFalse(Vignettenhistorie.objects.filter(pk=historie.pk).exists())

    def test_historie_mit_weiterer_fassung_bleibt_bestehen(self) -> None:
        """Nur die leer gewordene Historie wird abgeräumt, keine belegte."""
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        finale: Vignette = Vignette.objects._erstellen(
            historie=historie,
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag_text="Addiere 27 und 15.",
            arbeitsheft_bildbeschreibung="27 + 15 = 312",
            arbeitsheft_text="27 + 15 = 312",
            schuelerin_name="Mia",
            schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
            lehrperson_name="Herr Koch",
            lehrperson_geschlecht=Vignette.Geschlecht.MAENNLICH,
            fach="Mathematik",
            thema="Addition",
            klassenstufe="5",
            budget_typ=Vignette.BudgetTyp.SCHRITTE,
            budget_wert=5,
            gepinnter_kern=kern,
        )
        finale.finalisieren()
        entwurf: Vignette = finale.bearbeiten()

        entwurf.delete()

        self.assertTrue(Vignettenhistorie.objects.filter(pk=historie.pk).exists())

    def test_massenloeschung_raeumt_leer_gewordene_historien_ab(self) -> None:
        """Auch der QuerySet-Weg hinterlässt keine fassungslose Historie."""
        historien: list[Vignettenhistorie] = [
            Vignettenhistorie.objects.create() for _ in range(2)
        ]
        for historie in historien:
            Vignette.objects._erstellen(historie=historie)

        Vignette.objects.filter(zustand=Vignette.Zustand.ENTWURF).delete()

        self.assertFalse(
            Vignettenhistorie.objects.filter(
                pk__in=[historie.pk for historie in historien]
            ).exists()
        )

    def test_zustandswechsel_sind_auf_lebenszyklus_methoden_beschraenkt(self) -> None:
        """Direkte ORM-Saves dürfen keine Kante des Automaten umgehen."""
        entwurf: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
        )
        entwurf.zustand = Vignette.Zustand.ARCHIVIERT

        with self.assertRaisesMessage(ValidationError, "Zustandswechsel"):
            entwurf.save(update_fields=["zustand"])

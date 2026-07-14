"""ORM-Tests für Vignetten und ihre Historien."""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
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


def test_prompt_platzhalter_enthaelt_alle_rohen_prompt_werte() -> None:
    """Der Prompt erhält genau die vorgesehenen Vignettenfelder ohne Ableitungen."""

    vignette: Vignette = Vignette(
        zustand=Vignette.Zustand.FINAL,
        fehlermuster_beschreibung="Brüche werden addiert.",
        lernauftrag="Addiere zwei Brüche.",
        arbeitsheft_beschreibung="1/2 + 1/3 = 2/5",
        schuelerin_name="Mia",
        schuelerin_geschlecht=Vignette.Geschlecht.WEIBLICH,
        fach="Mathematik",
        thema="Brüche",
        klassenstufe="5",
    )

    assert prompt_platzhalter(vignette) == {
        "fehlermuster_beschreibung": "Brüche werden addiert.",
        "lernauftrag": "Addiere zwei Brüche.",
        "arbeitsheft_beschreibung": "1/2 + 1/3 = 2/5",
        "schuelerin_name": "Mia",
        "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "fach": "Mathematik",
        "thema": "Brüche",
        "klassenstufe": "5",
    }


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
        vignette, _, neuester_kern = (
            self._vignette_mit_zwei_finalen_kernen_anlegen()
        )

        self.assertEqual(vignette.gepinnter_kern, neuester_kern)

    def test_anlegen_traegt_konto_als_eigentuemerin_ein(self) -> None:
        """Die anlegende Person gehört zur neuen Vignettenhistorie."""
        vignette: Vignette
        konto: Konto
        vignette, konto, _ = self._vignette_mit_zwei_finalen_kernen_anlegen()

        self.assertEqual(list(vignette.historie.eigentuemerinnen.all()), [konto])


class VignetteConstraintTests(TestCase):
    """Die Datenbank schützt die gemeinsame Lebenszyklus-Form."""

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
            arbeitsheft_text="Bearbeitung",
        )
        Vignette.objects._erstellen(
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
            arbeitsheft_text="Bearbeitung",
        )
        archivierte_schwester: Vignette = Vignette.objects._erstellen(
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=finalisiert_am,
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

    def test_einbindbar_liefert_nur_finale_fassungen(self) -> None:
        """Entwürfe und archivierte Fassungen sind nicht einbindbar."""
        Vignette.objects._erstellen(historie=Vignettenhistorie.objects.create())
        finale: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="Bearbeitung",
        )
        Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=timezone.now(),
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
        self,
        kern_zustand: Simulationskern.Zustand = Simulationskern.Zustand.FINAL,
    ) -> Vignette:
        # Erstellt einen vollständigen Entwurf mit einem Kern im gewünschten Zustand.
        kern: Simulationskern = Simulationskern.objects.anlegen()
        if kern_zustand != Simulationskern.Zustand.ENTWURF:
            kern.finalisieren()
        if kern_zustand == Simulationskern.Zustand.ARCHIVIERT:
            kern.archivieren()
        return Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag="Addiere 27 und 15.",
            arbeitsheft_beschreibung="27 + 15 = 312",
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
        vignette.lernauftrag = "Addiere 28 und 15."

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
            Vignette.objects.filter(pk=vignette.pk).update(lernauftrag="Verändert")

    def test_finalisieren_lehnt_nichtentwuerfe_ab(self) -> None:
        """Finalisieren ist ausschließlich die Kante vom Entwurf nach final."""
        finale: Vignette = self._vollstaendigen_entwurf_anlegen()
        finale.finalisieren()
        kern2: Simulationskern = finale.gepinnter_kern.bearbeiten()
        kern2.finalisieren()
        archivierte: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag="Addiere 27 und 15.",
            arbeitsheft_beschreibung="27 + 15 = 312",
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

    def test_finalisieren_nennt_fehlendes_pflichtfeld(self) -> None:
        """Unvollständige Entwürfe erklären, welches Feld ergänzt werden muss."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.lernauftrag = ""

        with self.assertRaisesMessage(ValidationError, "lernauftrag"):
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

    def test_finalisieren_lehnt_nichtpositives_budget_ab(self) -> None:
        """Ein Gesprächsbudget muss mindestens einen Schritt oder eine Zeit tragen."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen()
        vignette.budget_wert = 0

        with self.assertRaisesMessage(ValidationError, "größer als 0"):
            vignette.finalisieren()

    def test_finalisieren_lehnt_entwurfs_kern_pin_ab(self) -> None:
        """Nur ein finaler Simulationskern kann dauerhaft gepinnt werden."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen(
            Simulationskern.Zustand.ENTWURF
        )

        with self.assertRaisesMessage(ValidationError, "nicht final"):
            vignette.finalisieren()

    def test_finalisieren_verweist_bei_archiviertem_kern_aufs_vorspulen(
        self,
    ) -> None:
        """Ein überholter Pin erklärt Autor:innen die nächste Handlung."""
        vignette: Vignette = self._vollstaendigen_entwurf_anlegen(
            Simulationskern.Zustand.ARCHIVIERT
        )

        with self.assertRaisesMessage(ValidationError, "archiviert") as fehler:
            vignette.finalisieren()

        self.assertIn("vorspulen", str(fehler.exception))


class VignetteBearbeitenTests(TestCase):
    """Das Bearbeiten erzeugt eine neue, unveränderte Entwurfsfassung."""

    def test_bearbeiten_erbt_pin_und_akteure_ohne_finale_zu_mutieren(self) -> None:
        """Eine finale Fassung bleibt beim Anlegen ihres Nachfolgeentwurfs erhalten."""
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        finale: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
            fehlermuster_beschreibung="Zählt die Stellenwerte einzeln.",
            lernauftrag="Addiere 27 und 15.",
            arbeitsheft_beschreibung="27 + 15 = 312",
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
        finale.schuelerin_name = "Nicht gespeicherter Name"

        entwurf: Vignette = finale.bearbeiten()

        self.assertEqual(entwurf.zustand, Vignette.Zustand.ENTWURF)
        self.assertEqual(entwurf.historie, finale.historie)
        self.assertEqual(entwurf.vorgaengerin, finale)
        self.assertEqual(entwurf.gepinnter_kern, kern)
        self.assertEqual(entwurf.schuelerin_name, "Mia")
        self.assertEqual(entwurf.schuelerin_geschlecht, Vignette.Geschlecht.WEIBLICH)
        self.assertEqual(entwurf.lehrperson_name, "Herr Koch")
        self.assertEqual(entwurf.lehrperson_geschlecht, Vignette.Geschlecht.MAENNLICH)
        finale.refresh_from_db()
        self.assertEqual(finale.zustand, Vignette.Zustand.FINAL)

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
            lernauftrag="Addiere 27 und 15.",
            arbeitsheft_beschreibung="27 + 15 = 312",
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
            lernauftrag="Addiere 27 und 15.",
            arbeitsheft_beschreibung="27 + 15 = 312",
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

    def test_zustandswechsel_sind_auf_lebenszyklus_methoden_beschraenkt(self) -> None:
        """Direkte ORM-Saves dürfen keine Kante des Automaten umgehen."""
        entwurf: Vignette = Vignette.objects._erstellen(
            historie=Vignettenhistorie.objects.create(),
        )
        entwurf.zustand = Vignette.Zustand.ARCHIVIERT

        with self.assertRaisesMessage(ValidationError, "Zustandswechsel"):
            entwurf.save(update_fields=["zustand"])

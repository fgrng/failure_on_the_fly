"""ORM-Tests für Vignetten und ihre Historien."""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from konten.models import Konto
from simulation.models import Simulationskern
from vignetten.models import Vignette, Vignettenhistorie, rahmen_platzhalter


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
        Vignette.objects.create(historie=historie)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects.create(historie=historie)

    def test_finalisiert_am_muss_genau_dem_zustand_entsprechen(self) -> None:
        """Eine finale Fassung darf keinen leeren Finalisierungszeitpunkt haben."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects.create(
                historie=Vignettenhistorie.objects.create(),
                zustand=Vignette.Zustand.FINAL,
                arbeitsheft_text="Bearbeitung",
            )

    def test_entwurf_darf_keinen_finalisierungszeitpunkt_haben(self) -> None:
        """Ein Entwurf kann keinen bereits gesetzten Finalisierungszeitpunkt tragen."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects.create(
                historie=Vignettenhistorie.objects.create(),
                finalisiert_am=timezone.now(),
            )

    def test_entarchivieren_zu_einer_schwester_wird_verhindert(self) -> None:
        """Eine archivierte Schwester kann nicht erneut final werden."""
        historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        finalisiert_am: datetime = timezone.now()
        vorgaengerin: Vignette = Vignette.objects.create(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
            arbeitsheft_text="Bearbeitung",
        )
        Vignette.objects.create(
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
            arbeitsheft_text="Bearbeitung",
        )
        archivierte_schwester: Vignette = Vignette.objects.create(
            historie=historie,
            vorgaengerin=vorgaengerin,
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=finalisiert_am,
            arbeitsheft_text="Bearbeitung",
        )
        archivierte_schwester.zustand = Vignette.Zustand.FINAL

        with self.assertRaises(IntegrityError), transaction.atomic():
            archivierte_schwester.save()

    def test_finale_fassung_braucht_arbeitsheft_text_oder_bild(self) -> None:
        """Die Arbeitsheft-OR-Constraint schützt finale Fassungen."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vignette.objects.create(
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
        Vignette.objects.create(historie=Vignettenhistorie.objects.create())
        finale: Vignette = Vignette.objects.create(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="Bearbeitung",
        )
        Vignette.objects.create(
            historie=Vignettenhistorie.objects.create(),
            zustand=Vignette.Zustand.ARCHIVIERT,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="Bearbeitung",
        )

        self.assertEqual(list(Vignette.objects.einbindbar()), [finale])


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
        return Vignette.objects.create(
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
        archivierte: Vignette = Vignette.objects.create(
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
        archivierte.zustand = Vignette.Zustand.ARCHIVIERT
        archivierte.save(update_fields=["zustand"])

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

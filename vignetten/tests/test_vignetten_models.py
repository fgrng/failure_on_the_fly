"""ORM-Tests für Vignetten und ihre Historien."""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from konten.models import Konto
from simulation.models import KernHistorie, Simulationskern
from vignetten.models import Vignette, Vignettenhistorie


class VignetteAnlegenTests(TestCase):
    """Die Schreibnaht erzeugt eine vollständige neue Vignettenlinie."""

    def _anlegen(self) -> tuple[Vignette, Konto, Simulationskern]:
        # Erzeugt die öffentliche Schreibnaht mit zwei finalen Kernfassungen.
        konto: Konto = get_user_model().objects.create_user(username="ada")
        historie: KernHistorie = KernHistorie.objects.create()
        finalisiert_am: datetime = timezone.now()
        erster_kern: Simulationskern = Simulationskern.objects.create(
            historie=historie,
            zustand=Simulationskern.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
        )
        neuester_kern: Simulationskern = Simulationskern.objects.create(
            historie=historie,
            vorgaengerin=erster_kern,
            zustand=Simulationskern.Zustand.FINAL,
            finalisiert_am=finalisiert_am + timezone.timedelta(seconds=1),
        )
        vignette: Vignette = Vignette.objects.anlegen(konto)

        return vignette, konto, neuester_kern

    def test_anlegen_erstellt_entwurf(self) -> None:
        """Eine neue Vignette beginnt als Entwurf."""
        vignette: Vignette
        vignette, _, _ = self._anlegen()

        self.assertEqual(vignette.zustand, Vignette.Zustand.ENTWURF)

    def test_anlegen_pinnt_neuesten_finalen_kern(self) -> None:
        """Eine neue Vignette pinnt den neuesten finalen Simulationskern."""
        vignette: Vignette
        neuester_kern: Simulationskern
        vignette, _, neuester_kern = self._anlegen()

        self.assertEqual(vignette.gepinnter_kern, neuester_kern)

    def test_anlegen_traegt_konto_als_eigentuemerin_ein(self) -> None:
        """Die anlegende Person gehört zur neuen Vignettenhistorie."""
        vignette: Vignette
        konto: Konto
        vignette, konto, _ = self._anlegen()

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
    """Die Lesenähe bleibt an den zwei vereinbarten QuerySet-Nähten."""

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

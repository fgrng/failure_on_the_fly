"""ORM-Tests für Vignetten und ihre Historien."""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from simulation.models import KernHistorie, Simulationskern
from vignetten.models import Vignette, Vignettenhistorie


class VignetteAnlegenTests(TestCase):
    """Die Schreibnaht erzeugt eine vollständige neue Vignettenlinie."""

    def test_anlegen_erstellt_historie_entwurf_eigentuemerin_und_pin(self) -> None:
        """Eine neue Vignette pinnt den neuesten finalen Simulationskern."""
        konto = get_user_model().objects.create_user(username="ada")
        historie = KernHistorie.objects.create()
        finalisiert_am: datetime = timezone.now()
        Simulationskern.objects.create(
            historie=historie,
            zustand=Simulationskern.Zustand.FINAL,
            finalisiert_am=finalisiert_am,
        )
        neuester_kern = Simulationskern.objects.create(
            historie=historie,
            vorgaengerin=Simulationskern.objects.first(),
            zustand=Simulationskern.Zustand.FINAL,
            finalisiert_am=finalisiert_am + timezone.timedelta(seconds=1),
        )

        vignette = Vignette.objects.anlegen(konto)

        self.assertEqual(
            (
                vignette.zustand,
                vignette.gepinnter_kern,
                list(vignette.historie.eigentuemerinnen.all()),
            ),
            (Vignette.Zustand.ENTWURF, neuester_kern, [konto]),
        )


class VignetteConstraintTests(TestCase):
    """Die Datenbank schützt die gemeinsame Lebenszyklus-Form."""

    def test_historie_hat_hoechstens_einen_entwurf(self) -> None:
        """Ein zweiter Entwurf derselben Historie scheitert am Unique-Index."""
        historie = Vignettenhistorie.objects.create()
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
        ada = get_user_model().objects.create_user(username="ada")
        grace = get_user_model().objects.create_user(username="grace")
        linus = get_user_model().objects.create_user(username="linus")
        geteilte_historie = Vignettenhistorie.objects.create()
        geteilte_historie.eigentuemerinnen.add(ada, grace)
        fremde_historie = Vignettenhistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(linus)

        self.assertEqual(
            list(Vignettenhistorie.objects.sichtbar_fuer(grace)), [geteilte_historie]
        )

    def test_einbindbar_liefert_nur_finale_fassungen(self) -> None:
        """Entwürfe und archivierte Fassungen sind nicht einbindbar."""
        Vignette.objects.create(historie=Vignettenhistorie.objects.create())
        finale = Vignette.objects.create(
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

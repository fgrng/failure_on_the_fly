"""Tests für die Einrichtung einer Workshop-Instanz."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from konten.models import Konto
from konten.navigation import AUTORIN_GRUPPE
from simulation.models import ModellKonfiguration, Simulationskern

from ..management.commands.workshopdaten_anlegen import SIMULATIONSMODELL


def _einrichten(**optionen: object) -> dict[str, str]:
    """Führt das Command aus und liest die ausgegebenen Anmeldedaten zurück."""

    ausgabe: StringIO = StringIO()
    call_command("workshopdaten_anlegen", stdout=ausgabe, **optionen)
    zugangsdaten: dict[str, str] = {}
    for zeile in ausgabe.getvalue().splitlines():
        felder: list[str] = zeile.split()
        if len(felder) == 2 and felder[0].startswith("workshop"):
            zugangsdaten[felder[0]] = felder[1]
    return zugangsdaten


class WorkshopdatenTests(TestCase):
    """Das Command richtet Konten, Kern und Modell-Konfiguration ein."""

    def test_legt_zehn_reine_autorenkonten_mit_nutzbarem_passwort_an(self) -> None:
        """Die Teilnehmer:innen können sich mit den ausgegebenen Daten anmelden."""

        zugangsdaten: dict[str, str] = _einrichten()

        self.assertEqual(len(zugangsdaten), 10)
        for anmeldename, passwort in zugangsdaten.items():
            with self.subTest(anmeldename):
                konto: Konto = get_user_model().objects.get(username=anmeldename)
                self.assertEqual(
                    list(konto.groups.values_list("name", flat=True)),
                    [AUTORIN_GRUPPE],
                )
                self.assertFalse(konto.is_staff)
                self.assertFalse(konto.is_superuser)
                self.assertTrue(
                    Client().login(username=anmeldename, password=passwort)
                )

    def test_stellt_kern_und_aktive_modell_konfiguration_bereit(self) -> None:
        """Ohne beides käme kein Probelauf zustande."""

        _einrichten()

        self.assertTrue(
            Simulationskern.objects.filter(
                zustand=Simulationskern.Zustand.FINAL
            ).exists()
        )
        aktive: ModellKonfiguration = ModellKonfiguration.objects.aktive()
        self.assertEqual(aktive.sprachmodell, SIMULATIONSMODELL)
        self.assertEqual(aktive.parameter, {})

    def test_zweiter_lauf_legt_nichts_doppelt_an_und_laesst_passwoerter_stehen(
        self,
    ) -> None:
        """Ein erneuter Lauf während des Workshops sperrt niemanden aus."""

        zugangsdaten: dict[str, str] = _einrichten()

        _einrichten()

        self.assertEqual(get_user_model().objects.count(), 10)
        self.assertEqual(Simulationskern.objects.count(), 1)
        self.assertEqual(ModellKonfiguration.objects.count(), 1)
        anmeldename, passwort = next(iter(zugangsdaten.items()))
        self.assertTrue(Client().login(username=anmeldename, password=passwort))

    def test_passwoerter_neu_setzt_die_zugaenge_zurueck(self) -> None:
        """Verlorene Zettel lassen sich ersetzen."""

        alte: dict[str, str] = _einrichten()

        neue: dict[str, str] = _einrichten(passwoerter_neu=True)

        self.assertEqual(set(alte), set(neue))
        anmeldename, altes_passwort = next(iter(alte.items()))
        self.assertFalse(Client().login(username=anmeldename, password=altes_passwort))
        self.assertTrue(
            Client().login(username=anmeldename, password=neue[anmeldename])
        )

    def test_gemeinsames_passwort_gilt_fuer_alle_konten(self) -> None:
        """Für einen kurzen Workshop reicht ein einziger Zettel."""

        zugangsdaten: dict[str, str] = _einrichten(passwort="probelauf-workshop")

        self.assertEqual(set(zugangsdaten.values()), {"probelauf-workshop"})


class WorkshopkontoRechteTests(TestCase):
    """Ein Workshop-Konto erreicht die Autorenbereiche und sonst nichts."""

    def setUp(self) -> None:
        """Richtet die Instanz ein und meldet ein Konto an."""

        self.zugangsdaten: dict[str, str] = _einrichten(passwort="geheim")
        self.client.login(username="workshop01", password="geheim")

    def test_autorenbereiche_sind_erreichbar(self) -> None:
        """Anlegen, Ansehen, Bearbeiten und Probelauf sind die Workshop-Funktionen."""

        for name in (
            "vignetten:liste",
            "vignetten:anlegen",
            "sitzungen:probelauf_auswahl",
            "simulation:kern",
        ):
            with self.subTest(name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_fremde_bereiche_bleiben_verschlossen(self) -> None:
        """Forschung, Ausbildung und der Administrations-Probelauf sind gesperrt."""

        for name in (
            "erhebungen:liste",
            "training:liste",
            "fragebogen_items:liste",
            "sitzungen:administratorin_probelauf_auswahl",
        ):
            with self.subTest(name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_dasselbe_konto_ist_mehrfach_gleichzeitig_angemeldet(self) -> None:
        """Zwei Browser desselben Kontos halten getrennte Sitzungen."""

        eins: Client = Client()
        zwei: Client = Client()
        self.assertTrue(eins.login(username="workshop01", password="geheim"))
        self.assertTrue(zwei.login(username="workshop01", password="geheim"))

        self.assertNotEqual(eins.session.session_key, zwei.session.session_key)
        self.assertEqual(eins.get(reverse("vignetten:liste")).status_code, 200)
        self.assertEqual(zwei.get(reverse("vignetten:liste")).status_code, 200)

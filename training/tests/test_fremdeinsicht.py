"""HTTP-Tests der Fremdeinsicht im Training (ADR-0049)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from konten.navigation import AUTORIN_GRUPPE, AUSBILDERIN_GRUPPE
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.models import Diagnose, Gespraechsschritt, Sitzung
from training.models import Training
from vignetten.models import Vignette


def _konto(username: str, gruppe: str | None = None, **felder: object) -> Konto:
    konto: Konto = get_user_model().objects.create_user(username=username, **felder)
    if gruppe is not None:
        konto.groups.add(Group.objects.get_or_create(name=gruppe)[0])
    return konto


def _finale_vignette(autorin: Konto, name: str) -> Vignette:
    # Legt eine finale Fassung im Bestand der Autorin an.
    if not Simulationskern.objects.filter(
        zustand=Simulationskern.Zustand.FINAL
    ).exists():
        Simulationskern.objects.anlegen().finalisieren()
    vignette: Vignette = Vignette.objects.anlegen(autorin)
    vignette.historie.name = name
    vignette.historie.save(update_fields=["name"])
    vignette.fehlermuster_beschreibung = "Zähler und Nenner addieren"
    vignette.arbeitsheft_bildbeschreibung = "Falsche Bruchrechnung"
    vignette.lernauftrag_text = "Addiere die Brüche."
    vignette.arbeitsheft_text = "1/2 + 1/3 = 2/5"
    vignette.schuelerin_name = "Lea"
    vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.lehrperson_name = "Weber"
    vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.fach = "Mathematik"
    vignette.thema = "Brüche"
    vignette.klassenstufe = "6"
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 3
    vignette.save()
    vignette.finalisieren()
    return vignette


def _gespielte_sitzung(
    training: Training,
    konto: Konto,
    vignette: Vignette,
    status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN,
    aeusserung: str = "Ich habe oben und unten zusammengezählt.",
) -> Sitzung:
    # Legt eine gespielte Sitzung unter der Trainingsbindung des Kontos an.
    sitzung: Sitzung = Sitzung.objects.create(
        teilnahme=training.bindung_fuer(konto).teilnahme,
        vignette=vignette,
        simulationskern=Simulationskern.objects.get(
            zustand=Simulationskern.Zustand.FINAL
        ),
        modell_konfiguration=ModellKonfiguration.objects.belegte(Verwendung.SCHUELERIN),
        status=status,
    )
    Gespraechsschritt.objects.create(
        sitzung=sitzung,
        eingabe="Wie hast du gerechnet?",
        denkspur="Geheime Denkspur der Schülerin.",
        aeusserung=aeusserung,
        reihenfolge=1,
    )
    Diagnose.objects.create(sitzung=sitzung, text="Zähler und Nenner addiert.")
    return sitzung


def _ansehen_url(sitzung: Sitzung) -> str:
    return reverse("training:sitzung_ansehen", args=[sitzung.pk])


class FremdeinsichtTestCase(TestCase):
    """Ein veröffentlichtes Training mit Kreis, Vignette und einer Teilnehmerin."""

    def setUp(self) -> None:
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(bezeichnung="Test", sprachmodell="fake"),
            Verwendung.SCHUELERIN,
        )
        self.ausbilderin: Konto = _konto("ada", AUSBILDERIN_GRUPPE)
        self.autorin: Konto = _konto("barbara", AUTORIN_GRUPPE)
        self.teilnehmerin: Konto = _konto(
            "grace", first_name="Grace", last_name="Hopper"
        )
        self.vignette: Vignette = _finale_vignette(self.autorin, "Brüche addieren")
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.vignetten.add(self.vignette)
        self.training.veroeffentlichen()
        self.training.beitreten(self.teilnehmerin)


class SitzungAnsehenTests(FremdeinsichtTestCase):
    """Wer eine fremde Trainingssitzung lesend öffnen darf."""

    def _status_fuer(
        self, konto: Konto, status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN
    ) -> int:
        # Öffnet eine Sitzung der Teilnehmerin aus Sicht des Kontos.
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette, status
        )
        self.client.force_login(konto)
        return self.client.get(_ansehen_url(sitzung)).status_code

    def test_kreismitglied_liest_eine_abgeschlossene_sitzung(self) -> None:
        """Die Eigentümerin sieht Transkript und Diagnose ihrer Gruppe."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(_ansehen_url(sitzung))

        self.assertContains(response, "Ich habe oben und unten zusammengezählt.")

    def test_ko_eigentuemerin_liest_eine_abgeschlossene_sitzung(self) -> None:
        """Eigentümerschaft ist gleichrangig, auch für die Einsicht."""
        ko_eigentuemerin: Konto = _konto("hedy", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(ko_eigentuemerin)

        self.assertEqual(self._status_fuer(ko_eigentuemerin), 200)

    def test_neues_kreismitglied_liest_auch_aeltere_sitzungen(self) -> None:
        """Einsicht folgt der aktuellen Mitgliedschaft, auch rückwirkend."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        neues_mitglied: Konto = _konto("hedy", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(neues_mitglied)
        self.client.force_login(neues_mitglied)

        response: HttpResponse = self.client.get(_ansehen_url(sitzung))

        self.assertEqual(response.status_code, 200)

    def test_ausgetretenes_kreismitglied_bekommt_404(self) -> None:
        """Wer den Kreis verlässt, sieht sofort nichts mehr."""
        nachfolgerin: Konto = _konto("hedy", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(nachfolgerin)
        self.training.austreten(self.ausbilderin.pk)

        self.assertEqual(self._status_fuer(self.ausbilderin), 404)

    def test_administration_liest_eine_abgeschlossene_sitzung(self) -> None:
        """Die Administration folgt allein aus der Sichtbarkeitsregel."""
        administratorin: Konto = _konto("root", is_superuser=True)

        self.assertEqual(self._status_fuer(administratorin), 200)

    def test_fremdes_konto_bekommt_404(self) -> None:
        """Eine Ausbilder:in außerhalb des Kreises sieht die Sitzung nicht."""
        fremde: Konto = _konto("margaret", AUSBILDERIN_GRUPPE)

        self.assertEqual(self._status_fuer(fremde), 404)

    def test_autorin_der_vignette_bekommt_404(self) -> None:
        """Autorschaft der Vignette begründet keine Einsicht."""
        self.assertEqual(self._status_fuer(self.autorin), 404)

    def test_nicht_abgeschlossene_sitzungen_bleiben_dem_kreis_verborgen(
        self,
    ) -> None:
        """Laufende, abgebrochene und gescheiterte Sitzungen liefern 404."""
        for status in (
            Sitzung.Status.LAUFEND,
            Sitzung.Status.ABGEBROCHEN,
            Sitzung.Status.GESCHEITERT,
        ):
            with self.subTest(status=status):
                self.assertEqual(self._status_fuer(self.ausbilderin, status), 404)

    def test_fremdeinsicht_verschweigt_die_denkspur(self) -> None:
        """Der Kreis sieht, was die Teilnehmerin sieht, also keine Denkspur."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(_ansehen_url(sitzung))

        self.assertNotContains(response, "Geheime Denkspur der Schülerin.")

    def test_sitzung_in_einem_fremden_training_bleibt_verborgen(self) -> None:
        """Dieselbe Person mit derselben Vignette anderswo gehört nicht dazu."""
        fremder_kreis: Konto = _konto("hedy", AUSBILDERIN_GRUPPE)
        fremdes_training: Training = Training.objects.anlegen(
            fremder_kreis, name="Anderes Seminar"
        )
        fremdes_training.vignetten.add(self.vignette)
        fremdes_training.veroeffentlichen()
        fremdes_training.beitreten(self.teilnehmerin)
        sitzung: Sitzung = _gespielte_sitzung(
            fremdes_training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(_ansehen_url(sitzung))

        self.assertEqual(response.status_code, 404)


class SelbsteinsichtTests(FremdeinsichtTestCase):
    """Die eigene Sitzung bleibt in jedem Status lesbar."""

    def test_eigene_sitzung_ist_in_jedem_status_lesbar(self) -> None:
        """Auch laufende, abgebrochene und gescheiterte eigene Sitzungen."""
        self.client.force_login(self.teilnehmerin)
        for status in Sitzung.Status:
            with self.subTest(status=status):
                sitzung: Sitzung = _gespielte_sitzung(
                    self.training, self.teilnehmerin, self.vignette, status
                )

                response: HttpResponse = self.client.get(_ansehen_url(sitzung))

                self.assertEqual(response.status_code, 200)

    def test_selbsteinsicht_verschweigt_die_denkspur(self) -> None:
        """Auch die eigene Sitzung zeigt keine Denkspur."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.teilnehmerin)

        response: HttpResponse = self.client.get(_ansehen_url(sitzung))

        self.assertNotContains(response, "Geheime Denkspur der Schülerin.")


class FremdeinsichtTabelleTests(FremdeinsichtTestCase):
    """Die Tabelle der Fremdeinsicht auf der Kuratierseite."""

    def _kuratierseite(self) -> str:
        # Liest die Kuratierseite aus Sicht der Eigentümerin.
        self.client.force_login(self.ausbilderin)
        return self.client.get(
            reverse("training:kuratieren", args=[self.training.pk])
        ).content.decode()

    def test_beigetretene_ohne_sitzung_erscheinen_als_zeile(self) -> None:
        """Wer nichts bearbeitet hat, steht trotzdem namentlich in der Tabelle."""
        self.assertIn("Grace Hopper", self._kuratierseite())

    def test_vignetten_des_trainings_sind_die_spalten(self) -> None:
        """Jede Vignette des Trainings hat ihren Spaltenkopf."""
        self.assertIn('title="Brüche addieren"', self._kuratierseite())

    def test_abgeschlossene_sitzung_ist_verlinkt(self) -> None:
        """Eine abgeschlossene Sitzung öffnet die lesende Sitzungsansicht."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )

        self.assertIn(_ansehen_url(sitzung), self._kuratierseite())

    def test_nicht_abgeschlossene_sitzung_ist_nicht_verlinkt(self) -> None:
        """Laufende Sitzungen gehören nicht zur Fremdeinsicht."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training,
            self.teilnehmerin,
            self.vignette,
            Sitzung.Status.LAUFEND,
        )

        self.assertNotIn(_ansehen_url(sitzung), self._kuratierseite())

    def test_sitzung_in_einem_fremden_training_ist_nicht_verlinkt(self) -> None:
        """Dieselbe Person mit derselben Vignette anderswo erscheint nicht."""
        fremdes_training: Training = Training.objects.anlegen(
            _konto("hedy", AUSBILDERIN_GRUPPE), name="Anderes Seminar"
        )
        fremdes_training.vignetten.add(self.vignette)
        fremdes_training.veroeffentlichen()
        fremdes_training.beitreten(self.teilnehmerin)
        sitzung: Sitzung = _gespielte_sitzung(
            fremdes_training, self.teilnehmerin, self.vignette
        )

        self.assertNotIn(_ansehen_url(sitzung), self._kuratierseite())

    def test_sitzungen_sind_je_vignette_nummeriert_und_datiert(self) -> None:
        """Mehrere Durchläufe stehen einzeln, mit Nummer und Datum."""
        erste: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        datum: str = timezone.localtime(erste.erstellt_am).strftime("%d.%m.%Y")

        seite: str = self._kuratierseite()

        self.assertIn(f'aria-label="Sitzung vom {datum}">2</a>', seite)

    def test_zeilen_sind_nach_namen_sortiert(self) -> None:
        """Die Gruppe steht alphabetisch, nicht in Beitrittsreihenfolge."""
        self.training.beitreten(_konto("ada2", first_name="Anna", last_name="Zeller"))

        seite: str = self._kuratierseite()

        self.assertLess(seite.index("Anna Zeller"), seite.index("Grace Hopper"))

    def test_leeres_training_zeigt_einen_hinweis_statt_der_tabelle(self) -> None:
        """Ohne Vignetten gibt es nichts zu tabellieren."""
        self.training.vignetten.clear()

        self.assertIn("Dieses Training enthält keine Vignetten.", self._kuratierseite())

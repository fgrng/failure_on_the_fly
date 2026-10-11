"""HTTP-Tests für Austritt und Entfernen aus dem Training (ADR-0049)."""

from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE, AUTORIN_GRUPPE
from simulation.models import Verwendung
from sitzungen.models import Sitzung
from sitzungen.tests.aufnahme import audioaufnahme
from training.models import Training
from training.tests.aufbau import (
    FremdeinsichtTestCase,
    ansehen_url,
    gespielte_sitzung,
)
from training.tests.seite import kuratierseite, tabellenzeilen
from vignetten.models import Vignette

HINWEIS_AUSGETRETEN: str = "Sie sind nicht mehr Teilnehmer:in dieses Trainings"


class AustrittTests(TestCase):
    """Eine Trainingsteilnehmerin tritt aus und behält ihre Selbsteinsicht."""

    def setUp(self) -> None:
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        self.ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.teilnehmerin: Konto = konto_mit_rollen("grace")
        self.vignette: Vignette = finale_vignette(
            konto_mit_rollen("barbara", AUTORIN_GRUPPE), name="Brüche vergleichen"
        )
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.vignetten.add(self.vignette)
        self.training.veroeffentlichen()
        self.client.force_login(self.teilnehmerin)
        self.client.get(
            reverse("training:beitreten", args=[self.training.trainings_link])
        )

    def _detail(self) -> HttpResponse:
        # Ruft die Trainingsseite aus Sicht des angemeldeten Kontos auf.
        return self.client.get(reverse("training:detail", args=[self.training.pk]))

    def _austreten(self) -> HttpResponse:
        # Tritt aus dem Training aus und folgt der Weiterleitung.
        return self.client.post(
            reverse("training:austreten", args=[self.training.pk]), follow=True
        )

    def _historie(self) -> list[dict[str, object]]:
        # Liest die Zeilen von „Meine Trainings“ des angemeldeten Kontos.
        return tabellenzeilen(self.client.get(reverse("training:historie")))

    def test_trainingsseite_bietet_den_austritt_mit_erklaerung_an(self) -> None:
        """Vor dem Austritt erklärt die Seite seine Folgen."""
        detail: HttpResponse = self._detail()

        self.assertContains(detail, "Aus dem Training austreten")
        self.assertContains(
            detail, reverse("training:austreten", args=[self.training.pk])
        )
        for folge in (
            "sieht der Kreis dieses Trainings Ihre Sitzungen nicht mehr",
            "für dieses Training ruhen",
            "Nichts wird gelöscht",
            "können Sie wieder beitreten",
        ):
            self.assertContains(detail, folge)

    def test_austritt_leitet_mit_meldung_auf_die_trainingsseite(self) -> None:
        """Nach dem Austritt zeigt die Trainingsseite den neuen Stand."""
        antwort: HttpResponse = self._austreten()

        self.assertRedirects(
            antwort, reverse("training:detail", args=[self.training.pk])
        )
        self.assertContains(antwort, "Sie sind aus dem Training")
        self.assertContains(antwort, HINWEIS_AUSGETRETEN)

    def test_austritt_nur_per_post(self) -> None:
        """Ein aufgerufener Link lässt niemanden austreten."""
        antwort: HttpResponse = self.client.get(
            reverse("training:austreten", args=[self.training.pk])
        )

        self.assertEqual(antwort.status_code, 405)
        self.assertNotContains(self._detail(), HINWEIS_AUSGETRETEN)

    def test_zweiter_austritt_aendert_nichts_und_scheitert_nicht(self) -> None:
        """Ein doppeltes Absenden bleibt harmlos."""
        self._austreten()

        antwort: HttpResponse = self._austreten()

        self.assertRedirects(
            antwort, reverse("training:detail", args=[self.training.pk])
        )
        self.assertContains(antwort, HINWEIS_AUSGETRETEN)

    def test_austritt_ohne_bindung_ist_unbekannt(self) -> None:
        """Wer dem Training nie beigetreten ist, erfährt nichts über es."""
        self.client.force_login(konto_mit_rollen("linus"))

        antwort: HttpResponse = self.client.post(
            reverse("training:austreten", args=[self.training.pk])
        )

        self.assertEqual(antwort.status_code, 404)

    def test_katalog_zeigt_das_training_nicht_mehr(self) -> None:
        """Der Katalog zeigt nur, woran die Person teilnimmt."""
        self._austreten()

        katalog: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertEqual(tabellenzeilen(katalog), [])

    def test_historie_kennzeichnet_das_training_als_ausgetreten(self) -> None:
        """Frühere Sitzungen bleiben über die Historie auffindbar."""
        self._austreten()

        historie: HttpResponse = self.client.get(reverse("training:historie"))

        self.assertEqual(
            [
                (zeile["name"], zeile["ausgetreten"])
                for zeile in tabellenzeilen(historie)
            ],
            [("Bruchrechnung", True)],
        )

    def test_historie_kennzeichnet_aktive_trainings_nicht(self) -> None:
        """Ohne Austritt steht kein Kennzeichen."""
        historie: HttpResponse = self.client.get(reverse("training:historie"))

        self.assertEqual(
            [zeile["ausgetreten"] for zeile in tabellenzeilen(historie)], [False]
        )

    def test_trainingsseite_zeigt_eigene_sitzungen_in_jedem_status(self) -> None:
        """Die Ausgetretene liest ihre Arbeit weiter."""
        sitzungen: list[Sitzung] = [
            gespielte_sitzung(self.training, self.teilnehmerin, self.vignette, status)
            for status in Sitzung.Status
        ]
        self._austreten()

        detail: HttpResponse = self._detail()

        for sitzung in sitzungen:
            with self.subTest(status=sitzung.status):
                self.assertContains(detail, ansehen_url(sitzung))

    def test_trainingsseite_bietet_weder_wahl_noch_start_noch_austritt(self) -> None:
        """Die Seite ist für die Ausgetretene nur lesend."""
        self._austreten()

        detail: HttpResponse = self._detail()

        self.assertContains(detail, HINWEIS_AUSGETRETEN)
        self.assertNotContains(
            detail, reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )
        self.assertNotContains(detail, "Neu starten")
        self.assertNotContains(detail, "Aus dem Training austreten")

    def test_wahl_einwilligung_und_start_werden_abgewiesen(self) -> None:
        """Nach dem Austritt entsteht keine Sitzung, und die Bindung bleibt ruhend."""
        self._austreten()
        wahl_url: str = reverse(
            "training:wahl", args=[self.training.pk, self.vignette.pk]
        )

        antworten: list[HttpResponse] = [
            self.client.get(wahl_url),
            self.client.post(wahl_url),
            self.client.post(
                reverse(
                    "training:einwilligung", args=[self.training.pk, self.vignette.pk]
                ),
                {"audioverarbeitung_eingewilligt": "ja"},
            ),
        ]

        self.assertEqual([a.status_code for a in antworten], [404, 404, 404])
        self.assertEqual(
            [
                (zeile["ausgetreten"], zeile["sitzungen_nach_status"])
                for zeile in self._historie()
            ],
            [
                (
                    True,
                    {
                        "laufend": 0,
                        "abgeschlossen": 0,
                        "abgebrochen": 0,
                        "gescheitert": 0,
                    },
                )
            ],
        )

    def test_eigene_sitzung_bleibt_lesbar_ohne_denkspur(self) -> None:
        """Auch eine laufende Sitzung öffnet sich lesend, ohne Denkspur."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette, Sitzung.Status.LAUFEND
        )
        self._austreten()

        antwort: HttpResponse = self.client.get(ansehen_url(sitzung))

        self.assertContains(antwort, "Ich habe oben und unten zusammengezählt.")
        self.assertNotContains(antwort, "Geheime Denkspur der Schülerin.")

    def test_kreis_und_administration_erreichen_das_training_unveraendert(
        self,
    ) -> None:
        """Ein Austritt von Teilnehmenden ändert nichts am Zugang des Kreises."""
        self._austreten()
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)

        for konto in (self.ausbilderin, administratorin):
            with self.subTest(konto=konto.username):
                self.client.force_login(konto)
                detail: HttpResponse = self._detail()
                self.assertContains(detail, "Neu starten")
                self.assertNotContains(detail, HINWEIS_AUSGETRETEN)
                self.assertEqual(
                    self.client.get(
                        reverse("training:kuratieren", args=[self.training.pk])
                    ).status_code,
                    200,
                )

    def test_ausgetretene_eigentuemerin_startet_keine_sitzung(self) -> None:
        """Der Kreiszugang führt nicht an einer ausgetretenen Bindung vorbei."""
        gespielte_sitzung(self.training, self.ausbilderin, self.vignette)
        self.client.force_login(self.ausbilderin)
        self._austreten()
        historie_vorher: list[dict[str, object]] = self._historie()

        start: HttpResponse = self.client.post(
            reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )

        self.assertEqual(start.status_code, 404)
        self.assertEqual(self._historie(), historie_vorher)

    def test_ausgetretene_eigentuemerin_sieht_keine_wahl(self) -> None:
        """Auch die Bestätigung der Wahl bleibt der ausgetretenen Eigentümerin verschlossen."""
        self.client.force_login(self.ausbilderin)
        gespielte_sitzung(self.training, self.ausbilderin, self.vignette)
        self._austreten()

        wahl: HttpResponse = self.client.get(
            reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )

        self.assertEqual(wahl.status_code, 404)


@override_settings(TRANSKRIPTION_ZERO_RETENTION=True)
class LaufendeSitzungNachAustrittTests(TestCase):
    """Eine beim Austritt laufende Sitzung bleibt liegen."""

    def setUp(self) -> None:
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        vignette: Vignette = finale_vignette(ausbilderin)
        self.training: Training = Training.objects.anlegen(
            ausbilderin, name="Bruchrechnung"
        )
        self.training.vignetten.add(vignette)
        self.training.veroeffentlichen()
        self.client.force_login(konto_mit_rollen("grace"))
        self.client.get(
            reverse("training:beitreten", args=[self.training.trainings_link])
        )
        self.client.post(reverse("training:wahl", args=[self.training.pk, vignette.pk]))
        start: HttpResponse = self.client.post(
            reverse("training:einwilligung", args=[self.training.pk, vignette.pk]),
            {"audioverarbeitung_eingewilligt": "ja"},
        )
        self.sitzung_url: str = reverse(
            "training:sitzung_ansehen", args=[start.context["sitzung_pk"]]
        )
        self.client.post(reverse("training:austreten", args=[self.training.pk]))

    def test_gespraechsablaeufe_setzen_die_sitzung_nicht_fort(self) -> None:
        """Auch ein noch offener Tab führt kein Gespräch weiter."""
        anfragen: dict[str, tuple[str, dict[str, object]]] = {
            "gespraech": ("training:gespraech", {"eingabe": "Wie rechnest du?"}),
            "beenden": ("training:gespraech_beenden", {}),
            "debrief": ("training:debrief", {"diagnose": "Zähler addiert."}),
            "abbrechen": ("training:abbrechen", {}),
            "transkription": ("training:transkription", {"audio": audioaufnahme()}),
        }

        for ablauf, (name, daten) in anfragen.items():
            with self.subTest(ablauf=ablauf):
                antwort: HttpResponse = self.client.post(reverse(name), daten)
                self.assertEqual(antwort.status_code, 404)
        self.assertEqual(
            [
                zeile["sitzungen_nach_status"]
                for zeile in tabellenzeilen(
                    self.client.get(reverse("training:historie"))
                )
            ],
            [{"laufend": 1, "abgeschlossen": 0, "abgebrochen": 0, "gescheitert": 0}],
        )
        sitzung: HttpResponse = self.client.get(self.sitzung_url)
        self.assertNotContains(sitzung, "Wie rechnest du?")
        self.assertNotContains(sitzung, "Zähler addiert.")


class FremdeinsichtNachAustrittTests(FremdeinsichtTestCase):
    """Nach dem Austritt verschwindet die Person für Kreis und Administration."""

    def _austreten(self) -> None:
        # Tritt als Teilnehmerin über die Trainingsseite aus.
        self.client.force_login(self.teilnehmerin)
        self.client.post(reverse("training:austreten", args=[self.training.pk]))

    def test_fremdeinsicht_zeigt_keine_zeile_mehr(self) -> None:
        """Die Tabelle auf der Kuratierseite nennt die Ausgetretene nicht."""
        gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        self._austreten()

        seite: str = kuratierseite(self.client, self.training, self.ausbilderin)

        self.assertNotIn("Grace Hopper", seite)
        self.assertIn("Noch niemand ist beigetreten.", seite)

    def test_beigetretenen_zahl_zaehlt_nur_aktive(self) -> None:
        """Wer ausgetreten ist, zählt nicht mehr mit."""
        self.training.beitreten(Konto.objects.create_user(username="margaret"))
        self._austreten()

        seite: str = kuratierseite(self.client, self.training, self.ausbilderin)

        self.assertIn("1 Person beigetreten", seite)

    def test_auch_aeltere_sitzungen_sind_fuer_kreis_und_administration_unbekannt(
        self,
    ) -> None:
        """Was vorher lesbar war, antwortet nach dem Austritt mit 404."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)
        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 200)
        self._austreten()

        for konto in (
            self.ausbilderin,
            konto_mit_rollen("root", is_superuser=True),
        ):
            with self.subTest(konto=konto.username):
                self.client.force_login(konto)
                self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 404)

    def test_ausgetretene_sieht_ihre_sitzung_weiter(self) -> None:
        """Die Selbsteinsicht bleibt unverändert."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self._austreten()

        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 200)

    def test_sitzungen_in_anderen_trainings_bleiben_einsehbar(self) -> None:
        """Der Austritt aus einem Training ändert nichts an einem anderen."""
        anderes: Training = Training.objects.anlegen(
            self.ausbilderin, name="Dezimalzahlen"
        )
        anderes.vignetten.add(self.vignette)
        anderes.veroeffentlichen()
        anderes.beitreten(self.teilnehmerin)
        sitzung: Sitzung = gespielte_sitzung(anderes, self.teilnehmerin, self.vignette)
        self._austreten()

        self.client.force_login(self.ausbilderin)

        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 200)
        self.assertIn(
            "Grace Hopper", kuratierseite(self.client, anderes, self.ausbilderin)
        )


class EntfernenTests(FremdeinsichtTestCase):
    """Kreis und Administration entfernen Trainingsteilnehmende (ADR-0049)."""

    def _entfernen_url(self, konto: Konto | None = None) -> str:
        # Adresse der Aktion „Entfernen“ für die Zeile des Kontos.
        return reverse(
            "training:teilnehmerin_entfernen",
            args=[self.training.pk, (konto or self.teilnehmerin).pk],
        )

    def _entfernen(self, konto: Konto) -> HttpResponse:
        # Entfernt die Teilnehmerin als angemeldetes Konto und folgt der Weiterleitung.
        self.client.force_login(konto)
        return self.client.post(self._entfernen_url(), follow=True)

    def _entfernen_bestaetigt(self, konto: Konto) -> None:
        # Das Entfernen landet auf der Kuratierseite, die Teilnehmerin fehlt dort.
        antwort: HttpResponse = self._entfernen(konto)

        self.assertRedirects(
            antwort, reverse("training:kuratieren", args=[self.training.pk])
        )
        self.assertNotIn(
            "Grace Hopper",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

    def _sicht(self, konto: Konto) -> tuple[str, list[dict[str, object]]]:
        # Trainingsseite und Historie aus Sicht des Kontos.
        self.client.force_login(konto)
        detail: str = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        ).content.decode()
        return detail, tabellenzeilen(self.client.get(reverse("training:historie")))

    def test_jede_zeile_bietet_das_entfernen_mit_erklaerung_an(self) -> None:
        """Die Bestätigung sagt, dass Entfernen kein Ausschluss ist."""
        seite: str = kuratierseite(self.client, self.training, self.ausbilderin)

        self.assertIn(self._entfernen_url(), seite)
        self.assertIn("über den offenen Trainings-Link wieder beitreten", seite)
        self.assertIn("Sperren Sie dazu den Beitritt", seite)

    def test_entfernen_leitet_mit_meldung_auf_die_kuratierseite(self) -> None:
        """Danach steht die Person nicht mehr in Fremdeinsicht und Zahl."""
        antwort: HttpResponse = self._entfernen(self.ausbilderin)

        self.assertRedirects(
            antwort, reverse("training:kuratieren", args=[self.training.pk])
        )
        self.assertContains(antwort, "Grace Hopper ist aus dem Training entfernt.")
        self.assertContains(antwort, "Noch niemand ist beigetreten.")
        self.assertContains(antwort, "0 Personen beigetreten")

    def test_entfernen_nur_per_post(self) -> None:
        """Ein aufgerufener Link entfernt niemanden."""
        self.client.force_login(self.ausbilderin)

        antwort: HttpResponse = self.client.get(self._entfernen_url())

        self.assertEqual(antwort.status_code, 405)
        self.assertIn(
            "Grace Hopper",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

    def test_sitzungen_der_entfernten_sind_fuer_den_kreis_unbekannt(self) -> None:
        """Auch eine vorher lesbare Sitzung antwortet mit 404."""
        sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        self.client.force_login(self.ausbilderin)
        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 200)

        self._entfernen(self.ausbilderin)

        self.assertEqual(self.client.get(ansehen_url(sitzung)).status_code, 404)

    def test_entfernte_sieht_dasselbe_wie_nach_eigenem_austritt(self) -> None:
        """Trainingsseite und Historie verraten nicht, wer es ausgelöst hat."""
        margaret: Konto = Konto.objects.create_user(username="margaret")
        self.training.beitreten(margaret)
        for konto in (self.teilnehmerin, margaret):
            gespielte_sitzung(self.training, konto, self.vignette)
        self._entfernen(self.ausbilderin)
        self.client.force_login(margaret)
        self.client.post(reverse("training:austreten", args=[self.training.pk]))

        detail_entfernt, historie_entfernt = self._sicht(self.teilnehmerin)
        _, historie_ausgetreten = self._sicht(margaret)

        self.assertIn(HINWEIS_AUSGETRETEN, detail_entfernt)
        self.assertNotIn("entfernt", detail_entfernt)
        self.assertEqual(historie_entfernt, historie_ausgetreten)

    def test_jede_eigentuemerin_entfernt(self) -> None:
        """Nicht nur, wer das Training angelegt hat."""
        mitglied: Konto = konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(mitglied)

        self._entfernen_bestaetigt(mitglied)

    def test_administration_entfernt_in_jedem_training(self) -> None:
        """Wie bei jeder anderen Kreisaktion."""
        self._entfernen_bestaetigt(konto_mit_rollen("root", is_superuser=True))

    def test_kreisfremde_und_teilnehmende_koennen_nicht_entfernen(self) -> None:
        """Nur der Kreis entscheidet über seine Liste."""
        margaret: Konto = Konto.objects.create_user(username="margaret")
        self.training.beitreten(margaret)

        for konto in (konto_mit_rollen("linus", AUSBILDERIN_GRUPPE), margaret):
            with self.subTest(konto=konto.username):
                self.client.force_login(konto)
                antwort: HttpResponse = self.client.post(self._entfernen_url())
                self.assertEqual(antwort.status_code, 404)
        self.assertIn(
            "Grace Hopper",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

    def test_konto_ohne_aktive_bindung_ist_unbekannt(self) -> None:
        """Weder Fremde noch schon Ausgetretene lassen sich entfernen."""
        self.client.force_login(self.teilnehmerin)
        self.client.post(reverse("training:austreten", args=[self.training.pk]))
        fremd: Konto = Konto.objects.create_user(username="linus")
        self.client.force_login(self.ausbilderin)

        for konto in (self.teilnehmerin, fremd):
            with self.subTest(konto=konto.username):
                antwort: HttpResponse = self.client.post(self._entfernen_url(konto))
                self.assertEqual(antwort.status_code, 404)
        self.assertIn(
            "0 Personen beigetreten",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

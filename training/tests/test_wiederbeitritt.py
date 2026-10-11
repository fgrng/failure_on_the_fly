"""HTTP-Tests für den Wiederbeitritt über den Trainings-Link (ADR-0049)."""

from django.http import HttpResponse
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen
from konten.models import Konto
from sitzungen.models import Sitzung
from training.tests.aufbau import (
    FremdeinsichtTestCase,
    ansehen_url,
    gespielte_sitzung,
)
from training.tests.seite import kuratierseite, tabellenzeilen

HINWEIS_AUSGETRETEN: str = "Sie sind nicht mehr Teilnehmer:in dieses Trainings"


class WiederbeitrittTests(FremdeinsichtTestCase):
    """Eine Ausgetretene tritt über den offenen Link wieder bei."""

    def setUp(self) -> None:
        super().setUp()
        self.sitzung: Sitzung = gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )

    def _austreten(self) -> None:
        # Tritt als Teilnehmerin über die Trainingsseite aus.
        self.client.force_login(self.teilnehmerin)
        self.client.post(reverse("training:austreten", args=[self.training.pk]))

    def _entfernen(self) -> None:
        # Entfernt die Teilnehmerin als Eigentümerin über die Kuratierseite.
        self.client.force_login(self.ausbilderin)
        self.client.post(
            reverse(
                "training:teilnehmerin_entfernen",
                args=[self.training.pk, self.teilnehmerin.pk],
            )
        )

    def _beitreten(self) -> HttpResponse:
        # Öffnet den Trainings-Link als Teilnehmerin.
        self.client.force_login(self.teilnehmerin)
        return self.client.get(
            reverse("training:beitreten", args=[self.training.trainings_link])
        )

    def _historie(self) -> list[tuple[object, object]]:
        # Liest Kennzeichen und Sitzungszahlen aus „Meine Trainings“.
        return [
            (zeile["ausgetreten"], zeile["sitzungen_nach_status"])
            for zeile in tabellenzeilen(self.client.get(reverse("training:historie")))
        ]

    def test_wiederbeitritt_fuehrt_ins_training_mit_wahl_und_start(self) -> None:
        """Die Trainingsseite bietet wieder Wahl und Start."""
        self._austreten()

        antwort: HttpResponse = self._beitreten()

        self.assertRedirects(
            antwort, reverse("training:detail", args=[self.training.pk])
        )
        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        )
        self.assertNotContains(detail, HINWEIS_AUSGETRETEN)
        self.assertContains(
            detail, reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )
        self.assertContains(detail, "Aus dem Training austreten")

    def test_training_steht_wieder_im_katalog(self) -> None:
        """Der Katalog zeigt das Training wieder."""
        self._austreten()
        self._beitreten()

        katalog: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertEqual(
            [zeile["name"] for zeile in tabellenzeilen(katalog)], ["Bruchrechnung"]
        )

    def test_dieselbe_bindung_lebt_mit_ihren_sitzungen_wieder_auf(self) -> None:
        """Die Historie hat eine Zeile, ohne Kennzeichen und mit der alten Sitzung."""
        self._austreten()
        self._beitreten()

        self.assertEqual(
            self._historie(),
            [
                (
                    False,
                    {
                        "laufend": 0,
                        "abgeschlossen": 1,
                        "abgebrochen": 0,
                        "gescheitert": 0,
                    },
                )
            ],
        )

    def test_kreis_sieht_die_person_und_ihre_frueheren_sitzungen_wieder(
        self,
    ) -> None:
        """Fremdeinsicht, Beigetretenen-Zahl und lesende Ansicht kommen zurück."""
        self._austreten()
        self._beitreten()

        seite: str = kuratierseite(self.client, self.training, self.ausbilderin)

        self.assertIn("Grace Hopper", seite)
        self.assertIn("1 Person beigetreten", seite)
        self.assertEqual(self.client.get(ansehen_url(self.sitzung)).status_code, 200)

    def test_entfernte_tritt_ebenso_wieder_bei(self) -> None:
        """Entfernen ist kein Ausschluss."""
        self._entfernen()

        self._beitreten()

        self.assertEqual([ausgetreten for ausgetreten, _ in self._historie()], [False])
        self.assertIn(
            "Grace Hopper",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

    def test_gesperrter_beitritt_haelt_ausgetretene_fern(self) -> None:
        """Die Sperrseite erscheint, und die Bindung bleibt ausgetreten."""
        self._austreten()
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])

        antwort: HttpResponse = self._beitreten()

        self.assertEqual(antwort.status_code, 403)
        self.assertTemplateUsed(antwort, "training/beitritt_gesperrt.html")
        self.assertEqual([ausgetreten for ausgetreten, _ in self._historie()], [True])
        self.assertNotIn(
            "Grace Hopper",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

    def test_gesperrter_beitritt_laesst_aktive_weiter_ins_training(self) -> None:
        """Wer nicht ausgetreten ist, kommt auch bei Sperre durch."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])

        antwort: HttpResponse = self._beitreten()

        self.assertRedirects(
            antwort, reverse("training:detail", args=[self.training.pk])
        )

    def test_sitzungsstart_reaktiviert_nicht(self) -> None:
        """Nur der Beitritt weckt die Bindung, ein Startversuch nicht."""
        self._austreten()

        self.client.post(
            reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )

        self.assertEqual([ausgetreten for ausgetreten, _ in self._historie()], [True])
        self.client.force_login(self.ausbilderin)
        self.assertEqual(self.client.get(ansehen_url(self.sitzung)).status_code, 404)

    def test_wiederbeitritt_legt_fuer_andere_keine_bindung_an(self) -> None:
        """Ein Konto ohne Bindung tritt beim offenen Link wie bisher neu bei."""
        neue: Konto = konto_mit_rollen("margaret")
        self.client.force_login(neue)

        self.client.get(
            reverse("training:beitreten", args=[self.training.trainings_link])
        )

        self.assertIn(
            "2 Personen beigetreten",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

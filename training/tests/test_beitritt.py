"""HTTP-Tests für das geschlossene Training und den Beitritt über den Trainings-Link."""

from typing import cast

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    konto_mit_rollen,
)
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE, AUTORIN_GRUPPE
from simulation.models import Verwendung
from sitzungen.models import Sitzung, Teilnahme
from training.models import Training, Trainingsbindung
from training.tests.seite import kuratierseite
from vignetten.models import Vignette


def _beitritt_url(training: Training) -> str:
    return reverse("training:beitreten", args=[training.trainings_link])


class BeitrittTests(TestCase):
    """Wer den Trainings-Link eingeloggt öffnet, tritt dem Training bei."""

    def setUp(self) -> None:
        self.ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.studierende: Konto = konto_mit_rollen("grace")
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.veroeffentlichen()

    def test_kreis_und_administration_oeffnen_den_link_ohne_beitritt(self) -> None:
        """Offene und gesperrte Links zählen auch wiederholt keinen Kreiszugang."""
        ko_eigentuemerin: Konto = konto_mit_rollen("lin", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(ko_eigentuemerin)
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)

        for gesperrt in (False, True):
            self.training.beitritt_gesperrt = gesperrt
            self.training.save(update_fields=["beitritt_gesperrt"])
            for konto in (self.ausbilderin, ko_eigentuemerin, administratorin):
                with self.subTest(gesperrt=gesperrt, konto=konto.username):
                    self.client.force_login(konto)
                    for _ in range(2):
                        response = self.client.get(_beitritt_url(self.training))
                        self.assertRedirects(
                            response,
                            reverse("training:detail", args=[self.training.pk]),
                        )
                    self.assertEqual(Trainingsbindung.objects.count(), 0)
                    self.assertEqual(Teilnahme.objects.count(), 0)
                    kuratierseite = self.client.get(
                        reverse("training:kuratieren", args=[self.training.pk])
                    )
                    self.assertContains(
                        kuratierseite,
                        "0 Personen sind bereits dabei"
                        if gesperrt
                        else "0 Personen beigetreten",
                    )

    def test_beitritt_legt_die_bindung_an_und_fuehrt_ins_training(self) -> None:
        """Der eingeloggte Aufruf bindet das Konto und leitet zur Trainingsseite."""
        self.client.force_login(self.studierende)

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )

    def test_erneutes_oeffnen_fuehrt_ohne_fehler_ins_training(self) -> None:
        """Wer schon beigetreten ist, landet ohne Fehler direkt im Training."""
        self.client.force_login(self.studierende)
        self.client.get(_beitritt_url(self.training))

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )

    def test_erneutes_oeffnen_zaehlt_nicht_doppelt(self) -> None:
        """Der Kreis zählt eine Person auch nach zwei Aufrufen nur einmal."""
        self.client.force_login(self.studierende)
        self.client.get(_beitritt_url(self.training))
        self.client.get(_beitritt_url(self.training))
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[self.training.pk])
        )

        self.assertContains(response, "1 Person beigetreten")

    def test_ohne_login_fuehrt_der_link_ueber_den_login_zurueck(self) -> None:
        """Der Login kennt den Beitritt als Ziel und kehrt dorthin zurück."""
        url: str = _beitritt_url(self.training)

        response: HttpResponse = self.client.get(url)

        self.assertRedirects(
            response, f"{reverse('login')}?next={url}", fetch_redirect_response=False
        )

    def test_login_kehrt_zum_beitritt_zurueck_und_fuehrt_ins_training(self) -> None:
        """Nach dem Login landet die Person beigetreten auf der Trainingsseite."""
        self.studierende.set_password("geheim-im-test")
        self.studierende.save()
        url: str = _beitritt_url(self.training)
        login_url: str = f"{reverse('login')}?next={url}"

        response: HttpResponse = self.client.post(
            login_url,
            {"username": "grace", "password": "geheim-im-test", "next": url},
            follow=True,
        )

        self.assertEqual(
            response.redirect_chain,
            [(url, 302), (reverse("training:detail", args=[self.training.pk]), 302)],
        )

    def test_gesperrter_link_meldet_die_sperre(self) -> None:
        """Bei gesperrtem Beitritt erscheint eine verständliche Meldung."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        self.client.force_login(self.studierende)

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertContains(
            response,
            "Bitte wenden Sie sich an Ihre Ausbilder:in.",
            status_code=403,
        )

    def test_gesperrter_link_laesst_niemanden_beitreten(self) -> None:
        """Nach dem gesperrten Aufruf bleibt das Training verschlossen."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        self.client.force_login(self.studierende)
        self.client.get(_beitritt_url(self.training))

        response: HttpResponse = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_gesperrter_link_fuehrt_beigetretene_weiter_ins_training(self) -> None:
        """Die Sperre hält nur Neue fern; die Gruppe bleibt dabei."""
        self.client.force_login(self.studierende)
        self.client.get(_beitritt_url(self.training))
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )
        self.assertEqual(Trainingsbindung.objects.count(), 1)
        self.assertEqual(Teilnahme.objects.count(), 1)

    def test_fremde_ausbilderin_tritt_wie_eine_teilnehmerin_bei(self) -> None:
        """Die Ausbilderrolle allein umgeht weder Beitritt noch Sperre."""
        self.client.force_login(konto_mit_rollen("eve", AUSBILDERIN_GRUPPE))
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])

        self.assertContains(
            self.client.get(_beitritt_url(self.training)),
            "Bitte wenden Sie sich an Ihre Ausbilder:in.",
            status_code=403,
        )
        self.assertEqual(Trainingsbindung.objects.count(), 0)
        self.assertEqual(Teilnahme.objects.count(), 0)

        self.training.beitritt_gesperrt = False
        self.training.save(update_fields=["beitritt_gesperrt"])
        for _ in range(2):
            self.assertRedirects(
                self.client.get(_beitritt_url(self.training)),
                reverse("training:detail", args=[self.training.pk]),
            )
        self.assertEqual(Trainingsbindung.objects.count(), 1)
        self.assertEqual(Teilnahme.objects.count(), 1)

    def test_gesperrter_link_fuehrt_den_kreis_ins_training(self) -> None:
        """Der Kreis braucht keinen Beitritt und landet trotz Sperre im Training."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )

    def test_gesperrter_link_fuehrt_die_administration_ins_training(self) -> None:
        """Die Administration sieht jedes Training und landet trotz Sperre darin."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        self.client.force_login(konto_mit_rollen("root", is_superuser=True))

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )

    def test_gesperrter_link_bindet_den_kreis_nicht(self) -> None:
        """Wer das Training über den Kreis sieht, zählt nicht als beigetreten."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        self.client.force_login(self.ausbilderin)
        self.client.get(_beitritt_url(self.training))

        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[self.training.pk])
        )

        self.assertContains(response, "0 Personen sind bereits dabei")

    def test_link_eines_entwurfs_ist_unbekannt(self) -> None:
        """Ein Entwurfs-Link bleibt auch für Kreis und Administration unbekannt."""
        entwurf: Training = Training.objects.anlegen(self.ausbilderin, name="Entwurf")
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)
        fremde_ausbilderin: Konto = konto_mit_rollen("eve", AUSBILDERIN_GRUPPE)
        for konto in (
            self.studierende,
            self.ausbilderin,
            administratorin,
            fremde_ausbilderin,
        ):
            with self.subTest(konto=konto.username):
                self.client.force_login(konto)
                response = self.client.get(_beitritt_url(entwurf))
                self.assertEqual(response.status_code, 404)
        self.assertEqual(Trainingsbindung.objects.count(), 0)
        self.assertEqual(Teilnahme.objects.count(), 0)

    def test_leeres_training_laesst_sich_veroeffentlichen_und_beitreten(
        self,
    ) -> None:
        """Ein Training ohne Vignetten ist ein gültiger Anlass."""
        leer: Training = Training.objects.anlegen(self.ausbilderin, name="Sammelanlass")
        self.client.force_login(self.ausbilderin)
        self.client.post(reverse("training:veroeffentlichen", args=[leer.pk]))
        self.client.force_login(self.studierende)

        beitritt: HttpResponse = self.client.get(_beitritt_url(leer))
        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[leer.pk])
        )

        self.assertRedirects(beitritt, reverse("training:detail", args=[leer.pk]))
        self.assertContains(detail, "Dieses Training enthält keine Vignetten.")


class GeschlossenesTrainingTests(TestCase):
    """Teilnehmende erreichen nur Trainings, denen sie beigetreten sind."""

    def setUp(self) -> None:
        self.ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.studierende: Konto = konto_mit_rollen("grace")
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.vignette: Vignette = finale_vignette(
            konto_mit_rollen("barbara", AUTORIN_GRUPPE), name="Brüche vergleichen"
        )
        self.training.vignetten.add(self.vignette)
        self.training.veroeffentlichen()

    def _beitreten(self, konto: Konto) -> None:
        self.client.force_login(konto)
        self.client.get(_beitritt_url(self.training))

    def test_kreis_und_administration_starten_sitzungen_und_behalten_sie(self) -> None:
        """Erst der Start bindet das Konto; spätere Linkaufrufe erhalten die Sitzung."""
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)
        for konto in (self.ausbilderin, administratorin):
            with self.subTest(konto=konto.username):
                self.client.force_login(konto)
                self.client.get(_beitritt_url(self.training))
                self.assertFalse(Trainingsbindung.objects.filter(konto=konto).exists())
                einwilligung = self.client.post(
                    reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
                )
                self.assertContains(einwilligung, "Einwilligung")
                start = self.client.post(
                    reverse(
                        "training:einwilligung",
                        args=[self.training.pk, self.vignette.pk],
                    ),
                    {"audioverarbeitung_eingewilligt": "nein"},
                )
                self.assertContains(start, "Ihre nächste Frage")
                bindung = cast(
                    Trainingsbindung, Trainingsbindung.objects.get(konto=konto)
                )
                sitzung = Sitzung.objects.get(teilnahme=bindung.teilnahme)
                self.client.post(reverse("training:abbrechen"))

                for gesperrt in (False, True):
                    self.training.beitritt_gesperrt = gesperrt
                    self.training.save(update_fields=["beitritt_gesperrt"])
                    for _ in range(2):
                        self.assertRedirects(
                            self.client.get(_beitritt_url(self.training)),
                            reverse("training:detail", args=[self.training.pk]),
                        )
                    self.assertEqual(
                        Trainingsbindung.objects.get(konto=konto).pk, bindung.pk
                    )
                    self.assertEqual(
                        Sitzung.objects.get(teilnahme=bindung.teilnahme).pk,
                        sitzung.pk,
                    )
                    self.assertContains(
                        self.client.get(
                            reverse("training:sitzung_ansehen", args=[sitzung.pk])
                        ),
                        "Arbeitsheft von Lea",
                    )
                self.training.beitritt_gesperrt = False
                self.training.save(update_fields=["beitritt_gesperrt"])
        self.assertEqual(Trainingsbindung.objects.count(), 2)
        self.assertEqual(Teilnahme.objects.count(), 2)

    def test_katalog_zeigt_teilnehmenden_nur_beigetretene_trainings(self) -> None:
        """Ein veröffentlichtes Training ist nicht mehr für alle sichtbar."""
        Training.objects.anlegen(
            self.ausbilderin, name="Fremdes Seminar"
        ).veroeffentlichen()
        self._beitreten(self.studierende)

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertContains(response, "Bruchrechnung")
        self.assertNotContains(response, "Fremdes Seminar")

    def test_detail_wahl_und_start_ohne_bindung_liefern_404(self) -> None:
        """Auch die direkte Adresse öffnet ein fremdes Training nicht."""
        self.client.force_login(self.studierende)
        wahl_url: str = reverse(
            "training:wahl", args=[self.training.pk, self.vignette.pk]
        )

        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        )
        wahl: HttpResponse = self.client.get(wahl_url)
        start: HttpResponse = self.client.post(wahl_url)
        einwilligung: HttpResponse = self.client.post(
            reverse("training:einwilligung", args=[self.training.pk, self.vignette.pk]),
            {"audioverarbeitung_eingewilligt": "nein"},
        )

        self.assertEqual(
            [r.status_code for r in (detail, wahl, start, einwilligung)],
            [404, 404, 404, 404],
        )

    def test_beigetretene_erreichen_detail_und_wahl(self) -> None:
        """Nach dem Beitritt ist das Training spielbar."""
        self._beitreten(self.studierende)

        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        )
        wahl: HttpResponse = self.client.get(
            reverse("training:wahl", args=[self.training.pk, self.vignette.pk])
        )

        self.assertContains(detail, "Brüche vergleichen")
        self.assertContains(wahl, "Vignette gewählt")

    def test_kreis_und_administration_erreichen_das_training_ohne_beitritt(
        self,
    ) -> None:
        """Der Kreis gibt das Training ohnehin; die Administration sieht alles."""
        ko_eigentuemerin: Konto = konto_mit_rollen("lin", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(ko_eigentuemerin)
        administratorin: Konto = konto_mit_rollen("root", is_superuser=True)

        for konto in (self.ausbilderin, ko_eigentuemerin, administratorin):
            with self.subTest(konto=konto.username):
                self.client.force_login(konto)
                katalog: HttpResponse = self.client.get(reverse("training:katalog"))
                detail: HttpResponse = self.client.get(
                    reverse("training:detail", args=[self.training.pk])
                )
                self.assertContains(katalog, "Bruchrechnung")
                self.assertContains(detail, "Brüche vergleichen")

    def test_trainingsseite_zeigt_den_festen_hinweis_zur_fremdeinsicht(
        self,
    ) -> None:
        """Teilnehmende lesen, dass der Kreis ihre Sitzungen einsieht."""
        self._beitreten(self.studierende)

        response: HttpResponse = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        )

        self.assertContains(
            response,
            "Die Ausbilder:innen dieses Trainings sehen Ihre abgeschlossenen "
            "Sitzungen namentlich.",
        )


class TrainingsLinkAufDerKuratierseiteTests(TestCase):
    """Der Kreis findet, kopiert, sperrt und öffnet den Trainings-Link."""

    def setUp(self) -> None:
        self.ausbilderin: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.ko_eigentuemerin: Konto = konto_mit_rollen("lin", AUSBILDERIN_GRUPPE)
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.eigentuemerinnen.add(self.ko_eigentuemerin)
        self.training.veroeffentlichen()

    def test_kuratierseite_zeigt_den_link_zum_kopieren(self) -> None:
        """Der volle Link steht lesbar neben dem Kopieren-Knopf."""
        seite: str = kuratierseite(self.client, self.training, self.ausbilderin)

        self.assertIn("Gruppe beitreten lassen", seite)
        self.assertIn(f"http://testserver{_beitritt_url(self.training)}", seite)
        self.assertIn("Kopieren", seite)
        self.assertIn("0 Personen beigetreten", seite)

    def test_ko_eigentuemerin_sperrt_den_beitritt(self) -> None:
        """Jede Eigentümerin des Kreises darf den Beitritt sperren."""
        self.client.force_login(self.ko_eigentuemerin)

        response: HttpResponse = self.client.post(
            reverse("training:beitritt_sperren", args=[self.training.pk]),
            follow=True,
        )

        self.assertContains(response, "Wieder öffnen")

    def test_ko_eigentuemerin_oeffnet_den_gesperrten_beitritt(self) -> None:
        """Jede Eigentümerin des Kreises darf den Beitritt wieder öffnen."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        self.client.force_login(self.ko_eigentuemerin)

        response: HttpResponse = self.client.post(
            reverse("training:beitritt_oeffnen", args=[self.training.pk]),
            follow=True,
        )

        self.assertContains(response, "Gruppe beitreten lassen")

    def test_fremde_ausbilderin_kann_den_beitritt_nicht_umschalten(self) -> None:
        """Außerhalb des Kreises gibt es das Training nicht."""
        self.client.force_login(konto_mit_rollen("eve", AUSBILDERIN_GRUPPE))

        response: HttpResponse = self.client.post(
            reverse("training:beitritt_sperren", args=[self.training.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_fremder_umschaltversuch_laesst_den_beitritt_offen(self) -> None:
        """Nach dem abgewiesenen Versuch kommt die Gruppe weiter hinein."""
        self.client.force_login(konto_mit_rollen("eve", AUSBILDERIN_GRUPPE))
        self.client.post(reverse("training:beitritt_sperren", args=[self.training.pk]))
        self.client.force_login(konto_mit_rollen("grace"))

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )

    def test_umschalten_nur_per_post(self) -> None:
        """Ein bloßer Aufruf schaltet nichts."""
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(
            reverse("training:beitritt_sperren", args=[self.training.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_band_eines_entwurfs_vertroestet_auf_das_veroeffentlichen(
        self,
    ) -> None:
        """Vor dem Veröffentlichen nimmt der Link niemanden auf."""
        entwurf: Training = Training.objects.anlegen(self.ausbilderin, name="Entwurf")
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[entwurf.pk])
        )

        self.assertContains(
            response, "Der Beitritt ist erst nach dem Veröffentlichen möglich."
        )

    def test_band_zaehlt_die_beigetretenen(self) -> None:
        """Die Zeile unter dem Link nennt die Zahl der Beigetretenen."""
        for name in ("grace", "linus"):
            self.client.force_login(konto_mit_rollen(name))
            self.client.get(_beitritt_url(self.training))

        self.assertIn(
            "2 Personen beigetreten",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

    def test_gesperrtes_band_nennt_eine_beigetretene_person_in_der_einzahl(
        self,
    ) -> None:
        """Auch im gesperrten Band steht die Einzahl richtig."""
        self.client.force_login(konto_mit_rollen("grace"))
        self.client.get(_beitritt_url(self.training))
        self.client.force_login(self.ausbilderin)
        self.client.post(reverse("training:beitritt_sperren", args=[self.training.pk]))

        self.assertIn(
            "1 Person ist bereits dabei",
            kuratierseite(self.client, self.training, self.ausbilderin),
        )

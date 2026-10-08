"""HTTP-Tests für das geschlossene Training und den Beitritt über den Trainings-Link."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE
from sitzungen.models import Teilnahme
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette, Vignettenhistorie


def _konto(username: str, gruppe: str | None = None) -> Konto:
    konto: Konto = get_user_model().objects.create_user(username=username)
    if gruppe is not None:
        konto.groups.add(Group.objects.get_or_create(name=gruppe)[0])
    return konto


def _finale_vignette(name: str) -> Vignette:
    return Vignette.objects._erstellen(
        historie=Vignettenhistorie.objects.create(name=name),
        zustand=Vignette.Zustand.FINAL,
        finalisiert_am=timezone.now(),
        lernauftrag_text="Vergleiche Brüche.",
        arbeitsheft_text="3/4 ist größer als 2/3.",
    )


def _beitritt_url(training: Training) -> str:
    return reverse("training:beitreten", args=[training.trainings_link])


class BeitrittTests(TestCase):
    """Wer den Trainings-Link eingeloggt öffnet, tritt dem Training bei."""

    def setUp(self) -> None:
        self.ausbilderin: Konto = _konto("ada", AUSBILDERIN_GRUPPE)
        self.studierende: Konto = _konto("grace")
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.veroeffentlichen()

    def test_jedes_training_hat_einen_eigenen_trainings_link(self) -> None:
        """Zwei Trainings teilen sich nie einen Link."""
        anderes: Training = Training.objects.anlegen(self.ausbilderin, name="Zahlen")

        self.assertIsNotNone(self.training.trainings_link)
        self.assertNotEqual(self.training.trainings_link, anderes.trainings_link)

    def test_beitritt_legt_die_bindung_an_und_fuehrt_ins_training(self) -> None:
        """Der eingeloggte Aufruf bindet das Konto und leitet zur Trainingsseite."""
        self.client.force_login(self.studierende)

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )
        self.assertTrue(
            Trainingsbindung.objects.filter(
                training=self.training, konto=self.studierende
            ).exists()
        )

    def test_erneutes_oeffnen_legt_keine_zweite_bindung_an(self) -> None:
        """Wer schon beigetreten ist, landet ohne Fehler direkt im Training."""
        self.client.force_login(self.studierende)
        self.client.get(_beitritt_url(self.training))

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertRedirects(
            response, reverse("training:detail", args=[self.training.pk])
        )
        self.assertEqual(
            Trainingsbindung.objects.filter(
                training=self.training, konto=self.studierende
            ).count(),
            1,
        )
        self.assertEqual(Teilnahme.objects.count(), 1)

    def test_ohne_login_fuehrt_der_link_ueber_den_login_zurueck(self) -> None:
        """Der Login kennt den Beitritt als Ziel und kehrt dorthin zurück."""
        url: str = _beitritt_url(self.training)

        response: HttpResponse = self.client.get(url)

        self.assertRedirects(
            response, f"{reverse('login')}?next={url}", fetch_redirect_response=False
        )
        self.assertFalse(Trainingsbindung.objects.exists())

    def test_gesperrter_link_legt_keine_bindung_an_und_meldet_das(self) -> None:
        """Bei gesperrtem Beitritt erscheint eine verständliche Meldung."""
        self.training.beitritt_gesperrt = True
        self.training.save(update_fields=["beitritt_gesperrt"])
        self.client.force_login(self.studierende)

        response: HttpResponse = self.client.get(_beitritt_url(self.training))

        self.assertContains(response, "Beitritt gesperrt", status_code=403)
        self.assertContains(response, "Bruchrechnung", status_code=403)
        self.assertFalse(Trainingsbindung.objects.exists())

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

    def test_link_eines_entwurfs_ist_unbekannt(self) -> None:
        """Ein Entwurf nimmt noch niemanden auf."""
        entwurf: Training = Training.objects.anlegen(self.ausbilderin, name="Entwurf")
        self.client.force_login(self.studierende)

        response: HttpResponse = self.client.get(_beitritt_url(entwurf))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Trainingsbindung.objects.exists())

    def test_leeres_training_laesst_sich_veroeffentlichen_und_beitreten(
        self,
    ) -> None:
        """Ein Training ohne Vignetten ist ein gültiger Anlass."""
        leer: Training = Training.objects.anlegen(self.ausbilderin, name="Sammelanlass")
        self.client.force_login(self.ausbilderin)
        self.client.post(reverse("training:veroeffentlichen", args=[leer.pk]))
        leer.refresh_from_db()
        self.assertEqual(leer.zustand, Training.Zustand.VEROEFFENTLICHT)
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
        self.ausbilderin: Konto = _konto("ada", AUSBILDERIN_GRUPPE)
        self.studierende: Konto = _konto("grace")
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.vignette: Vignette = _finale_vignette("Brüche vergleichen")
        self.training.vignetten.add(self.vignette)
        self.training.veroeffentlichen()

    def _beitreten(self, konto: Konto) -> None:
        self.client.force_login(konto)
        self.client.get(_beitritt_url(self.training))

    def test_katalog_zeigt_teilnehmenden_nur_beigetretene_trainings(self) -> None:
        """Ein veröffentlichtes Training ist nicht mehr für alle sichtbar."""
        Training.objects.anlegen(
            self.ausbilderin, name="Fremdes Seminar"
        ).veroeffentlichen()
        self._beitreten(self.studierende)

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertContains(response, "Bruchrechnung")
        self.assertNotContains(response, "Fremdes Seminar")

    def test_katalog_ohne_beitritt_ist_leer(self) -> None:
        """Wer keinem Training beigetreten ist, sieht keines."""
        self.client.force_login(self.studierende)

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertNotContains(response, "Bruchrechnung")

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

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(wahl.status_code, 404)
        self.assertEqual(start.status_code, 404)
        self.assertEqual(einwilligung.status_code, 404)
        self.assertFalse(Trainingsbindung.objects.exists())

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

    def test_bestehende_bindung_gilt_als_beitritt(self) -> None:
        """Eine Bindung aus der Zeit vor dem Trainings-Link behält den Zugang."""
        Trainingsbindung.objects.create(
            teilnahme=Teilnahme.objects.create(),
            training=self.training,
            konto=self.studierende,
        )
        self.client.force_login(self.studierende)

        katalog: HttpResponse = self.client.get(reverse("training:katalog"))
        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        )

        self.assertContains(katalog, "Bruchrechnung")
        self.assertContains(detail, "Brüche vergleichen")

    def test_kreis_und_administration_erreichen_das_training_ohne_beitritt(
        self,
    ) -> None:
        """Der Kreis gibt das Training ohnehin; die Administration sieht alles."""
        ko_eigentuemerin: Konto = _konto("lin", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(ko_eigentuemerin)
        administratorin: Konto = get_user_model().objects.create_user(
            username="root", is_superuser=True
        )

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
        self.ausbilderin: Konto = _konto("ada", AUSBILDERIN_GRUPPE)
        self.ko_eigentuemerin: Konto = _konto("lin", AUSBILDERIN_GRUPPE)
        self.training: Training = Training.objects.anlegen(
            self.ausbilderin, name="Bruchrechnung"
        )
        self.training.eigentuemerinnen.add(self.ko_eigentuemerin)
        self.training.veroeffentlichen()

    def _kuratierseite(self) -> HttpResponse:
        return self.client.get(reverse("training:kuratieren", args=[self.training.pk]))

    def test_kuratierseite_zeigt_den_link_zum_kopieren(self) -> None:
        """Der volle Link steht lesbar neben dem Kopieren-Knopf."""
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self._kuratierseite()

        self.assertContains(response, "Gruppe beitreten lassen")
        self.assertContains(
            response, f"http://testserver{_beitritt_url(self.training)}"
        )
        self.assertContains(response, "Kopieren")
        self.assertContains(response, "0 Personen beigetreten")

    def test_ko_eigentuemerin_sperrt_und_oeffnet_den_beitritt(self) -> None:
        """Jede Eigentümerin des Kreises darf den Beitritt umschalten."""
        self.client.force_login(self.ko_eigentuemerin)

        sperren: HttpResponse = self.client.post(
            reverse("training:beitritt_sperren", args=[self.training.pk])
        )
        self.training.refresh_from_db()
        self.assertTrue(self.training.beitritt_gesperrt)
        self.assertRedirects(
            sperren, reverse("training:kuratieren", args=[self.training.pk])
        )
        gesperrt: HttpResponse = self._kuratierseite()
        self.assertContains(gesperrt, "Beitritt gesperrt")
        self.assertContains(gesperrt, "Wieder öffnen")

        self.client.post(reverse("training:beitritt_oeffnen", args=[self.training.pk]))
        self.training.refresh_from_db()
        self.assertFalse(self.training.beitritt_gesperrt)
        self.assertContains(self._kuratierseite(), "Sperren")

    def test_fremde_ausbilderin_kann_den_beitritt_nicht_umschalten(self) -> None:
        """Außerhalb des Kreises gibt es das Training nicht."""
        self.client.force_login(_konto("eve", AUSBILDERIN_GRUPPE))

        response: HttpResponse = self.client.post(
            reverse("training:beitritt_sperren", args=[self.training.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.training.refresh_from_db()
        self.assertFalse(self.training.beitritt_gesperrt)

    def test_umschalten_nur_per_post(self) -> None:
        """Ein bloßer Aufruf schaltet nichts."""
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(
            reverse("training:beitritt_sperren", args=[self.training.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_band_zaehlt_die_beigetretenen(self) -> None:
        """Die Zeile unter dem Link nennt die Zahl der Beigetretenen."""
        for name in ("grace", "linus"):
            self.client.force_login(_konto(name))
            self.client.get(_beitritt_url(self.training))
        self.client.force_login(self.ausbilderin)

        self.assertContains(self._kuratierseite(), "2 Personen beigetreten")

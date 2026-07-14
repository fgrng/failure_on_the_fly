"""HTTP-Tests für die Ausbilder-UI der Trainings."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from training.models import Training
from vignetten.models import Vignette, Vignettenhistorie


class TrainingAnlegenTests(TestCase):
    """Ausbilder:innen legen Trainings über die HTTP-Views an."""

    def test_legt_training_an_und_listet_nur_eigene_trainings(self) -> None:
        """Ein angelegtes Training erscheint nur bei seiner Eigentümerin."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        Training.objects.create(name="Fremdes Training", eigentuemerin=grace)
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("training:anlegen"), {"name": "Brüche üben"}
        )

        training: Training = Training.objects.get(eigentuemerin=ada)
        self.assertRedirects(response, reverse("training:kuratieren", args=[training.pk]))
        liste: HttpResponse = self.client.get(reverse("training:liste"))
        self.assertContains(liste, "Brüche üben")
        self.assertNotContains(liste, "Fremdes Training")


class TrainingKuratierenTests(TestCase):
    """Ausbilder:innen kuratieren finale Vignetten ihres Eigentümer-Kreises."""

    def test_nimmt_nur_eigene_finale_vignetten_auf_und_entfernt_sie_wieder(
        self,
    ) -> None:
        """Auswahl, Austausch und Veröffentlichen laufen über HTTP."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        eigene_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        eigene_historie.eigentuemerinnen.add(ada)
        finale: Vignette = Vignette.objects._erstellen(
            historie=eigene_historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            fach="Brüche",
            arbeitsheft_text="1/2",
        )
        Vignette.objects._erstellen(
            historie=eigene_historie, fach="Nichtfinale Vignette"
        )
        fremde_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(grace)
        fremde_finale: Vignette = Vignette.objects._erstellen(
            historie=fremde_historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            fach="Fremd",
            arbeitsheft_text="1/2",
        )
        zweite_finale: Vignette = Vignette.objects._erstellen(
            historie=eigene_historie,
            vorgaengerin=finale,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            fach="Dezimalzahlen",
            arbeitsheft_text="0,5",
        )
        training: Training = Training.objects.create(name="Brüche", eigentuemerin=ada)
        self.client.force_login(ada)

        detail: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[training.pk])
        )

        self.assertContains(detail, "Brüche")
        self.assertNotContains(detail, "Fremd")
        self.assertNotContains(detail, "Nichtfinale Vignette")
        hinzufuegen: HttpResponse = self.client.post(
            reverse("training:vignette_hinzufuegen", args=[training.pk, finale.pk])
        )
        self.assertRedirects(
            hinzufuegen, reverse("training:kuratieren", args=[training.pk])
        )
        self.assertEqual(list(training.vignetten.all()), [finale])
        self.assertEqual(
            self.client.post(
                reverse("training:veroeffentlichen", args=[training.pk])
            ).status_code,
            302,
        )
        training.refresh_from_db()
        self.assertEqual(training.zustand, Training.Zustand.VEROEFFENTLICHT)
        nach_veroeffentlichung: HttpResponse = self.client.post(
            reverse(
                "training:vignette_hinzufuegen", args=[training.pk, zweite_finale.pk]
            )
        )
        self.assertRedirects(
            nach_veroeffentlichung,
            reverse("training:kuratieren", args=[training.pk]),
        )
        self.assertEqual(list(training.vignetten.all()), [finale, zweite_finale])
        entfernen: HttpResponse = self.client.post(
            reverse("training:vignette_entfernen", args=[training.pk, finale.pk])
        )
        self.assertRedirects(
            entfernen, reverse("training:kuratieren", args=[training.pk])
        )
        self.client.post(
            reverse("training:vignette_entfernen", args=[training.pk, zweite_finale.pk])
        )
        self.assertEqual(list(training.vignetten.all()), [])
        self.assertFalse(training.vignetten.filter(pk=fremde_finale.pk).exists())


class TrainingSichtbarkeitTests(TestCase):
    """Fremde Trainings existieren über die HTTP-Views nicht."""

    def test_fremdes_training_gibt_auch_ueber_die_detail_url_404(self) -> None:
        """Die Detail-View lädt ausschließlich über sichtbar_fuer()."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremdes: Training = Training.objects.create(
            name="Fremdes Training", eigentuemerin=grace
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[fremdes.pk])
        )

        self.assertEqual(response.status_code, 404)


class VeroeffentlichteTrainingsTests(TestCase):
    """Nur veröffentlichte Trainings sind für den Katalog abfragbar."""

    def test_entwurf_erscheint_nicht_im_veroeffentlichten_queryset(self) -> None:
        """Ein frisch angelegtes Training bleibt bis zum Übergang unsichtbar."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        entwurf: Training = Training.objects.create(name="Brüche", eigentuemerin=ada)

        self.assertNotIn(entwurf, Training.objects.veroeffentlicht())

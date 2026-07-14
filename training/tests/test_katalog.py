"""HTTP-Tests für den offenen Trainingskatalog."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from training.models import Training
from vignetten.models import Vignette, Vignettenhistorie


class TrainingskatalogTests(TestCase):
    """Eingeloggte Konten wählen frei aus veröffentlichten Trainings."""

    def test_zeigt_veroeffentlichte_trainings_im_katalog_und_in_der_navigation(
        self,
    ) -> None:
        """Jedes eingeloggte Konto findet alle veröffentlichten Trainings."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        training.veroeffentlichen()
        self.client.force_login(studierende)

        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertContains(response, "Bruchrechnung")
        self.assertContains(response, reverse("training:detail", args=[training.pk]))
        self.assertContains(response, reverse("training:katalog"))

    def test_versteckt_unveroeffentlichte_trainings(self) -> None:
        """Entwürfe erscheinen weder im Katalog noch über ihre Detail-URL."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        entwurf: Training = Training.objects.create(
            name="Versteckte Bruchrechnung", eigentuemerin=ausbilderin
        )
        self.client.force_login(studierende)

        katalog: HttpResponse = self.client.get(reverse("training:katalog"))
        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[entwurf.pk])
        )

        self.assertNotContains(katalog, "Versteckte Bruchrechnung")
        self.assertEqual(detail.status_code, 404)

    def test_listet_finale_vignetten_und_bestaetigt_freie_wahl(self) -> None:
        """Eine veröffentlichte Sammlung verlinkt jede eingebundene Vignette."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Brüche vergleichen"
        )
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="3/4 ist größer als 2/3.",
        )
        training.vignetten.add(vignette)
        training.veroeffentlichen()
        self.client.force_login(studierende)

        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[training.pk])
        )
        wahl_url: str = reverse("training:wahl", args=[training.pk, vignette.pk])
        wahl: HttpResponse = self.client.get(wahl_url)

        self.assertContains(detail, "Brüche vergleichen")
        self.assertContains(detail, wahl_url)
        self.assertContains(wahl, "Vignette gewählt")

    def test_katalog_erfordert_anmeldung(self) -> None:
        """Ohne Konto führt der Katalog zum Login statt Inhalte preiszugeben."""
        response: HttpResponse = self.client.get(reverse("training:katalog"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('training:katalog')}",
            fetch_redirect_response=False,
        )

    def test_versteckt_nachtraeglich_archivierte_vignette(self) -> None:
        """Archivierte Fassungen bleiben trotz bestehender Bindung unspielbar."""
        ausbilderin: Konto = get_user_model().objects.create_user(username="ada")
        studierende: Konto = get_user_model().objects.create_user(username="grace")
        training: Training = Training.objects.create(
            name="Bruchrechnung", eigentuemerin=ausbilderin
        )
        historie: Vignettenhistorie = Vignettenhistorie.objects.create(
            name="Archivierte Brüche"
        )
        vignette: Vignette = Vignette.objects._erstellen(
            historie=historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            arbeitsheft_text="3/4 ist größer als 2/3.",
        )
        training.vignetten.add(vignette)
        vignette.archivieren()
        training.veroeffentlichen()
        self.client.force_login(studierende)

        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[training.pk])
        )
        wahl: HttpResponse = self.client.get(
            reverse("training:wahl", args=[training.pk, vignette.pk])
        )

        self.assertNotContains(detail, "Archivierte Brüche")
        self.assertEqual(wahl.status_code, 404)

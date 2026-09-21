"""HTTP-Tests für die Ausbilder-UI der Trainings."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        Training.objects.anlegen(grace, name="Fremdes Training")
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("training:anlegen"), {"name": "Gleichungen"}
        )

        training: Training = Training.objects.get(eigentuemerinnen=ada)
        self.assertRedirects(
            response, reverse("training:kuratieren", args=[training.pk])
        )
        liste: HttpResponse = self.client.get(reverse("training:liste"))
        self.assertContains(liste, "Gleichungen")
        self.assertNotContains(liste, "Fremdes Training")

    def test_konto_ohne_ausbilderrolle_kann_kein_training_anlegen(self) -> None:
        """Die Ausbilder-UI weist eingeloggte Teilnehmer:innen zurück."""
        teilnehmerin: Konto = get_user_model().objects.create_user(username="grace")
        self.client.force_login(teilnehmerin)

        response: HttpResponse = self.client.post(
            reverse("training:anlegen"), {"name": "Kein Training"}
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get(reverse("training:liste")).status_code, 403)
        for url in (
            reverse("training:kuratieren", args=[1]),
            reverse("training:vignette_hinzufuegen", args=[1, 1]),
            reverse("training:vignette_entfernen", args=[1, 1]),
            reverse("training:veroeffentlichen", args=[1]),
        ):
            self.assertEqual(self.client.post(url).status_code, 403)
        self.assertFalse(Training.objects.exists())

    def test_administratorin_erreicht_alle_sichtbaren_trainings(self) -> None:
        """Die administrative Sonderrolle darf die Ausbilder-UI vollständig nutzen."""
        administratorin: Konto = get_user_model().objects.create_user(username="linus")
        administratorin.is_superuser = True
        administratorin.save()
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        eigenes: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
        fremdes: Training = Training.objects.anlegen(grace, name="Prozente")
        self.client.force_login(administratorin)

        liste: HttpResponse = self.client.get(reverse("training:liste"))
        angelegt: HttpResponse = self.client.post(
            reverse("training:anlegen"), {"name": "Neues Training"}
        )
        veroeffentlicht: HttpResponse = self.client.post(
            reverse("training:veroeffentlichen", args=[eigenes.pk])
        )

        self.assertContains(liste, eigenes.name)
        self.assertContains(liste, fremdes.name)
        self.assertEqual(angelegt.status_code, 302)
        self.assertEqual(veroeffentlicht.status_code, 302)

    def test_koeigentuemerin_kann_training_kuratieren_und_veroeffentlichen(
        self,
    ) -> None:
        """Eine Ko-Eigentümerin hat in der Ausbilder-UI dieselben Rechte."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Bruchrechnung")
        training.eigentuemerinnen.add(grace)
        self.client.force_login(grace)

        kuratieren: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[training.pk])
        )
        veroeffentlichen: HttpResponse = self.client.post(
            reverse("training:veroeffentlichen", args=[training.pk])
        )

        self.assertContains(kuratieren, training.name)
        self.assertRedirects(
            veroeffentlichen, reverse("training:kuratieren", args=[training.pk])
        )
        training.refresh_from_db()
        self.assertEqual(training.zustand, Training.Zustand.VEROEFFENTLICHT)


class TrainingKuratierenTests(TestCase):
    """Ausbilder:innen kuratieren finale Vignetten ihres Eigentümer-Kreises."""

    def test_zeigt_den_eigentuemer_kreis(self) -> None:
        """Die Kuratierungsansicht macht den Eigentümer-Kreis sichtbar."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[training.pk])
        )

        self.assertContains(response, "Eigentümer:innen")
        self.assertContains(response, "Eigentümer:in hinzufügen")
        self.assertContains(response, ada.username)

    def test_nimmt_nur_eigene_finale_vignetten_auf_und_entfernt_sie_wieder(
        self,
    ) -> None:
        """Auswahl, Austausch und Veröffentlichen laufen über HTTP."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        eigene_historie: Vignettenhistorie = Vignettenhistorie.objects.create()
        eigene_historie.eigentuemerinnen.add(ada)
        finale: Vignette = Vignette.objects._erstellen(
            historie=eigene_historie,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Vergleiche Brüche.",
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
            lernauftrag_text="Vergleiche Brüche.",
            fach="Fremd",
            arbeitsheft_text="1/2",
        )
        zweite_finale: Vignette = Vignette.objects._erstellen(
            historie=eigene_historie,
            vorgaengerin=finale,
            zustand=Vignette.Zustand.FINAL,
            finalisiert_am=timezone.now(),
            lernauftrag_text="Vergleiche Brüche.",
            fach="Dezimalzahlen",
            arbeitsheft_text="0,5",
        )
        training: Training = Training.objects.anlegen(ada, name="Brüche")
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


class TrainingKoautorschaftTests(TestCase):
    """Ausbilder:innen teilen Trainings mit gleichrangigen Ko-Eigentümerinnen."""

    def test_hinzufuegen_gibt_koeigentuemern_listenzugriff(self) -> None:
        """Eine eingetragene Ausbilderin sieht das Training in ihrer Liste."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("training:eigentuemerin_hinzufuegen", args=[training.pk]),
            {"konto": grace.pk},
        )

        self.assertRedirects(
            response, reverse("training:kuratieren", args=[training.pk])
        )
        self.client.force_login(grace)
        self.assertContains(
            self.client.get(reverse("training:liste")),
            reverse("training:kuratieren", args=[training.pk]),
        )

    def test_hinzufuegen_erlaubt_koeigentuemern_das_veroeffentlichen(self) -> None:
        """Eine eingetragene Ausbilderin darf das Training veröffentlichen."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        self.client.force_login(ada)
        self.client.post(
            reverse("training:eigentuemerin_hinzufuegen", args=[training.pk]),
            {"konto": grace.pk},
        )
        self.client.force_login(grace)

        self.assertRedirects(
            self.client.post(reverse("training:veroeffentlichen", args=[training.pk])),
            reverse("training:kuratieren", args=[training.pk]),
        )

    def test_selbstentfernung_uebergibt_training(self) -> None:
        """Die Übergabe entfernt die eigene Person bei verbleibender Ko-Autorin."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        training.eigentuemerinnen.add(grace)
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("training:eigentuemerin_entfernen", args=[training.pk, ada.pk])
        )

        self.assertRedirects(response, reverse("training:liste"))
        self.assertEqual(
            self.client.get(
                reverse("training:kuratieren", args=[training.pk])
            ).status_code,
            404,
        )

    def test_entfernen_der_letzten_eigentuemerin_wird_verweigert(self) -> None:
        """Der Eigentümer-Kreis eines Trainings bleibt besetzt."""
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(grace, name="Brüche")
        self.client.force_login(grace)
        self.client.post(
            reverse("training:eigentuemerin_entfernen", args=[training.pk, grace.pk])
        )
        self.assertContains(
            self.client.get(reverse("training:kuratieren", args=[training.pk])),
            grace.username,
        )

    def test_hinzufuegen_erfordert_bestehende_ausbilderrolle(self) -> None:
        """Teilen akzeptiert keine Konten ohne Ausbilder- oder Administrationsrolle."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        ohne_rolle: Konto = get_user_model().objects.create_user(username="linus")
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("training:eigentuemerin_hinzufuegen", args=[training.pk]),
            {"konto": ohne_rolle.pk},
        )

        self.assertEqual(response.status_code, 404)
        self.client.force_login(ohne_rolle)
        self.assertEqual(self.client.get(reverse("training:liste")).status_code, 403)

    def test_hinzufuegen_akzeptiert_administratorinnen(self) -> None:
        """Eine Administratorin kann als Ko-Eigentümerin eingetragen werden."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        administratorin: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        self.client.force_login(ada)

        self.assertContains(
            self.client.get(reverse("training:kuratieren", args=[training.pk])),
            f'<option value="{administratorin.pk}">{administratorin.username}</option>',
            html=True,
        )
        self.client.post(
            reverse("training:eigentuemerin_hinzufuegen", args=[training.pk]),
            {"konto": administratorin.pk},
        )
        self.client.force_login(administratorin)

        self.assertContains(
            self.client.get(reverse("training:liste")),
            reverse("training:kuratieren", args=[training.pk]),
        )

    def test_veroeffentlichtes_training_kann_weiter_uebergeben_werden(self) -> None:
        """Die Veröffentlichung friert die Verantwortung nicht ein."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        training.veroeffentlichen()
        self.client.force_login(ada)

        self.client.post(
            reverse("training:eigentuemerin_hinzufuegen", args=[training.pk]),
            {"konto": grace.pk},
        )
        self.client.post(
            reverse("training:eigentuemerin_entfernen", args=[training.pk, ada.pk])
        )

        self.client.force_login(grace)

        self.assertContains(
            self.client.get(reverse("training:kuratieren", args=[training.pk])),
            "Veröffentlicht",
        )

    def test_administration_kann_fremdes_training_uebergeben(self) -> None:
        """Die Administration kann eine fremde Ausbilderin durch eine andere ablösen."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        administratorin: Konto = get_user_model().objects.create_user(username="linus")
        administratorin.is_superuser = True
        administratorin.save()
        training: Training = Training.objects.anlegen(grace, name="Brüche")
        self.client.force_login(administratorin)

        self.client.post(
            reverse("training:eigentuemerin_hinzufuegen", args=[training.pk]),
            {"konto": ada.pk},
        )
        response: HttpResponse = self.client.post(
            reverse("training:eigentuemerin_entfernen", args=[training.pk, grace.pk])
        )

        self.assertRedirects(
            response, reverse("training:kuratieren", args=[training.pk])
        )
        self.client.force_login(grace)
        self.assertEqual(
            self.client.get(
                reverse("training:kuratieren", args=[training.pk])
            ).status_code,
            404,
        )

    def test_nicht_eigentuemerin_kann_keine_uebergabe_ausloesen(self) -> None:
        """Eine fremde Administration bleibt beim Training, wenn sie niemanden entfernt."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Ausbilder:in"))
        administratorin: Konto = get_user_model().objects.create_user(username="linus")
        administratorin.is_superuser = True
        administratorin.save()
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        training.eigentuemerinnen.add(grace)
        self.client.force_login(administratorin)

        response: HttpResponse = self.client.post(
            reverse(
                "training:eigentuemerin_entfernen",
                args=[training.pk, administratorin.pk],
            )
        )

        self.assertRedirects(
            response, reverse("training:kuratieren", args=[training.pk])
        )

    def test_eigentuemerin_hinzufuegen_ist_nur_per_post_erreichbar(self) -> None:
        """Das Hinzufügen weist GET-Anfragen ab."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        self.client.force_login(ada)

        hinzufuegen: HttpResponse = self.client.get(
            reverse("training:eigentuemerin_hinzufuegen", args=[training.pk])
        )
        self.assertEqual(hinzufuegen.status_code, 405)

    def test_eigentuemerin_entfernen_ist_nur_per_post_erreichbar(self) -> None:
        """Das Entfernen weist GET-Anfragen ab."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Brüche")
        self.client.force_login(ada)

        entfernen: HttpResponse = self.client.get(
            reverse("training:eigentuemerin_entfernen", args=[training.pk, ada.pk])
        )

        self.assertEqual(entfernen.status_code, 405)


class TrainingSichtbarkeitTests(TestCase):
    """Fremde Trainings existieren über die HTTP-Views nicht."""

    def test_fremdes_training_gibt_auch_ueber_die_detail_url_404(self) -> None:
        """Die Detail-View lädt ausschließlich über sichtbar_fuer()."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremdes: Training = Training.objects.anlegen(grace, name="Fremdes Training")
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
        entwurf: Training = Training.objects.anlegen(ada, name="Brüche")

        self.assertNotIn(entwurf, Training.objects.veroeffentlicht())

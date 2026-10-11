"""HTTP-Tests für die Ausbilder-UI der Trainings."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import finale_vignette, konto_mit_rollen, vignetten_entwurf
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE
from training.models import Training
from training.tests.seite import kuratierseite, nummerierte_vignetten, tabellenzeilen
from vignetten.models import Vignette


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

    def test_zeilen_sind_ueber_den_namen_verlinkt(self) -> None:
        """Der Name führt zum Kuratieren; der Zeilenhinweis nennt »Kuratieren ›«."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        training: Training = Training.objects.anlegen(ada, name="Gleichungen")
        self.client.force_login(ada)

        liste: HttpResponse = self.client.get(reverse("training:liste"))

        kuratier_url: str = reverse("training:kuratieren", args=[training.pk])
        self.assertContains(liste, kuratier_url)
        self.assertContains(liste, "Kuratieren ›")
        self.assertEqual(
            [(zeile["name"], zeile["url"]) for zeile in tabellenzeilen(liste)],
            [("Gleichungen", kuratier_url)],
        )

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
        self.assertContains(response, "Wer dieses Training sehen und bearbeiten darf")

    def test_nimmt_nur_eigene_finale_vignetten_auf_und_entfernt_sie_wieder(
        self,
    ) -> None:
        """Auswahl, Austausch und Veröffentlichen laufen über HTTP."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        finale: Vignette = finale_vignette(ada, name="Brüche")
        entwurf: Vignette = vignetten_entwurf(ada)
        fremde_finale: Vignette = finale_vignette(grace, name="Fremd")
        zweite_finale: Vignette = finale_vignette(ada, name="Dezimalzahlen")
        training: Training = Training.objects.anlegen(ada, name="Bruchtraining")
        kuratieren_url: str = reverse("training:kuratieren", args=[training.pk])
        self.client.force_login(ada)

        def hinzufuegen_url(vignette: Vignette) -> str:
            # Adresse der Hinzufügen-Aktion für die Vignette in diesem Training.

            return reverse(
                "training:vignette_hinzufuegen", args=[training.pk, vignette.pk]
            )

        def entfernen_url(vignette: Vignette) -> str:
            # Adresse der Entfernen-Aktion für die Vignette in diesem Training.

            return reverse(
                "training:vignette_entfernen", args=[training.pk, vignette.pk]
            )

        detail: HttpResponse = self.client.get(kuratieren_url)

        self.assertContains(detail, hinzufuegen_url(finale))
        self.assertContains(detail, hinzufuegen_url(zweite_finale))
        self.assertNotContains(detail, hinzufuegen_url(fremde_finale))
        self.assertNotContains(detail, hinzufuegen_url(entwurf))
        self.assertEqual(
            self.client.post(hinzufuegen_url(fremde_finale)).status_code, 404
        )
        self.assertEqual(self.client.post(hinzufuegen_url(entwurf)).status_code, 404)

        hinzufuegen: HttpResponse = self.client.post(hinzufuegen_url(finale))

        self.assertRedirects(hinzufuegen, kuratieren_url)
        nach_aufnahme: HttpResponse = self.client.get(kuratieren_url)
        self.assertContains(nach_aufnahme, entfernen_url(finale))
        self.assertNotContains(nach_aufnahme, hinzufuegen_url(finale))
        self.assertEqual(
            self.client.post(
                reverse("training:veroeffentlichen", args=[training.pk])
            ).status_code,
            302,
        )
        training.refresh_from_db()
        self.assertEqual(training.zustand, Training.Zustand.VEROEFFENTLICHT)
        nach_veroeffentlichung: HttpResponse = self.client.post(
            hinzufuegen_url(zweite_finale)
        )
        self.assertRedirects(nach_veroeffentlichung, kuratieren_url)
        beide: HttpResponse = self.client.get(kuratieren_url)
        self.assertContains(beide, entfernen_url(finale))
        self.assertContains(beide, entfernen_url(zweite_finale))
        entfernen: HttpResponse = self.client.post(entfernen_url(finale))
        self.assertRedirects(entfernen, kuratieren_url)
        self.client.post(entfernen_url(zweite_finale))
        leer: HttpResponse = self.client.get(kuratieren_url)
        self.assertContains(leer, "Noch keine Vignetten aufgenommen.")
        self.assertContains(leer, hinzufuegen_url(finale))
        self.assertContains(leer, hinzufuegen_url(zweite_finale))


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


class TrainingsreihenfolgeTests(TestCase):
    """Die Vignetten eines Trainings erscheinen nummeriert in ihrer Reihenfolge."""

    def setUp(self) -> None:
        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Ausbilder:in"))
        self.training: Training = Training.objects.anlegen(self.ada, name="Brüche")
        self.erste: Vignette = finale_vignette(self.ada, name="Erweitern")
        self.zweite: Vignette = finale_vignette(self.ada, name="Kürzen")
        self.dritte: Vignette = finale_vignette(self.ada, name="Addieren")

    def _post(self, aktion: str, vignette: Vignette) -> None:
        # Löst eine Kuratier-Aktion für die Vignette in diesem Training aus.

        self.client.force_login(self.ada)
        self.client.post(
            reverse(f"training:vignette_{aktion}", args=[self.training.pk, vignette.pk])
        )

    def test_kuratieren_zeigt_die_vignetten_in_aufnahmereihenfolge(self) -> None:
        """Neu Aufgenommenes steht am Ende, Entferntes lässt nachrücken."""
        self._post("hinzufuegen", self.zweite)
        self._post("hinzufuegen", self.dritte)
        self._post("hinzufuegen", self.erste)
        self._post("entfernen", self.dritte)

        self.assertEqual(
            nummerierte_vignetten(kuratierseite(self.client, self.training, self.ada)),
            ["1. Kürzen", "2. Erweitern"],
        )

    def _detailseite_der_teilnehmerin(self) -> HttpResponse:
        # Veröffentlicht das Training mit Addieren, Erweitern, Kürzen in dieser
        # Reihenfolge und ruft seine Detailseite als Beigetretene auf.

        for vignette in (self.dritte, self.erste, self.zweite):
            self.training.vignette_aufnehmen(vignette)
        self.training.veroeffentlichen()
        grace: Konto = get_user_model().objects.create_user(username="grace")
        self.training.beitreten(grace)
        self.client.force_login(grace)
        return self.client.get(reverse("training:detail", args=[self.training.pk]))

    def test_teilnehmende_sehen_die_vignetten_nummeriert(self) -> None:
        """Die Detailseite folgt der empfohlenen Reihenfolge."""
        detail: HttpResponse = self._detailseite_der_teilnehmerin()

        self.assertEqual(
            nummerierte_vignetten(detail.content.decode()),
            ["1. Addieren", "2. Erweitern", "3. Kürzen"],
        )

    def test_teilnehmende_starten_jede_vignette_unabhaengig_von_ihrer_nummer(
        self,
    ) -> None:
        """Jede Vignette bleibt startbar, nicht nur die erste."""
        detail: HttpResponse = self._detailseite_der_teilnehmerin()

        for vignette in (self.dritte, self.erste, self.zweite):
            self.assertContains(
                detail, reverse("training:wahl", args=[self.training.pk, vignette.pk])
            )


class VignettenVerschiebenTests(TestCase):
    """Die Ausbilder:in sortiert die Vignetten eines Trainings mit Hoch/Runter um."""

    def setUp(self) -> None:
        self.ada: Konto = konto_mit_rollen("ada", AUSBILDERIN_GRUPPE)
        self.training: Training = Training.objects.anlegen(self.ada, name="Brüche")
        self.vignetten: list[Vignette] = [
            finale_vignette(self.ada, name=name)
            for name in ("Erweitern", "Kürzen", "Addieren")
        ]
        for vignette in self.vignetten:
            self.training.vignette_aufnehmen(vignette)

    def _verschieben(
        self, konto: Konto, vignette: Vignette, position: int
    ) -> HttpResponse:
        # Verschiebt die Vignette als das Konto an die Zielposition.

        self.client.force_login(konto)
        return self.client.post(
            reverse(
                "training:vignette_verschieben",
                args=[self.training.pk, vignette.pk],
            ),
            {"position": position},
        )

    def _knopf_druecken(self, vignette: Vignette, richtung: str) -> None:
        # Sendet das Formular des Knopfs, wie die Kuratierseite es ausliefert.

        seite: str = kuratierseite(self.client, self.training, self.ada)
        formular: re.Match[str] | None = re.search(
            r'<form method="post" action="([^"]+)">(?:(?!</form>).)*'
            r'name="position" value="(-?\d+)"(?:(?!</form>).)*'
            rf'aria-label="{re.escape(vignette.anzeigename)} {richtung}"',
            seite,
            re.DOTALL,
        )
        if formular is None:
            raise AssertionError(f"Kein Knopf »{richtung}« für {vignette}.")
        self.client.post(formular.group(1), {"position": formular.group(2)})

    def _reihenfolge(self) -> list[str]:
        # Die nummerierte Reihenfolge, wie die Kuratierseite sie zeigt.

        return nummerierte_vignetten(
            kuratierseite(self.client, self.training, self.ada)
        )

    def test_verschieben_im_entwurf_reiht_die_uebrigen_neu_ein(self) -> None:
        """Addieren nach oben an die erste Stelle, die übrigen rücken nach."""
        antwort: HttpResponse = self._verschieben(self.ada, self.vignetten[2], 1)

        self.assertRedirects(
            antwort, reverse("training:kuratieren", args=[self.training.pk])
        )
        self.assertEqual(
            self._reihenfolge(), ["1. Addieren", "2. Erweitern", "3. Kürzen"]
        )

    def test_hoch_tauscht_mit_der_vorigen_vignette(self) -> None:
        """Hoch rückt eine Vignette genau eine Stelle nach vorn."""
        self._knopf_druecken(self.vignetten[2], "nach oben")

        self.assertEqual(
            self._reihenfolge(), ["1. Erweitern", "2. Addieren", "3. Kürzen"]
        )

    def test_runter_tauscht_mit_der_naechsten_vignette(self) -> None:
        """Runter rückt eine Vignette genau eine Stelle nach hinten."""
        self._knopf_druecken(self.vignetten[0], "nach unten")

        self.assertEqual(
            self._reihenfolge(), ["1. Kürzen", "2. Erweitern", "3. Addieren"]
        )

    def test_verschieben_nach_dem_veroeffentlichen_zeigt_die_detailseite(
        self,
    ) -> None:
        """Teilnehmende sehen die neue Reihenfolge sofort."""
        self.training.veroeffentlichen()
        grace: Konto = get_user_model().objects.create_user(username="grace")
        self.training.beitreten(grace)

        self._verschieben(self.ada, self.vignetten[0], 3)

        self.client.force_login(grace)
        detail: HttpResponse = self.client.get(
            reverse("training:detail", args=[self.training.pk])
        )
        self.assertEqual(
            nummerierte_vignetten(detail.content.decode()),
            ["1. Kürzen", "2. Addieren", "3. Erweitern"],
        )

    def test_koeigentuemerin_und_administratorin_duerfen_verschieben(self) -> None:
        """Wer aufnehmen und entfernen darf, darf auch verschieben."""
        grace: Konto = konto_mit_rollen("grace", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(grace)
        linus: Konto = konto_mit_rollen("linus", is_superuser=True)

        self._verschieben(grace, self.vignetten[1], 1)
        self._verschieben(linus, self.vignetten[2], 1)

        self.assertEqual(
            self._reihenfolge(), ["1. Addieren", "2. Kürzen", "3. Erweitern"]
        )

    def test_fremde_konten_werden_abgewiesen(self) -> None:
        """Fremde Ausbilder:innen sehen das Training nicht, Teilnehmende nichts."""
        fremde_ausbilderin: Konto = konto_mit_rollen("grace", AUSBILDERIN_GRUPPE)
        teilnehmerin: Konto = konto_mit_rollen("linus")

        self.assertEqual(
            [
                self._verschieben(fremde_ausbilderin, self.vignetten[2], 1).status_code,
                self._verschieben(teilnehmerin, self.vignetten[2], 1).status_code,
            ],
            [404, 403],
        )
        self.assertEqual(
            self._reihenfolge(), ["1. Erweitern", "2. Kürzen", "3. Addieren"]
        )

    def test_verschieben_braucht_post_und_eine_position(self) -> None:
        """GET ist nicht erlaubt, eine fehlende Position eine fehlerhafte Anfrage."""
        url: str = reverse(
            "training:vignette_verschieben",
            args=[self.training.pk, self.vignetten[0].pk],
        )
        self.client.force_login(self.ada)

        self.assertEqual(
            [
                self.client.get(url).status_code,
                self.client.post(url).status_code,
                self.client.post(url, {"position": "oben"}).status_code,
            ],
            [405, 400, 400],
        )

    def test_nicht_aufgenommene_vignette_gibt_404(self) -> None:
        """Verschieben lässt sich nur, was im Training steht."""
        fehlende: Vignette = finale_vignette(self.ada, name="Dividieren")

        self.assertEqual(self._verschieben(self.ada, fehlende, 1).status_code, 404)

    def test_erste_hat_keinen_hoch_und_letzte_keinen_runter_knopf(self) -> None:
        """Wirkungslose Knöpfe erscheinen nicht."""
        seite: str = kuratierseite(self.client, self.training, self.ada)

        self.assertEqual(
            [
                [
                    f'aria-label="{vignette.anzeigename} {richtung}"' in seite
                    for richtung in ("nach oben", "nach unten")
                ]
                for vignette in self.vignetten
            ],
            [[False, True], [True, True], [True, False]],
        )

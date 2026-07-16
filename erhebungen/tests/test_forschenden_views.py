"""HTTP-Tests für die Forschenden-UI der Erhebungen."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from erhebungen.models import Erhebung, Erhebungsvignette
from simulation.models import ModellKonfiguration, Simulationskern
from vignetten.models import Vignette


def _finale_vignette_anlegen(konto: Konto, fach: str) -> Vignette:
    """Legt eine einbindbare finale Vignette an."""

    vignette: Vignette = Vignette.objects.anlegen(konto)
    vignette.fehlermuster_beschreibung = "Zähler und Nenner addieren"
    vignette.lernauftrag = "Addiere die Brüche."
    vignette.arbeitsheft_beschreibung = "Falsche Bruchrechnung"
    vignette.arbeitsheft_text = "1/2 + 1/3 = 2/5"
    vignette.schuelerin_name = "Lea"
    vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.lehrperson_name = "Ada"
    vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.fach = fach
    vignette.thema = "Bruchrechnung"
    vignette.klassenstufe = "6"
    vignette.budget_typ = Vignette.BudgetTyp.SCHRITTE
    vignette.budget_wert = 3
    vignette.save()
    vignette.finalisieren()
    return vignette


class ErhebungenForschendenRollenTests(TestCase):
    """Nur Forschende erreichen die Forschenden-Views."""

    def test_konto_ohne_forschendenrolle_erhaelt_auf_alle_forschenden_views_403(
        self,
    ) -> None:
        """Die Erhebungs-UI ist von der öffentlichen Teilnahme getrennt geschützt."""
        konto: Konto = get_user_model().objects.create_user(username="grace")
        erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche", eigentuemerin=konto
        )
        self.client.force_login(konto)

        for url in (
            reverse("erhebungen:liste"),
            reverse("erhebungen:anlegen"),
            reverse("erhebungen:detail", args=[erhebung.pk]),
            reverse("erhebungen:loeschen", args=[erhebung.pk]),
        ):
            response: HttpResponse = self.client.post(url)
            self.assertEqual(response.status_code, 403)


class ErhebungenAnlegenUndListeTests(TestCase):
    """Forschende verwalten ihre eigenen Entwürfe über die Liste."""

    def test_anlegen_erstellt_eigenen_entwurf_und_liste_versteckt_fremde(self) -> None:
        """Die Liste ist der sichtbare Einstieg für eigene Erhebungen."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        Erhebung.objects.create(name="Fremde Erhebung", eigentuemerin=grace)
        self.client.force_login(ada)

        angelegt: HttpResponse = self.client.post(
            reverse("erhebungen:anlegen"), {"name": "Brüche erforschen"}
        )

        erhebung: Erhebung = Erhebung.objects.get(eigentuemerin=ada)
        self.assertRedirects(
            angelegt, reverse("erhebungen:detail", args=[erhebung.pk])
        )
        self.assertEqual(erhebung.status, Erhebung.Status.ENTWURF)
        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))
        self.assertContains(liste, "Brüche erforschen")
        self.assertNotContains(liste, "Fremde Erhebung")
        self.assertContains(liste, reverse("erhebungen:anlegen"))
        self.assertContains(liste, reverse("erhebungen:loeschen", args=[erhebung.pk]))
        self.assertContains(liste, 'aria-current="page"')


class ErhebungenSichtbarkeitUndLoeschenTests(TestCase):
    """Die Detail- und Lösch-URLs folgen der Eigentümersicht."""

    def setUp(self) -> None:
        """Legt eine Forschende mit einem Entwurf an."""
        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.entwurf: Erhebung = Erhebung.objects.create(
            name="Eigener Entwurf", eigentuemerin=self.ada
        )
        self.client.force_login(self.ada)

    def test_fremde_erhebung_ist_nicht_erreichbar(self) -> None:
        """Andere Eigentümerinnen erhalten keine Information über eine Erhebung."""
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde_erhebung: Erhebung = Erhebung.objects.create(
            name="Fremde Erhebung", eigentuemerin=grace
        )

        response: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[fremde_erhebung.pk])
        )
        loeschen: HttpResponse = self.client.post(
            reverse("erhebungen:loeschen", args=[fremde_erhebung.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(loeschen.status_code, 404)

    def test_loescht_nur_eigenen_entwurf_und_bietet_finalen_keinen_loeschknopf(self) -> None:
        """Die physische Löschaktion bleibt auf Entwürfe beschränkt."""
        geloescht: HttpResponse = self.client.post(
            reverse("erhebungen:loeschen", args=[self.entwurf.pk])
        )
        finale: Erhebung = Erhebung.objects.create(
            name="Finale Erhebung", eigentuemerin=self.ada
        )
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        finale.finalisieren()
        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))

        self.assertRedirects(geloescht, reverse("erhebungen:liste"))
        self.assertFalse(Erhebung.objects.filter(pk=self.entwurf.pk).exists())
        self.assertNotContains(
            liste, reverse("erhebungen:loeschen", args=[finale.pk])
        )


class ErhebungenEntwurfKonfigurierenTests(TestCase):
    """Forschende stellen den Vignettenablauf ihres Entwurfs zusammen."""

    def setUp(self) -> None:
        """Legt die kleinste Umgebung einer Forschenden mit Entwurf an."""

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche", eigentuemerin=self.ada
        )
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        self.eigene_finale: Vignette = _finale_vignette_anlegen(self.ada, "Mathematik")
        self.client.force_login(self.ada)

    def test_bietet_nur_eigene_finale_vignetten_zur_aufnahme_an(self) -> None:
        """Die Detailseite bietet nur noch nicht aufgenommene eigene Finale an."""

        grace: Konto = get_user_model().objects.create_user(username="grace")
        _finale_vignette_anlegen(grace, "Physik")
        entwurf: Vignette = Vignette.objects.anlegen(self.ada)

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(detail, "Mathematik")
        self.assertNotContains(detail, "Physik")
        self.assertNotContains(
            detail,
            reverse(
                "erhebungen:vignette_hinzufuegen",
                args=[self.erhebung.pk, entwurf.pk],
            ),
        )

    def test_lehnt_fremde_und_unfertige_vignetten_ab(self) -> None:
        """Nur eigene finale Vignetten lassen sich in den Entwurf aufnehmen."""

        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde_finale: Vignette = _finale_vignette_anlegen(grace, "Physik")
        entwurf: Vignette = Vignette.objects.anlegen(self.ada)

        fremde_aufnehmen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen",
                args=[self.erhebung.pk, fremde_finale.pk],
            )
        )
        entwurf_aufnehmen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen",
                args=[self.erhebung.pk, entwurf.pk],
            )
        )
        self.assertEqual(fremde_aufnehmen.status_code, 404)
        self.assertEqual(entwurf_aufnehmen.status_code, 404)

    def test_nimmt_finale_vignette_auf_und_entfernt_sie_wieder(self) -> None:
        """Die Aufnahme erscheint an erster Position und lässt sich zurücknehmen."""

        aufnehmen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )

        self.assertRedirects(aufnehmen, reverse("erhebungen:detail", args=[self.erhebung.pk]))
        aufgenommen: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(aufgenommen, "Position 1")

        entfernt: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_entfernen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )

        self.assertRedirects(entfernt, reverse("erhebungen:detail", args=[self.erhebung.pk]))
        self.assertNotContains(
            self.client.get(reverse("erhebungen:detail", args=[self.erhebung.pk])),
            reverse(
                "erhebungen:vignette_entfernen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            ),
        )

    def test_speichert_texte_und_feste_reihenfolge(self) -> None:
        """Ein Entwurf zeigt die gespeicherten Texte und Reihenfolge wieder an."""

        zweite: Vignette = _finale_vignette_anlegen(self.ada, "Chemie")
        erste_zugehoerigkeit: Erhebungsvignette = Erhebungsvignette.objects.create(
            erhebung=self.erhebung, vignette=self.eigene_finale, position=1
        )
        zweite_zugehoerigkeit: Erhebungsvignette = Erhebungsvignette.objects.create(
            erhebung=self.erhebung, vignette=zweite, position=2
        )

        speichern: HttpResponse = self.client.post(
            reverse("erhebungen:konfiguration_speichern", args=[self.erhebung.pk]),
            {
                "randomisierung": Erhebung.Randomisierung.FEST,
                "instruktionstext": "Bitte diagnostizieren Sie.",
                "einwilligungstext": "Ich willige ein.",
                "abschlusstext": "Vielen Dank.",
                "vignetten": [str(zweite_zugehoerigkeit.pk), str(erste_zugehoerigkeit.pk)],
            },
        )

        self.assertRedirects(speichern, reverse("erhebungen:detail", args=[self.erhebung.pk]))
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(detail, "Bitte diagnostizieren Sie.")
        self.assertContains(detail, "Ich willige ein.")
        self.assertContains(detail, "Vielen Dank.")
        self.assertContains(
            detail,
            f'<option value="{zweite_zugehoerigkeit.pk}" selected>',
        )
        self.assertContains(
            detail,
            f'<option value="{erste_zugehoerigkeit.pk}" selected>',
        )

    def test_zufaellige_reihenfolge_blendet_positionswahl_aus(self) -> None:
        """Eine zufällige Reihenfolge hat keine bearbeitbare Positionswahl."""

        Erhebungsvignette.objects.create(
            erhebung=self.erhebung, vignette=self.eigene_finale, position=1
        )

        zufaellig: HttpResponse = self.client.post(
            reverse("erhebungen:konfiguration_speichern", args=[self.erhebung.pk]),
            {"randomisierung": Erhebung.Randomisierung.ZUFAELLIG},
        )

        self.assertRedirects(zufaellig, reverse("erhebungen:detail", args=[self.erhebung.pk]))
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(detail, 'value="zufällig" selected')
        self.assertNotContains(detail, "Reihenfolge der aufgenommenen Vignetten:")

    def test_schreibaktionen_schuetzen_fremde_und_finale_erhebungen(self) -> None:
        """Nur der eigene Entwurf bleibt über jede Konfigurations-URL veränderbar."""

        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.erhebung.finalisieren()
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde_erhebung: Erhebung = Erhebung.objects.create(
            name="Fremd", eigentuemerin=grace
        )

        final_entfernen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_entfernen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )
        final_aufnehmen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )
        final_speichern: HttpResponse = self.client.post(
            reverse("erhebungen:konfiguration_speichern", args=[self.erhebung.pk]),
            {"instruktionstext": "Nicht speichern"},
        )
        fremd: HttpResponse = self.client.post(
            reverse("erhebungen:konfiguration_speichern", args=[fremde_erhebung.pk]),
            {"instruktionstext": "Nicht speichern"},
        )

        self.assertEqual(final_entfernen.status_code, 302)
        self.assertEqual(final_aufnehmen.status_code, 302)
        self.assertEqual(final_speichern.status_code, 302)
        self.assertEqual(fremd.status_code, 404)
        self.assertFalse(
            Erhebungsvignette.objects.filter(erhebung=self.erhebung).exists()
        )
        self.erhebung.refresh_from_db()
        self.assertEqual(self.erhebung.instruktionstext, "")
        self.erhebung.archivieren()

        archiv_speichern: HttpResponse = self.client.post(
            reverse("erhebungen:konfiguration_speichern", args=[self.erhebung.pk]),
            {"instruktionstext": "Noch immer nicht speichern"},
        )
        archiv_aufnehmen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )

        self.assertEqual(archiv_speichern.status_code, 302)
        self.assertEqual(archiv_aufnehmen.status_code, 302)
        self.erhebung.refresh_from_db()
        self.assertEqual(self.erhebung.instruktionstext, "")

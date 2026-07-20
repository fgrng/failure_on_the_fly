"""HTTP-Tests für die Forschenden-UI der Erhebungen."""

import csv
import re
from datetime import datetime, timedelta
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from konten.models import Konto
from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsitem,
    Erhebungsvignette,
    Stichprobe,
    Vignettenposition,
    Vignettenziehung,
)
from fragebogen_items.models import FragebogenItem
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Diagnose, Fehlversuch, Gespraechsschritt, Sitzung, Teilnahme
from training.models import Training, Trainingsbindung
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


def _finales_item_anlegen(konto: Konto, wortlaut: str) -> FragebogenItem:
    """Legt eine einbindbare finale Item-Fassung an."""

    item: FragebogenItem = FragebogenItem.objects.anlegen(konto, wortlaut=wortlaut)
    item.finalisieren()
    return item


class ErhebungenForschendenRollenTests(TestCase):
    """Nur Forschende erreichen die Forschenden-Views."""

    def test_konto_ohne_forschendenrolle_erhaelt_auf_alle_forschenden_views_403(
        self,
    ) -> None:
        """Die Erhebungs-UI ist von der öffentlichen Teilnahme getrennt geschützt."""
        konto: Konto = get_user_model().objects.create_user(username="grace")
        erhebung: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=konto)
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
        self.assertRedirects(angelegt, reverse("erhebungen:detail", args=[erhebung.pk]))
        self.assertEqual(erhebung.status, Erhebung.Status.ENTWURF)
        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))
        self.assertContains(liste, "Brüche erforschen")
        self.assertNotContains(liste, "Fremde Erhebung")
        self.assertContains(liste, reverse("erhebungen:anlegen"))
        self.assertContains(liste, reverse("erhebungen:loeschen", args=[erhebung.pk]))
        self.assertContains(liste, 'aria-current="page"')

    def test_liste_traegt_bereichsfarbe_und_bekannte_badge_klassen(self) -> None:
        """Jeder Status bildet auf eine im Stylesheet definierte Badge-Klasse ab."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(sprachmodell="gpt-forschung")
        )
        Erhebung.objects.create(name="Noch Entwurf", eigentuemerin=ada)
        finale: Erhebung = Erhebung.objects.create(
            name="Schon final", eigentuemerin=ada
        )
        finale.finalisieren()
        abgelegte: Erhebung = Erhebung.objects.create(
            name="Längst abgelegt", eigentuemerin=ada
        )
        abgelegte.finalisieren()
        abgelegte.archivieren()
        self.client.force_login(ada)

        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))

        self.assertContains(liste, "area--research")
        self.assertContains(liste, "badge--draft")
        self.assertContains(liste, "badge--final")
        self.assertContains(liste, "badge--archived")
        self.assertNotContains(liste, "badge--entwurf")
        self.assertNotContains(liste, "badge--archiviert")


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

    def test_loescht_nur_eigenen_entwurf_und_bietet_finalen_keinen_loeschknopf(
        self,
    ) -> None:
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
        self.assertNotContains(liste, reverse("erhebungen:loeschen", args=[finale.pk]))


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

        self.assertRedirects(
            aufnehmen, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
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

        self.assertRedirects(
            entfernt, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertNotContains(
            self.client.get(reverse("erhebungen:detail", args=[self.erhebung.pk])),
            reverse(
                "erhebungen:vignette_entfernen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            ),
        )

    def test_item_bleibt_am_anderen_andockpunkt_verfuegbar(self) -> None:
        """Ein finales eigenes Item lässt sich an beide Andockpunkte aufnehmen."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )

        aufnehmen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )

        self.assertEqual(aufnehmen.status_code, 200)
        self.assertEqual(
            [
                zeile["pk"]
                for zeile in aufnehmen.context["nach_sitzung_aufgenommene_daten"]
            ],
            [item.pk],
        )
        self.assertEqual(aufnehmen.context["nach_sitzung_verfuegbare_daten"], [])
        self.assertEqual(
            [zeile["pk"] for zeile in aufnehmen.context["am_ende_verfuegbare_daten"]],
            [item.pk],
        )

        andere_bindung: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[self.erhebung.pk, item.pk, Erhebungsitem.Andockpunkt.AM_ENDE],
            )
        )
        self.assertEqual(andere_bindung.status_code, 200)
        self.assertEqual(
            Erhebungsitem.objects.filter(erhebung=self.erhebung).count(), 2
        )

    def test_bibliothek_kennzeichnet_item_am_ende_nach_jeder_sitzung(self) -> None:
        """Die Bibliothek nach jeder Sitzung markiert Items vom Ende."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )
        self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[self.erhebung.pk, item.pk, Erhebungsitem.Andockpunkt.AM_ENDE],
            )
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(detail, "schon am Ende")
        self.assertContains(detail, "badge--research")
        self.assertContains(
            detail,
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            ),
        )

    def test_badge_verschwindet_nach_entfernen_am_anderen_andockpunkt(self) -> None:
        """Das Badge verschwindet, wenn die Bindung am anderen Andockpunkt endet."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )
        self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[self.erhebung.pk, item.pk, Erhebungsitem.Andockpunkt.AM_ENDE],
            )
        )
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        entfernen_url_treffer: re.Match[str] | None = re.search(
            r'(?P<url>/[^"]+/items/\d+/entfernen/)', detail.content.decode()
        )
        if entfernen_url_treffer is None:
            self.fail("Die aufgenommene Item-Zeile enthält keine Entfernen-URL.")

        self.client.post(entfernen_url_treffer.group("url"))

        self.assertNotContains(
            self.client.get(reverse("erhebungen:detail", args=[self.erhebung.pk])),
            "schon am Ende",
        )

    def test_bibliothek_kennzeichnet_item_nach_jeder_sitzung_am_ende(self) -> None:
        """Die Bibliothek am Ende markiert Items nach jeder Sitzung."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )
        self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )
        gegenrichtung: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(gegenrichtung, "schon nach jeder Sitzung")
        self.assertContains(
            gegenrichtung,
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[self.erhebung.pk, item.pk, Erhebungsitem.Andockpunkt.AM_ENDE],
            ),
        )

    def test_doppelte_itemaufnahme_am_selben_andockpunkt_wird_abgelehnt(self) -> None:
        """Eine Item-Fassung kann je Andockpunkt nur einmal vorkommen."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )
        self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )

        doppelte_aufnahme: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )

        self.assertEqual(doppelte_aufnahme.status_code, 409)

    def test_verschiebt_item_innerhalb_seines_andockpunkts_ohne_seitenwechsel(
        self,
    ) -> None:
        """Hoch verschiebt die Zuordnung und lässt den anderen Andockpunkt unverändert."""

        erstes_item: FragebogenItem = _finales_item_anlegen(self.ada, "Erstes Item")
        zweites_item: FragebogenItem = _finales_item_anlegen(self.ada, "Zweites Item")
        drittes_item: FragebogenItem = _finales_item_anlegen(self.ada, "Am Ende")
        for item, andockpunkt in (
            (erstes_item, Erhebungsitem.Andockpunkt.NACH_SITZUNG),
            (zweites_item, Erhebungsitem.Andockpunkt.NACH_SITZUNG),
            (drittes_item, Erhebungsitem.Andockpunkt.AM_ENDE),
        ):
            self.client.post(
                reverse(
                    "erhebungen:item_hinzufuegen",
                    args=[self.erhebung.pk, item.pk, andockpunkt],
                )
            )
        zweite_zuordnung: Erhebungsitem = Erhebungsitem.objects.get(
            erhebung=self.erhebung, item=zweites_item
        )

        verschieben: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hoch",
                args=[self.erhebung.pk, zweite_zuordnung.pk],
            )
        )

        self.assertEqual(verschieben.status_code, 200)
        self.assertEqual(
            [
                zeile["pk"]
                for zeile in verschieben.context["nach_sitzung_aufgenommene_daten"]
            ],
            [zweites_item.pk, erstes_item.pk],
        )
        self.assertEqual(
            [
                zeile["pk"]
                for zeile in verschieben.context["am_ende_aufgenommene_daten"]
            ],
            [drittes_item.pk],
        )
        self.assertEqual(
            [
                aktion["beschriftung"]
                for aktion in verschieben.context["nach_sitzung_aufgenommene_daten"][0][
                    "aktionen"
                ]
            ],
            ["Runter", "Entfernen"],
        )
        self.assertEqual(
            [
                aktion["beschriftung"]
                for aktion in verschieben.context["nach_sitzung_aufgenommene_daten"][1][
                    "aktionen"
                ]
            ],
            ["Hoch", "Entfernen"],
        )

    def test_entfernen_schliesst_die_itemreihenfolge_lueckenlos(self) -> None:
        """Das nächste Item ergänzt die nach dem Entfernen geschlossene Reihenfolge."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )
        self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )

        erste_bindung: Erhebungsitem = Erhebungsitem.objects.get(
            erhebung=self.erhebung,
            item=item,
            andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        )
        zweites_item: FragebogenItem = _finales_item_anlegen(self.ada, "Was fiel auf?")
        drittes_item: FragebogenItem = _finales_item_anlegen(self.ada, "Was bleibt?")
        self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    zweites_item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )
        self.client.post(
            reverse(
                "erhebungen:item_entfernen",
                args=[self.erhebung.pk, erste_bindung.pk],
            )
        )
        anhaengen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    drittes_item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )
        self.assertEqual(anhaengen.status_code, 200)
        self.assertEqual(
            Erhebungsitem.objects.get(
                erhebung=self.erhebung,
                item=drittes_item,
                andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
            ).position,
            2,
        )

    def test_itemverwaltung_ist_ausserhalb_des_entwurfs_gesperrt(self) -> None:
        """Finale Erhebungen verweigern die Änderung ihrer Item-Zuordnungen."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(sprachmodell="fake")
        )
        self.erhebung.finalisieren()
        gesperrt: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[
                    self.erhebung.pk,
                    item.pk,
                    Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                ],
            )
        )
        self.assertEqual(gesperrt.status_code, 403)

    def test_itemreihenfolge_ist_ausserhalb_des_entwurfs_gesperrt(self) -> None:
        """Auch Hoch und Runter ändern eine finale Erhebung nicht."""

        erstes_item: FragebogenItem = _finales_item_anlegen(self.ada, "Erstes Item")
        zweites_item: FragebogenItem = _finales_item_anlegen(self.ada, "Zweites Item")
        for item in (erstes_item, zweites_item):
            self.client.post(
                reverse(
                    "erhebungen:item_hinzufuegen",
                    args=[
                        self.erhebung.pk,
                        item.pk,
                        Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                    ],
                )
            )
        zweite_zuordnung: Erhebungsitem = Erhebungsitem.objects.get(
            erhebung=self.erhebung, item=zweites_item
        )
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(sprachmodell="fake")
        )
        self.erhebung.finalisieren()

        gesperrt: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hoch",
                args=[self.erhebung.pk, zweite_zuordnung.pk],
            )
        )

        self.assertEqual(gesperrt.status_code, 403)
        zweite_zuordnung.refresh_from_db()
        self.assertEqual(zweite_zuordnung.position, 2)

    def test_itemverwaltung_ist_nach_dem_zurueckziehen_wieder_offen(self) -> None:
        """Zurückgezogene Erhebungen erlauben wieder Item-Zuordnungen."""

        item: FragebogenItem = _finales_item_anlegen(
            self.ada, "Wie sicher fühlten Sie sich?"
        )
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(sprachmodell="fake")
        )
        self.erhebung.finalisieren()
        self.erhebung.zurueckziehen()
        wieder_offen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[self.erhebung.pk, item.pk, Erhebungsitem.Andockpunkt.AM_ENDE],
            )
        )
        self.assertEqual(wieder_offen.status_code, 200)

    def test_stellt_zuordnungszeilen_mit_ihren_aktions_urls_bereit(self) -> None:
        """Beide Spalten tragen dieselbe Zeilenform mit passender Aktions-URL."""

        verfuegbar: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(verfuegbar.context["aufgenommene_daten"], [])
        self.assertEqual(
            verfuegbar.context["verfuegbare_daten"],
            [
                {
                    "pk": self.eigene_finale.pk,
                    "label": "Mathematik",
                    "fach": "Mathematik",
                    "thema": self.eigene_finale.thema,
                    "aktion_url": reverse(
                        "erhebungen:vignette_hinzufuegen",
                        args=[self.erhebung.pk, self.eigene_finale.pk],
                    ),
                }
            ],
        )

        self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )

        aufgenommen: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(aufgenommen.context["verfuegbare_daten"], [])
        self.assertEqual(
            [
                zeile["aktion_url"]
                for zeile in aufgenommen.context["aufgenommene_daten"]
            ],
            [
                reverse(
                    "erhebungen:vignette_entfernen",
                    args=[self.erhebung.pk, self.eigene_finale.pk],
                )
            ],
        )

    def test_detailseite_rendert_zuordnungsspalten_ueber_include(self) -> None:
        """Bibliothek und Aufnahme verwenden denselben Zuordnungsspalten-Baustein."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertTemplateUsed(detail, "erhebungen/includes/zuordnungsspalte.html")

    def test_haelt_fremde_und_unfertige_fassungen_aus_den_zeilen_heraus(self) -> None:
        """Die anbietende Spalte zeigt weder fremde noch nicht-finale Fassungen."""

        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde_finale: Vignette = _finale_vignette_anlegen(grace, "Physik")
        eigener_entwurf: Vignette = Vignette.objects.anlegen(self.ada)

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        angebotene_ids: list[int] = [
            zeile["pk"] for zeile in detail.context["verfuegbare_daten"]
        ]
        self.assertEqual(angebotene_ids, [self.eigene_finale.pk])
        self.assertNotIn(fremde_finale.pk, angebotene_ids)
        self.assertNotIn(eigener_entwurf.pk, angebotene_ids)

    def test_detailseite_traegt_bereichsfarbe_und_bekannte_badge_klasse(self) -> None:
        """Die Detailseite färbt den Forschungsbereich und nutzt echte Badge-Klassen."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(detail, "area--research")
        self.assertContains(detail, "badge--draft")
        self.assertNotContains(detail, "badge--entwurf")

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
                "vignetten": [
                    str(zweite_zugehoerigkeit.pk),
                    str(erste_zugehoerigkeit.pk),
                ],
            },
        )

        self.assertRedirects(
            speichern, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
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

        self.assertRedirects(
            zufaellig, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
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


class ErhebungenFinalisierenTests(TestCase):
    """Forschende finalisieren Entwürfe über die Detailseite."""

    def setUp(self) -> None:
        # Richtet den gemeinsamen Entwurf einer eingeloggten Forschenden ein.

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche", eigentuemerin=self.ada
        )
        self.konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="gpt-forschung"
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.client.force_login(self.ada)

    def test_finalisieren_sperrt_design_und_zeigt_gepinnte_konfiguration(self) -> None:
        """Die Detailseite zeigt den finalen, gepinnten Zustand statt Editoren."""

        response: HttpResponse = self.client.post(
            reverse("erhebungen:finalisieren", args=[self.erhebung.pk]), follow=True
        )

        self.assertContains(response, "Final")
        self.assertContains(response, "gpt-forschung")
        self.assertNotContains(response, "Konfiguration speichern")
        self.assertNotContains(response, "Finale Vignetten aufnehmen")
        self.assertNotContains(response, ">Entfernen<")

    def test_nicht_archivierte_stichprobe_versteckt_zurueckziehen(self) -> None:
        """Eine laufende Stichprobe sperrt den Rückweg schon in der UI."""

        self.erhebung.finalisieren()
        Stichprobe.objects.create(
            erhebung=self.erhebung, beginn=timezone.now(), ende=timezone.now()
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertNotContains(detail, "Zurückziehen")

    def test_zurueckziehen_macht_die_erhebung_wieder_bearbeitbar(self) -> None:
        """Eine datenfreie finale Erhebung kehrt über die Aktion zum Entwurf zurück."""

        self.erhebung.finalisieren()

        response: HttpResponse = self.client.post(
            reverse("erhebungen:zurueckziehen", args=[self.erhebung.pk]), follow=True
        )

        self.assertContains(response, "Konfiguration speichern")

    def test_datentragende_archivierte_stichprobe_versteckt_zurueckziehen(self) -> None:
        """Auch eine archivierte Stichprobe mit Datenspur sperrt den Rückweg."""

        self.erhebung.finalisieren()
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung, beginn=timezone.now(), ende=timezone.now()
        )
        stichprobe.archivieren()
        Erhebungsbindung.objects.create(
            stichprobe=stichprobe,
            teilnahme=Teilnahme.objects.create(),
            token="2345-6789",
        )
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        versuch: HttpResponse = self.client.post(
            reverse("erhebungen:zurueckziehen", args=[self.erhebung.pk]), follow=True
        )

        self.assertNotContains(detail, "Zurückziehen")
        self.assertContains(versuch, "können nicht zurückgezogen werden")


class StichprobenAnlegenTests(TestCase):
    """Forschende legen Stichproben unter finalen Erhebungen an."""

    def setUp(self) -> None:
        """Richtet eine finale Erhebung einer eingeloggten Forschenden ein."""

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche", eigentuemerin=self.ada
        )
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="gpt-forschung"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.erhebung.finalisieren()
        self.client.force_login(self.ada)

    def test_legt_stichprobe_mit_zeitraum_und_teilnahme_link_an(self) -> None:
        """Die Detailseite erzeugt den öffentlichen Link für den eingegebenen Zeitraum."""

        anlegen: HttpResponse = self.client.post(
            reverse("erhebungen:stichprobe_anlegen", args=[self.erhebung.pk]),
            {"beginn": "2026-08-01T09:00", "ende": "2026-08-31T17:00"},
        )

        stichprobe: Stichprobe = Stichprobe.objects.get(erhebung=self.erhebung)
        self.assertRedirects(
            anlegen, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(
            stichprobe.beginn, timezone.make_aware(datetime(2026, 8, 1, 9))
        )
        self.assertEqual(
            stichprobe.ende, timezone.make_aware(datetime(2026, 8, 31, 17))
        )
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(
            detail,
            detail.wsgi_request.build_absolute_uri(
                reverse("erhebungen:teilnehmen", args=[stichprobe.teilnahme_link])
            ),
        )

    def test_zeigt_phase_und_anzahl_teilnahmen_je_stichprobe(self) -> None:
        """Die Detailseite ordnet jede Stichprobe zeitlich und nach Datenvolumen ein."""

        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        Erhebungsbindung.objects.create(
            stichprobe=stichprobe,
            teilnahme=Teilnahme.objects.create(),
            token="2345-6789",
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(detail, '<th scope="col">Phase</th>')
        self.assertContains(detail, "<td>laufend</td>")
        self.assertContains(detail, '<th scope="col">Teilnahmen</th>')
        self.assertContains(detail, "<td>1</td>")

    def test_laesst_stichproben_nur_auf_eigenen_finalen_erhebungen_an(self) -> None:
        """Entwürfe und fremde Erhebungen erhalten keine anlegbare Stichprobe."""

        entwurf: Erhebung = Erhebung.objects.create(
            name="Entwurf", eigentuemerin=self.ada
        )
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde: Erhebung = Erhebung.objects.create(name="Fremd", eigentuemerin=grace)
        zeitraum: dict[str, str] = {
            "beginn": "2026-08-01T09:00",
            "ende": "2026-08-31T17:00",
        }

        entwurf_antwort: HttpResponse = self.client.post(
            reverse("erhebungen:stichprobe_anlegen", args=[entwurf.pk]), zeitraum
        )
        fremd_antwort: HttpResponse = self.client.post(
            reverse("erhebungen:stichprobe_anlegen", args=[fremde.pk]), zeitraum
        )

        self.assertRedirects(
            entwurf_antwort, reverse("erhebungen:detail", args=[entwurf.pk])
        )
        self.assertEqual(fremd_antwort.status_code, 404)
        self.assertFalse(Stichprobe.objects.filter(erhebung=entwurf).exists())

    def test_lehnt_zeitraum_mit_ende_vor_beginn_ab(self) -> None:
        """Der Zeitraum einer Stichprobe endet nicht vor seinem Beginn."""

        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:stichprobe_anlegen", args=[self.erhebung.pk]),
            {"beginn": "2026-08-31T17:00", "ende": "2026-08-01T09:00"},
        )

        self.assertEqual(antwort.status_code, 400)
        self.assertFalse(Stichprobe.objects.filter(erhebung=self.erhebung).exists())


class ErhebungenArchivierenTests(TestCase):
    """Forschende archivieren über die Detailseite nur erlaubte Objekte."""

    def setUp(self) -> None:
        """Richtet eine finale Erhebung einer eingeloggten Forschenden ein."""

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche", eigentuemerin=self.ada
        )
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="gpt-forschung"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.erhebung.finalisieren()
        self.client.force_login(self.ada)

    def test_archiviert_datenfreie_stichprobe_ueber_die_detailseite(self) -> None:
        """Eine datenfreie Stichprobe zeigt die Aktion und wird darüber archiviert."""

        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=2),
            ende=timezone.now() - timedelta(days=1),
        )
        archivieren_url: str = reverse(
            "erhebungen:stichprobe_archivieren", args=[self.erhebung.pk, stichprobe.pk]
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        archivieren: HttpResponse = self.client.post(archivieren_url)

        self.assertContains(detail, archivieren_url)
        self.assertRedirects(
            archivieren, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        stichprobe.refresh_from_db()
        self.assertTrue(stichprobe.archiviert)

    def test_versteckt_datentragende_stichprobe_und_zeigt_guard_fehler(self) -> None:
        """Datentragende Stichproben bieten keinen Übergang und weisen ihn ab."""

        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=2),
            ende=timezone.now() - timedelta(days=1),
        )
        Erhebungsbindung.objects.create(
            stichprobe=stichprobe,
            teilnahme=Teilnahme.objects.create(),
            token="2345-6789",
        )
        archivieren_url: str = reverse(
            "erhebungen:stichprobe_archivieren", args=[self.erhebung.pk, stichprobe.pk]
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        archivieren: HttpResponse = self.client.post(archivieren_url, follow=True)

        self.assertNotContains(detail, archivieren_url)
        self.assertContains(
            archivieren, "Datentragende Stichproben können nicht archiviert werden."
        )
        stichprobe.refresh_from_db()
        self.assertFalse(stichprobe.archiviert)

    def test_archiviert_und_entarchiviert_finale_erhebung(self) -> None:
        """Eine finale Erhebung wechselt über beide Detailseiten-Aktionen zurück."""

        archivieren_url: str = reverse(
            "erhebungen:archivieren", args=[self.erhebung.pk]
        )
        entarchivieren_url: str = reverse(
            "erhebungen:entarchivieren", args=[self.erhebung.pk]
        )

        final_detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        archivieren: HttpResponse = self.client.post(archivieren_url, follow=True)
        entarchivieren: HttpResponse = self.client.post(entarchivieren_url, follow=True)

        self.assertContains(final_detail, archivieren_url)
        self.assertContains(archivieren, "Archiviert")
        self.assertContains(archivieren, entarchivieren_url)
        self.assertContains(entarchivieren, "Final")
        self.erhebung.refresh_from_db()
        self.assertEqual(self.erhebung.status, Erhebung.Status.FINAL)

    def test_versteckt_erhebung_archivieren_bei_laufender_stichprobe(self) -> None:
        """Eine laufende Stichprobe sperrt Archivieren in UI und Domänen-Guard."""

        Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        archivieren_url: str = reverse(
            "erhebungen:archivieren", args=[self.erhebung.pk]
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        archivieren: HttpResponse = self.client.post(archivieren_url, follow=True)

        self.assertNotContains(detail, archivieren_url)
        self.assertContains(
            archivieren,
            "Erhebungen mit laufenden Stichproben können nicht archiviert werden.",
        )
        self.erhebung.refresh_from_db()
        self.assertEqual(self.erhebung.status, Erhebung.Status.FINAL)

    def test_versteckt_entarchivieren_bei_laufender_stichprobe(self) -> None:
        """Eine laufende Stichprobe sperrt auch den Rückweg aus dem Archiv."""

        self.erhebung.archivieren()
        Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        entarchivieren_url: str = reverse(
            "erhebungen:entarchivieren", args=[self.erhebung.pk]
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        entarchivieren: HttpResponse = self.client.post(entarchivieren_url, follow=True)

        self.assertNotContains(detail, entarchivieren_url)
        self.assertContains(
            entarchivieren,
            "Erhebungen mit laufenden Stichproben können nicht entarchiviert werden.",
        )
        self.erhebung.refresh_from_db()
        self.assertEqual(self.erhebung.status, Erhebung.Status.ARCHIVIERT)


class ErhebungsExportTests(TestCase):
    """Forschende laden die minimale relationale Datenspur als ZIP herunter."""

    def test_exportiert_erhebung_stichprobe_und_teilnahme_als_csvs(self) -> None:
        """Das ZIP bewahrt Freitext, NULL und Zeitstempel im festgelegten Format."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="gpt-forschung"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.create(
            name="Brüche & Zahlen",
            eigentuemerin=ada,
            instruktionstext="Zeile eins\nZeile zwei",
            einwilligungstext="",
        )
        erhebung.finalisieren()
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=datetime(2026, 7, 1, 8, tzinfo=timezone.UTC),
            ende=datetime(2026, 7, 31, 17, tzinfo=timezone.UTC),
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
            stichprobe=stichprobe,
            teilnahme=Teilnahme.objects.create(),
            token="2345-6789",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        with ZipFile(BytesIO(response.content)) as zip_datei:
            self.assertEqual(
                sorted(zip_datei.namelist()),
                [
                    "diagnosen.csv",
                    "erhebung.csv",
                    "fehlversuche.csv",
                    "gespraechsschritte.csv",
                    "sitzungen.csv",
                    "stichproben.csv",
                    "teilnahmen.csv",
                    "vignettenziehungen.csv",
                ],
            )
            erhebungszeile = next(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("erhebung.csv"), encoding="utf-8")
                )
            )
            stichprobenzeile = next(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("stichproben.csv"), encoding="utf-8")
                )
            )
            teilnahmezeile = next(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("teilnahmen.csv"), encoding="utf-8")
                )
            )

        self.assertEqual(erhebungszeile["instruktionstext"], "Zeile eins\nZeile zwei")
        self.assertEqual(erhebungszeile["einwilligungstext"], "")
        self.assertEqual(
            erhebungszeile["modell_konfiguration_id"], str(konfiguration.pk)
        )
        self.assertEqual(stichprobenzeile["id"], str(stichprobe.pk))
        self.assertEqual(stichprobenzeile["beginn"], "2026-07-01T08:00:00+00:00")
        self.assertEqual(teilnahmezeile["token"], bindung.token)
        self.assertEqual(teilnahmezeile["audioverarbeitung_eingewilligt"], "NA")
        self.assertRegex(
            teilnahmezeile["erstellt_am"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$",
        )

    def test_exportiert_ziehungen_und_alle_erhebungssitzungen(self) -> None:
        """Die Ziehung zeigt den Plan, Sitzungen zeigen jeden tatsächlichen Ausgang."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="gpt-forschung"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=ada)
        erhebung.finalisieren()
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        vignette: Vignette = _finale_vignette_anlegen(ada, "Mathematik")
        bindungen: list[Erhebungsbindung] = [
            Erhebungsbindung.objects.create(
                stichprobe=stichprobe,
                teilnahme=Teilnahme.objects.create(),
                token=f"2345-678{nummer}",
            )
            for nummer in range(1, 6)
        ]
        for bindung in bindungen:
            Vignettenziehung.objects.create(
                erhebungsbindung=bindung, vignette=vignette, position=1
            )
        for bindung, status in zip(bindungen[:4], Sitzung.Status.values, strict=True):
            sitzung: Sitzung = Sitzung.objects.create(
                teilnahme=bindung.teilnahme,
                vignette=vignette,
                simulationskern=kern,
                modell_konfiguration=konfiguration,
                status=status,
            )
            Vignettenposition.objects.create(
                erhebungsbindung=bindung,
                sitzung=sitzung,
                vignette=vignette,
                position=1,
            )
        Sitzung.objects.create(
            teilnahme=Teilnahme.objects.create(),
            vignette=vignette,
            simulationskern=kern,
            modell_konfiguration=konfiguration,
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            ziehungen: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(
                        zip_datei.open("vignettenziehungen.csv"), encoding="utf-8"
                    )
                )
            )
            sitzungen: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("sitzungen.csv"), encoding="utf-8")
                )
            )

        self.assertEqual(
            {
                "ziehungen": {
                    (
                        ziehung["token"],
                        ziehung["vignette_id"],
                        ziehung["position"],
                    )
                    for ziehung in ziehungen
                },
                "sitzungen": {
                    (
                        sitzung["token"],
                        sitzung["vignette_id"],
                        sitzung["position"],
                        sitzung["status"],
                    )
                    for sitzung in sitzungen
                },
            },
            {
                "ziehungen": {
                    (bindung.token, str(vignette.pk), "1") for bindung in bindungen
                },
                "sitzungen": {
                    (bindung.token, str(vignette.pk), "1", status)
                    for bindung, status in zip(
                        bindungen[:4], Sitzung.Status.values, strict=True
                    )
                },
            },
        )

    def test_exportiert_gespraechsschritte_fehlversuche_und_diagnosen(self) -> None:
        """Der Export bewahrt die vollständige Datenspur einschließlich Abbrüchen."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="gpt-forschung"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.create(name="Brüche", eigentuemerin=ada)
        erhebung.finalisieren()
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
            stichprobe=stichprobe,
            teilnahme=Teilnahme.objects.create(),
            token="2345-6789",
        )
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        vignette: Vignette = _finale_vignette_anlegen(ada, "Mathematik")
        sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=bindung.teilnahme,
            vignette=vignette,
            simulationskern=kern,
            modell_konfiguration=konfiguration,
        )
        Vignettenposition.objects.create(
            erhebungsbindung=bindung, sitzung=sitzung, vignette=vignette, position=1
        )
        erfolgreicher_schritt: Gespraechsschritt = Gespraechsschritt.objects.create(
            sitzung=sitzung,
            reihenfolge=1,
            eingabe="Warum?",
            denkspur="Zeile eins\nZeile zwei",
            aeusserung="Antwort eins\nAntwort zwei",
            native_reasoning_spur=None,
        )
        Fehlversuch.objects.create(
            gespraechsschritt=erfolgreicher_schritt,
            grund="Formatbruch",
            rohantwort="nicht parsebar",
        )
        leerer_schritt: Gespraechsschritt = Gespraechsschritt.objects.create(
            sitzung=sitzung,
            reihenfolge=2,
            eingabe="Bitte knapp.",
            denkspur="",
            aeusserung="",
        )
        abbruchschritt: Gespraechsschritt = Gespraechsschritt.objects.answerless_anlegen(
            sitzung=sitzung,
            reihenfolge=3,
            eingabe="Noch einmal?",
            fehlversuche=[Fehlversuch(grund="Anbieterfehler", rohantwort="timeout")],
        )
        Diagnose.objects.create(sitzung=sitzung, text="Bruchfehler")
        training: Training = Training.objects.create(
            name="Nicht exportieren", eigentuemerin=ada
        )
        training.vignetten.add(vignette)
        trainingsteilnahme: Teilnahme = Teilnahme.objects.create()
        Trainingsbindung.objects.create(
            training=training,
            teilnahme=trainingsteilnahme,
            konto=ada,
        )
        trainingssitzung: Sitzung = Sitzung.objects.create(
            teilnahme=trainingsteilnahme,
            vignette=vignette,
            simulationskern=kern,
            modell_konfiguration=konfiguration,
        )
        trainingsschritt: Gespraechsschritt = Gespraechsschritt.objects.create(
            sitzung=trainingssitzung,
            reihenfolge=1,
            eingabe="Nicht exportieren.",
            denkspur="Nicht exportieren.",
            aeusserung="Nicht exportieren.",
        )
        Fehlversuch.objects.create(
            gespraechsschritt=trainingsschritt,
            grund="Nicht exportieren.",
            rohantwort="Nicht exportieren.",
        )
        Diagnose.objects.create(sitzung=trainingssitzung, text="Nicht exportieren.")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            self.assertTrue(
                {
                    "gespraechsschritte.csv",
                    "fehlversuche.csv",
                    "diagnosen.csv",
                }.issubset(zip_datei.namelist())
            )
            schritte: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(
                        zip_datei.open("gespraechsschritte.csv"), encoding="utf-8"
                    )
                )
            )
            fehlversuche: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("fehlversuche.csv"), encoding="utf-8")
                )
            )
            diagnosen: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("diagnosen.csv"), encoding="utf-8")
                )
            )

        self.assertEqual(
            [{name: wert for name, wert in schritt.items() if name != "erstellt_am"} for schritt in schritte],
            [
                {
                    "id": str(erfolgreicher_schritt.pk),
                    "sitzung_id": str(sitzung.pk),
                    "reihenfolge": "1",
                    "eingabe": "Warum?",
                    "denkspur": "Zeile eins\nZeile zwei",
                    "aeusserung": "Antwort eins\nAntwort zwei",
                    "native_reasoning_spur": "NA",
                },
                {
                    "id": str(leerer_schritt.pk),
                    "sitzung_id": str(sitzung.pk),
                    "reihenfolge": "2",
                    "eingabe": "Bitte knapp.",
                    "denkspur": "",
                    "aeusserung": "",
                    "native_reasoning_spur": "NA",
                },
                {
                    "id": str(abbruchschritt.pk),
                    "sitzung_id": str(sitzung.pk),
                    "reihenfolge": "3",
                    "eingabe": "Noch einmal?",
                    "denkspur": "NA",
                    "aeusserung": "NA",
                    "native_reasoning_spur": "NA",
                },
            ],
        )
        for schritt in schritte:
            self.assertRegex(
                schritt["erstellt_am"],
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$",
            )
        self.assertEqual(
            {
                (
                    fehlversuch["gespraechsschritt_id"],
                    fehlversuch["grund"],
                    fehlversuch["rohantwort"],
                )
                for fehlversuch in fehlversuche
            },
            {
                (str(erfolgreicher_schritt.pk), "Formatbruch", "nicht parsebar"),
                (str(abbruchschritt.pk), "Anbieterfehler", "timeout"),
            },
        )
        self.assertEqual(
            [{name: wert for name, wert in diagnose.items() if name != "erstellt_am"} for diagnose in diagnosen],
            [
                {
                    "sitzung_id": str(sitzung.pk),
                    "text": "Bruchfehler",
                }
            ],
        )
        self.assertRegex(
            diagnosen[0]["erstellt_am"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$",
        )

    def test_export_ist_eigentumsgebunden_und_auch_ohne_daten_wohlgeformt(self) -> None:
        """Entwürfe exportieren Kopfzeilen; fremde Erhebungen bleiben verborgen."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Forschende:r"))
        entwurf: Erhebung = Erhebung.objects.create(
            name="Leerer Entwurf", eigentuemerin=ada
        )
        fremde_erhebung: Erhebung = Erhebung.objects.create(
            name="Fremde Erhebung", eigentuemerin=grace
        )
        self.client.force_login(ada)

        detail_ohne_stichprobe: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[entwurf.pk])
        )
        export: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[entwurf.pk])
        )
        fremder_export: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[fremde_erhebung.pk])
        )

        self.assertNotContains(
            detail_ohne_stichprobe, reverse("erhebungen:export", args=[entwurf.pk])
        )
        self.assertEqual(fremder_export.status_code, 404)
        self.assertRegex(
            export["Content-Disposition"],
            r'^attachment; filename="erhebung-\d+-leerer-entwurf-\d{8}T\d{6}Z.zip"$',
        )
        with ZipFile(BytesIO(export.content)) as zip_datei:
            for dateiname in (
                "erhebung.csv",
                "stichproben.csv",
                "teilnahmen.csv",
                "vignettenziehungen.csv",
                "sitzungen.csv",
                "gespraechsschritte.csv",
                "fehlversuche.csv",
                "diagnosen.csv",
            ):
                with TextIOWrapper(
                    zip_datei.open(dateiname), encoding="utf-8"
                ) as csv_datei:
                    self.assertEqual(
                        len(list(csv.reader(csv_datei))),
                        2 if dateiname == "erhebung.csv" else 1,
                    )

    def test_detail_zeigt_export_mit_stichprobe_auch_nach_archivierung(self) -> None:
        """Der Daten-Download folgt dem Datenbestand statt dem Erhebungsstatus."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="gpt-forschung"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.create(name="Archiv", eigentuemerin=ada)
        erhebung.finalisieren()
        Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(days=2),
            ende=timezone.now() - timedelta(days=1),
        )
        erhebung.archivieren()
        self.client.force_login(ada)

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[erhebung.pk])
        )
        export: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertContains(detail, reverse("erhebungen:export", args=[erhebung.pk]))
        self.assertEqual(export.status_code, 200)

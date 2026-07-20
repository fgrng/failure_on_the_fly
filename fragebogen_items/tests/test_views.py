"""HTTP-Tests für den Fragebogen-Item-Editor."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from fragebogen_items.models import FragebogenItem
from konten.models import Konto


def _forschende(username: str) -> Konto:
    """Legt ein Konto mit Zugriff auf den Fragebogen-Item-Editor an."""
    konto: Konto = get_user_model().objects.create_user(username=username)
    konto.groups.add(Group.objects.get(name="Forschende:r"))
    return konto


class FragebogenItemAnlegenViewTests(TestCase):
    """Das Anlegeformular ist die HTTP-Naht zum Item-Manager."""

    def test_legt_likert_entwurf_an_und_listet_ihn(self) -> None:
        """Eine Forschende legt ein Likert-Item an und findet es in ihrer Bibliothek."""
        ada: Konto = _forschende("ada")
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("fragebogen_items:anlegen"),
            {
                "typ": FragebogenItem.Typ.LIKERT,
                "wortlaut": "Die Aufgaben waren verständlich.",
            },
        )

        item: FragebogenItem = FragebogenItem.objects.get()
        self.assertRedirects(
            response, reverse("fragebogen_items:detail", args=[item.pk])
        )
        self.assertEqual(item.zustand, FragebogenItem.Zustand.ENTWURF)
        self.assertEqual(list(item.historie.eigentuemerinnen.all()), [ada])

        liste: HttpResponse = self.client.get(reverse("fragebogen_items:liste"))

        self.assertContains(liste, "Die Aufgaben waren verständlich.")
        self.assertContains(liste, "Entwurf")

    def test_legt_freitext_entwurf_an(self) -> None:
        """Eine Forschende kann auch ein Freitext-Item über HTTP anlegen."""
        ada: Konto = _forschende("ada")
        self.client.force_login(ada)

        response: HttpResponse = self.client.post(
            reverse("fragebogen_items:anlegen"),
            {"typ": FragebogenItem.Typ.FREITEXT, "wortlaut": "Was fiel Ihnen auf?"},
        )

        item: FragebogenItem = FragebogenItem.objects.get()
        self.assertRedirects(
            response, reverse("fragebogen_items:detail", args=[item.pk])
        )
        self.assertEqual(item.typ, FragebogenItem.Typ.FREITEXT)


class FragebogenItemFinalisierenViewTests(TestCase):
    """Entwürfe werden im Editor zu einbindbaren finalen Fassungen."""

    ada: Konto
    item: FragebogenItem

    def setUp(self) -> None:
        """Legt einen sichtbaren Entwurf für jeden Test an."""
        self.ada = _forschende("ada")
        self.item = FragebogenItem.objects.anlegen(
            self.ada,
            wortlaut="Die Aufgaben waren verständlich.",
        )
        self.client.force_login(self.ada)

    def test_zeigt_finalisieren_bei_entwurf(self) -> None:
        """Der Editor bietet die Aktion nur für einen Entwurf an."""
        response: HttpResponse = self.client.get(
            reverse("fragebogen_items:detail", args=[self.item.pk])
        )

        self.assertContains(response, "Finalisieren")

    def test_finalisieren_leitet_zur_detailansicht_weiter(self) -> None:
        """Die Aktion führt nach ihrer Ausführung zur finalisierten Fassung."""
        response: HttpResponse = self.client.post(
            reverse("fragebogen_items:finalisieren", args=[self.item.pk])
        )

        self.assertRedirects(
            response,
            reverse("fragebogen_items:detail", args=[self.item.pk]),
        )

    def test_finalisieren_setzt_den_finalen_zustand(self) -> None:
        """Die Aktion macht den Entwurf zu einer finalen Fassung."""
        self.client.post(reverse("fragebogen_items:finalisieren", args=[self.item.pk]))
        self.item.refresh_from_db()

        self.assertEqual(self.item.zustand, FragebogenItem.Zustand.FINAL)

    def test_finalisieren_setzt_den_zeitpunkt(self) -> None:
        """Die Aktion hält den Finalisierungszeitpunkt fest."""
        self.client.post(reverse("fragebogen_items:finalisieren", args=[self.item.pk]))
        self.item.refresh_from_db()

        self.assertIsNotNone(self.item.finalisiert_am)

    def test_finalisierte_fassung_zeigt_keine_finalisieren_aktion(self) -> None:
        """Nach dem Zustandswechsel ist die Aktion im Editor nicht mehr sichtbar."""
        self.client.post(reverse("fragebogen_items:finalisieren", args=[self.item.pk]))
        response: HttpResponse = self.client.get(
            reverse("fragebogen_items:detail", args=[self.item.pk])
        )

        self.assertNotContains(response, "Finalisieren")

    def test_finalisierte_fassung_zeigt_final_in_der_bibliothek(self) -> None:
        """Die Bibliothek zeigt den Zustand der finalisierten Fassung an."""
        self.client.post(reverse("fragebogen_items:finalisieren", args=[self.item.pk]))
        response: HttpResponse = self.client.get(reverse("fragebogen_items:liste"))

        self.assertContains(response, "Final")

    def test_finalisieren_akzeptiert_keine_bereits_finale_fassung(self) -> None:
        """Die zustandsgebundene Aktion ist nach dem Finalisieren nicht erneut nutzbar."""
        self.item.finalisieren()

        response: HttpResponse = self.client.post(
            reverse("fragebogen_items:finalisieren", args=[self.item.pk])
        )

        self.assertEqual(response.status_code, 404)


class FragebogenItemSichtbarkeitViewTests(TestCase):
    """Die Bibliothek bleibt auf den Eigentümer-Kreis beschränkt."""

    def test_versteckt_fremde_items_in_liste_und_detail(self) -> None:
        """Eine Forschende kann weder fremde Listenzeilen noch Detail-URLs sehen."""
        ada: Konto = _forschende("ada")
        grace: Konto = _forschende("grace")
        eigenes_item: FragebogenItem = FragebogenItem.objects.anlegen(
            ada, wortlaut="Mein Item"
        )
        fremdes_item: FragebogenItem = FragebogenItem.objects.anlegen(
            grace, wortlaut="Fremdes Item"
        )
        self.client.force_login(ada)

        liste: HttpResponse = self.client.get(reverse("fragebogen_items:liste"))
        detail: HttpResponse = self.client.get(
            reverse("fragebogen_items:detail", args=[fremdes_item.pk])
        )

        self.assertContains(liste, eigenes_item.wortlaut)
        self.assertNotContains(liste, fremdes_item.wortlaut)
        self.assertEqual(detail.status_code, 404)

    def test_konto_ohne_forschungsrolle_erhaelt_403(self) -> None:
        """Die App hält ihre Forschenden-Rollenprüfung selbst."""
        konto: Konto = get_user_model().objects.create_user(username="grace")
        item: FragebogenItem = FragebogenItem.objects.anlegen(
            konto, wortlaut="Geschütztes Item"
        )
        self.client.force_login(konto)

        for url in (
            reverse("fragebogen_items:liste"),
            reverse("fragebogen_items:anlegen"),
            reverse("fragebogen_items:detail", args=[item.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 403)


class FragebogenItemKoautorschaftViewTests(TestCase):
    """Der Editor teilt eine Item-Historie ausschließlich mit Ko-Autorinnen."""

    ada: Konto
    grace: Konto
    linus: Konto
    item: FragebogenItem

    def setUp(self) -> None:
        """Legt eine private Item-Historie und drei Forschende an."""
        self.ada = _forschende("ada")
        self.grace = _forschende("grace")
        self.linus = _forschende("linus")
        self.item = FragebogenItem.objects.anlegen(
            self.ada, wortlaut="Geteiltes Item"
        )

    def test_editor_zeigt_die_eigentuemerin(self) -> None:
        """Die Eigentümerin erscheint in der Ko-Autorinnenliste des Editors."""
        self.client.force_login(self.ada)

        response: HttpResponse = self.client.get(
            reverse("fragebogen_items:detail", args=[self.item.pk])
        )

        self.assertContains(response, self.ada.username)

    def test_hinzufuegen_gibt_koautorin_bibliothekszugriff(self) -> None:
        """Eine hinzugefügte Ko-Autorin sieht die Item-Linie in ihrer Bibliothek."""
        self.client.force_login(self.ada)
        self.client.post(
            reverse("fragebogen_items:koautorin_hinzufuegen", args=[self.item.pk]),
            {"konto": self.grace.pk},
        )
        self.client.force_login(self.grace)

        response: HttpResponse = self.client.get(reverse("fragebogen_items:liste"))

        self.assertContains(response, self.item.wortlaut)

    def test_koautorin_kann_item_finalisieren(self) -> None:
        """Eine Ko-Autorin darf die sichtbare Item-Linie gleichrangig pflegen."""
        self.client.force_login(self.ada)
        self.client.post(
            reverse("fragebogen_items:koautorin_hinzufuegen", args=[self.item.pk]),
            {"konto": self.grace.pk},
        )
        self.client.force_login(self.grace)

        response: HttpResponse = self.client.post(
            reverse("fragebogen_items:finalisieren", args=[self.item.pk])
        )

        self.assertRedirects(
            response, reverse("fragebogen_items:detail", args=[self.item.pk])
        )

    def test_fremde_kann_die_item_linie_nicht_aufrufen_oder_aendern(self) -> None:
        """Eine Fremde erhält für Ansicht und Editor-Aktionen keine Berechtigung."""
        self.client.force_login(self.linus)

        responses: list[HttpResponse] = [
            self.client.get(reverse("fragebogen_items:detail", args=[self.item.pk])),
            self.client.post(
                reverse("fragebogen_items:finalisieren", args=[self.item.pk])
            ),
            self.client.post(
                reverse("fragebogen_items:koautorin_hinzufuegen", args=[self.item.pk]),
                {"konto": self.grace.pk},
            ),
            self.client.post(
                reverse(
                    "fragebogen_items:koautorin_entfernen",
                    args=[self.item.pk, self.ada.pk],
                )
            ),
        ]

        self.assertEqual({response.status_code for response in responses}, {404})

    def test_entfernen_entzieht_koautorin_den_bibliothekszugriff(self) -> None:
        """Eine entfernte Ko-Autorin sieht die Item-Linie nicht mehr."""
        self.client.force_login(self.ada)
        self.client.post(
            reverse("fragebogen_items:koautorin_hinzufuegen", args=[self.item.pk]),
            {"konto": self.grace.pk},
        )
        self.client.post(
            reverse(
                "fragebogen_items:koautorin_entfernen",
                args=[self.item.pk, self.grace.pk],
            )
        )
        self.client.force_login(self.grace)

        response: HttpResponse = self.client.get(
            reverse("fragebogen_items:detail", args=[self.item.pk])
        )

        self.assertEqual(response.status_code, 404)


class FragebogenItemLikertViewTests(TestCase):
    """Likert-Items zeigen ihre global festgelegte Skala nur lesend."""

    def test_detail_zeigt_alle_globalen_likert_stufen_ohne_eingabefelder(self) -> None:
        """Die Skalenpole sind sichtbar, aber am Item nicht konfigurierbar."""
        ada: Konto = _forschende("ada")
        item: FragebogenItem = FragebogenItem.objects.anlegen(
            ada,
            typ=FragebogenItem.Typ.LIKERT,
            wortlaut="Ich fühle mich sicher.",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("fragebogen_items:detail", args=[item.pk])
        )

        for skalenpol in (
            "Stimme voll zu",
            "Stimme zu",
            "Stimme eher zu",
            "Stimme eher nicht zu",
            "Stimme nicht zu",
            "Stimme gar nicht zu",
        ):
            self.assertContains(response, skalenpol)
        self.assertNotContains(response, 'name="skalenpol"')


class FragebogenItemListeViewTests(TestCase):
    """Die Bibliothek verdichtet Fassungen zu einer Zeile je Historie."""

    def test_zeigt_pro_historie_nur_die_neueste_fassung_mit_ihrem_zustand(
        self,
    ) -> None:
        """Alte Fassungen bleiben aus der Bibliothek ausgeblendet."""
        ada: Konto = _forschende("ada")
        alte_fassung: FragebogenItem = FragebogenItem.objects.anlegen(
            ada, wortlaut="Alte Fassung"
        )
        alte_fassung.finalisieren()
        neue_fassung: FragebogenItem = alte_fassung.bearbeiten()
        neue_fassung.wortlaut = "Neueste Fassung"
        neue_fassung.save()
        finale_historie: FragebogenItem = FragebogenItem.objects.anlegen(
            ada, wortlaut="Bereits final"
        )
        finale_historie.finalisieren()
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(reverse("fragebogen_items:liste"))

        self.assertContains(response, "Neueste Fassung")
        self.assertNotContains(response, "Alte Fassung")
        self.assertContains(response, "Entwurf")
        self.assertContains(response, "Bereits final")
        self.assertContains(response, "Final")
        self.assertContains(response, 'badge--final')
        self.assertContains(response, 'badge--research')

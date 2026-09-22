"""HTTP-Tests für die Forschenden-UI der Erhebungen."""

import csv
import json
import re
from datetime import UTC, datetime, timedelta
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from config.tests.dokumentation import exportdateien_aus_adr_0029
from konten.models import Konto
from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsitem,
    Erhebungsvignette,
    ItemAntwort,
    Itemblock,
    Stichprobe,
    Vignettenziehung,
)
from erhebungen.teilnahme_session import TEILNAHME_TOKENS_SESSION_KEY
from fragebogen_items.models import FragebogenItem
from simulation.models import Anbieter, ModellKonfiguration, Simulationskern
from sitzungen.models import (
    Diagnose,
    Eingabemodus,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
    Vignettenposition,
)
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette


def _zeitstempel(wert: datetime) -> str:
    """Schreibt einen Zeitstempel so, wie der Export ihn erwartet."""

    return timezone.localtime(wert, timezone.UTC).isoformat(timespec="seconds")


def _laufende_bindung(erhebung: Erhebung, token: str) -> Erhebungsbindung:
    """Bindet eine Teilnahme an eine gerade laufende Stichprobe der Erhebung."""

    return Erhebungsbindung.objects.create(
        stichprobe=Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        ),
        teilnahme=Teilnahme.objects.create(),
        token=token,
    )


def _forschungskonfiguration(
    name: str = "forschung",
    parameter: dict[str, object] | None = None,
) -> ModellKonfiguration:
    """Legt eine gültige Konfiguration an, die sich am Namen wiedererkennen lässt."""

    return ModellKonfiguration.objects.create(
        anbieter=Anbieter.OPENROUTER,
        sprachmodell=f"openrouter/{name}",
        anbieter_token="sk-or-geheim",
        parameter=parameter or {},
    )


def _infomaniak_konfiguration() -> ModellKonfiguration:
    """Legt eine Konfiguration an, die Basis-URL und Token wirklich trägt."""

    return ModellKonfiguration.objects.create(
        anbieter=Anbieter.INFOMANIAK,
        sprachmodell="openai/mistral24b",
        anbieter_basis_url="https://api.infomaniak.com/1/ai/4711/openai",
        anbieter_token="sk-infomaniak-geheim",
        parameter={"temperature": 0.2},
    )


def _finale_vignette_anlegen(
    konto: Konto,
    fach: str,
    budget_typ: str = Vignette.BudgetTyp.SCHRITTE,
    budget_wert: int = 3,
) -> Vignette:
    """Legt eine einbindbare finale Vignette an."""

    vignette: Vignette = Vignette.objects.anlegen(konto)
    vignette.fehlermuster_beschreibung = "Zähler und Nenner addieren"
    vignette.lernauftrag_text = "Addiere die Brüche."
    vignette.arbeitsheft_bildbeschreibung = "Falsche Bruchrechnung"
    vignette.arbeitsheft_text = "1/2 + 1/3 = 2/5"
    vignette.schuelerin_name = "Lea"
    vignette.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.lehrperson_name = "Ada"
    vignette.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
    vignette.fach = fach
    vignette.thema = "Bruchrechnung"
    vignette.klassenstufe = "6"
    vignette.budget_typ = budget_typ
    vignette.budget_wert = budget_wert
    vignette.save()
    vignette.finalisieren()
    return vignette


def _finales_item_anlegen(
    konto: Konto,
    wortlaut: str,
    typ: str = FragebogenItem.Typ.FREITEXT,
) -> FragebogenItem:
    """Legt eine einbindbare finale Item-Fassung an."""

    item: FragebogenItem = FragebogenItem.objects.anlegen(
        konto, typ=typ, wortlaut=wortlaut
    )
    item.finalisieren()
    return item


def _item_zuordnen(
    erhebung: Erhebung,
    item: FragebogenItem,
    andockpunkt: str,
    position: int,
) -> Erhebungsitem:
    """Bindet eine Item-Fassung an einen Andockpunkt der Erhebung."""

    return Erhebungsitem.objects.create(
        erhebung=erhebung, item=item, andockpunkt=andockpunkt, position=position
    )


class ErhebungenForschendenRollenTests(TestCase):
    """Nur Forschende erreichen die Forschenden-Views."""

    def test_konto_ohne_forschendenrolle_erhaelt_auf_alle_forschenden_views_403(
        self,
    ) -> None:
        """Die Erhebungs-UI ist von der öffentlichen Teilnahme getrennt geschützt."""
        konto: Konto = get_user_model().objects.create_user(username="grace")
        erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
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
        Erhebung.objects.anlegen(grace, name="Fremde Erhebung")
        self.client.force_login(ada)

        angelegt: HttpResponse = self.client.post(
            reverse("erhebungen:anlegen"), {"name": "Brüche erforschen"}
        )

        erhebung: Erhebung = Erhebung.objects.get(eigentuemerinnen=ada)
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
        ModellKonfiguration.objects.aktivieren(_forschungskonfiguration())
        Erhebung.objects.anlegen(ada, name="Noch Entwurf")
        finale: Erhebung = Erhebung.objects.anlegen(ada, name="Schon final")
        finale.finalisieren()
        abgelegte: Erhebung = Erhebung.objects.anlegen(ada, name="Längst abgelegt")
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

    def test_liste_zeigt_kein_teilnahme_token_aus_der_browsersession(self) -> None:
        """Ein selbst getesteter Teilnahme-Link spielt kein Token in die Sidebar."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.client.force_login(ada)
        sitzung = self.client.session
        sitzung[TEILNAHME_TOKENS_SESSION_KEY] = {
            "4f1c0f0e-0000-4000-8000-000000000000": "ABCD-2345"
        }
        sitzung.save()

        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))

        self.assertNotContains(liste, "ABCD-2345")
        self.assertContains(liste, "sidebar-account")

    def test_administration_legt_eine_erhebung_an(self) -> None:
        """Die Administration steht im Forschungsbereich nicht vor der Tür (ADR-0033)."""
        administratorin: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        self.client.force_login(administratorin)

        angelegt: HttpResponse = self.client.post(
            reverse("erhebungen:anlegen"), {"name": "Brüche erforschen"}
        )

        erhebung: Erhebung = Erhebung.objects.get(eigentuemerinnen=administratorin)
        self.assertRedirects(angelegt, reverse("erhebungen:detail", args=[erhebung.pk]))

    def test_administration_sieht_fremde_erhebung_in_der_liste(self) -> None:
        """Die Administration findet fremde Erhebungen für den Eigentümerwechsel."""
        grace: Konto = get_user_model().objects.create_user(username="grace")
        erhebung: Erhebung = Erhebung.objects.anlegen(grace, name="Fremde Erhebung")
        administratorin: Konto = get_user_model().objects.create_user(username="ada")
        administratorin.is_superuser = True
        administratorin.save()
        self.client.force_login(administratorin)

        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))

        self.assertContains(liste, erhebung.name)


class ErhebungenSichtbarkeitUndLoeschenTests(TestCase):
    """Die Detail- und Lösch-URLs folgen der Eigentümersicht."""

    def setUp(self) -> None:
        """Legt eine Forschende mit einem Entwurf an."""
        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.entwurf: Erhebung = Erhebung.objects.anlegen(
            self.ada, name="Eigener Entwurf"
        )
        self.client.force_login(self.ada)

    def test_fremde_erhebung_ist_nicht_erreichbar(self) -> None:
        """Andere Eigentümerinnen erhalten keine Information über eine Erhebung."""
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde_erhebung: Erhebung = Erhebung.objects.anlegen(
            grace, name="Fremde Erhebung"
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
        finale: Erhebung = Erhebung.objects.anlegen(self.ada, name="Finale Erhebung")
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake"
        )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        finale.finalisieren()
        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))

        self.assertRedirects(geloescht, reverse("erhebungen:liste"))
        self.assertFalse(Erhebung.objects.filter(pk=self.entwurf.pk).exists())
        self.assertNotContains(liste, reverse("erhebungen:loeschen", args=[finale.pk]))


class ErhebungenKoForschendenViewTests(TestCase):
    """Forschende teilen Erhebungen mit gleichrangigen Ko-Forschenden."""

    def test_hinzufuegen_gibt_ko_forschender_listen_und_editorzugriff(self) -> None:
        """Eine eingetragene Ko-Forschende sieht und bearbeitet den Entwurf."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Geteilte Erhebung")
        self.client.force_login(ada)

        hinzufuegen: HttpResponse = self.client.post(
            reverse("erhebungen:eigentuemerin_hinzufuegen", args=[erhebung.pk]),
            {"konto": grace.pk},
        )

        self.assertRedirects(
            hinzufuegen, reverse("erhebungen:detail", args=[erhebung.pk])
        )
        self.client.force_login(grace)
        self.assertContains(self.client.get(reverse("erhebungen:liste")), erhebung.name)
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[erhebung.pk])
        )
        self.assertContains(detail, "Eigentümer:innen")
        self.assertContains(detail, ada.username)
        self.assertContains(detail, grace.username)
        bearbeiten: HttpResponse = self.client.post(
            reverse("erhebungen:konfiguration_speichern", args=[erhebung.pk]),
            {"instruktionstext": "Bitte denken Sie laut.", "randomisierung": "fest"},
        )

        self.assertRedirects(
            bearbeiten, reverse("erhebungen:detail", args=[erhebung.pk])
        )
        erhebung.refresh_from_db()
        self.assertEqual(erhebung.instruktionstext, "Bitte denken Sie laut.")

    def test_selbstentfernung_uebergibt_finale_und_laufende_erhebung(self) -> None:
        """Eine Forschende kann die Verantwortung auch im Erhebungszeitraum abgeben."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Laufende Erhebung")
        ModellKonfiguration.objects.aktivieren(_forschungskonfiguration())
        erhebung.finalisieren()
        Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        erhebung.eigentuemerinnen.add(grace)
        self.client.force_login(ada)

        entfernen: HttpResponse = self.client.post(
            reverse("erhebungen:eigentuemerin_entfernen", args=[erhebung.pk, ada.pk])
        )

        self.assertRedirects(entfernen, reverse("erhebungen:liste"))
        self.assertEqual(list(erhebung.eigentuemerinnen.all()), [grace])

    def test_nicht_eigentuemerin_loest_keinen_selbst_redirect_aus(self) -> None:
        """Eine fremde Administration bleibt bei der Erhebung, wenn sie niemanden entfernt."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Forschende:r"))
        administratorin: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fremde Erhebung")
        erhebung.eigentuemerinnen.add(grace)
        self.client.force_login(administratorin)

        response: HttpResponse = self.client.post(
            reverse(
                "erhebungen:eigentuemerin_entfernen",
                args=[erhebung.pk, administratorin.pk],
            )
        )

        self.assertRedirects(response, reverse("erhebungen:detail", args=[erhebung.pk]))

    def test_entfernen_der_letzten_eigentuemerin_wird_verweigert(self) -> None:
        """Die Bedienung kann eine aktive Erhebung nicht eigentümerlos machen."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Geschützte Erhebung")
        self.client.force_login(ada)

        self.client.post(
            reverse("erhebungen:eigentuemerin_entfernen", args=[erhebung.pk, ada.pk])
        )

        self.assertEqual(list(erhebung.eigentuemerinnen.all()), [ada])

    def test_teilen_laesst_nur_forschende_oder_administration_zu(self) -> None:
        """Das Eintragen vergibt keine Rolle und lässt Unberechtigte außen vor."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        ohne_rolle: Konto = get_user_model().objects.create_user(username="linus")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Geschützte Erhebung")
        self.client.force_login(ada)

        hinzufuegen: HttpResponse = self.client.post(
            reverse("erhebungen:eigentuemerin_hinzufuegen", args=[erhebung.pk]),
            {"konto": ohne_rolle.pk},
        )

        self.assertEqual(hinzufuegen.status_code, 404)
        self.assertFalse(erhebung.eigentuemerinnen.filter(pk=ohne_rolle.pk).exists())
        self.assertFalse(ohne_rolle.groups.exists())

    def test_administration_kann_fremde_erhebung_uebergeben(self) -> None:
        """Die Administration kann eine fremde Forschende durch eine andere ablösen."""
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Forschende:r"))
        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        administratorin: Konto = get_user_model().objects.create_user(
            username="linus", is_superuser=True
        )
        erhebung: Erhebung = Erhebung.objects.anlegen(grace, name="Fremde Erhebung")
        self.client.force_login(administratorin)

        self.assertContains(
            self.client.get(reverse("erhebungen:detail", args=[erhebung.pk])),
            f'<option value="{administratorin.pk}">{administratorin.username}</option>',
            html=True,
        )
        self.client.post(
            reverse("erhebungen:eigentuemerin_hinzufuegen", args=[erhebung.pk]),
            {"konto": ada.pk},
        )
        self.client.post(
            reverse("erhebungen:eigentuemerin_hinzufuegen", args=[erhebung.pk]),
            {"konto": administratorin.pk},
        )
        entfernen: HttpResponse = self.client.post(
            reverse("erhebungen:eigentuemerin_entfernen", args=[erhebung.pk, grace.pk])
        )

        self.assertRedirects(
            entfernen, reverse("erhebungen:detail", args=[erhebung.pk])
        )
        self.assertEqual(set(erhebung.eigentuemerinnen.all()), {ada, administratorin})


class ErhebungenEntwurfKonfigurierenTests(TestCase):
    """Forschende stellen den Vignettenablauf ihres Entwurfs zusammen."""

    def setUp(self) -> None:
        """Legt die kleinste Umgebung einer Forschenden mit Entwurf an."""

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
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
        self.assertContains(wieder_offen, "Finale Items aufnehmen")
        self.assertEqual(
            wieder_offen.context["am_ende_aufgenommene_daten"][0]["label"],
            item.wortlaut,
        )

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
        fremde_erhebung: Erhebung = Erhebung.objects.anlegen(grace, name="Fremd")

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


class ErhebungsansichtAnbieterTests(TestCase):
    """Die gelbe Ansicht zeigt genau die Exportspalten der Konfiguration."""

    def setUp(self) -> None:
        # Pinnt eine Infomaniak-Konfiguration an eine finale Erhebung.

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.konfiguration: ModellKonfiguration = _infomaniak_konfiguration()
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
        self.erhebung.finalisieren()
        self.client.force_login(self.ada)

    def test_zeigt_anbieter_sprachmodell_und_parameter(self) -> None:
        """Die Forschende sieht in der Oberfläche, was auch im Datensatz steht."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(detail, "Anbieter")
        self.assertContains(detail, "infomaniak")
        self.assertContains(detail, "openai/mistral24b")
        self.assertContains(detail, "temperature")

    def test_zeigt_weder_basis_url_noch_token(self) -> None:
        """Kontoidentifikator und Geheimnis bleiben aus der gelben Ansicht heraus."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertNotContains(detail, "infomaniak.com")
        self.assertNotContains(detail, self.konfiguration.anbieter_token)


class ErhebungenFinalisierenTests(TestCase):
    """Forschende finalisieren Entwürfe über die Detailseite."""

    def setUp(self) -> None:
        # Richtet den gemeinsamen Entwurf einer eingeloggten Forschenden ein.

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.ada.groups.add(Group.objects.get(name="Forschende:r"))
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
        self.konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.client.force_login(self.ada)

    def test_finalisieren_sperrt_design_und_zeigt_gepinnte_konfiguration(self) -> None:
        """Die Detailseite zeigt den finalen, gepinnten Zustand statt Editoren."""

        response: HttpResponse = self.client.post(
            reverse("erhebungen:finalisieren", args=[self.erhebung.pk]), follow=True
        )

        self.assertContains(response, "Final")
        self.assertContains(response, "openrouter/forschung")
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
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
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

    @override_settings(TIME_ZONE="Europe/Berlin")
    def test_liest_den_eingegebenen_zeitraum_als_ortszeit(self) -> None:
        """Das Formularfeld sendet nackte Wanduhrzeit; sie meint die Ortszeit.

        Liest der View sie stattdessen als UTC, verschiebt sich das
        Teilnahmefenster um den Ortsversatz und die Stichprobe verweigert
        die Teilnahme, obwohl sie laut Eingabe längst läuft.
        """

        self.client.post(
            reverse("erhebungen:stichprobe_anlegen", args=[self.erhebung.pk]),
            {"beginn": "2026-08-01T09:00", "ende": "2026-08-31T17:00"},
        )

        stichprobe: Stichprobe = Stichprobe.objects.get(erhebung=self.erhebung)
        self.assertEqual(stichprobe.beginn, datetime(2026, 8, 1, 7, tzinfo=UTC))
        self.assertEqual(stichprobe.ende, datetime(2026, 8, 31, 15, tzinfo=UTC))

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

        entwurf: Erhebung = Erhebung.objects.anlegen(self.ada, name="Entwurf")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        fremde: Erhebung = Erhebung.objects.anlegen(grace, name="Fremd")
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
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
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
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(
            ada,
            name="Brüche & Zahlen",
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
                    "fragebogen_items.csv",
                    "gespraechsschritte.csv",
                    "item_antworten.csv",
                    "itembloecke.csv",
                    "likert_skala.csv",
                    "modellkonfigurationen.csv",
                    "simulationskerne.csv",
                    "sitzungen.csv",
                    "stichproben.csv",
                    "teilnahmen.csv",
                    "vignettenfassungen.csv",
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

    def test_exportiert_nur_referenzierte_fassungen_mit_vollem_inhalt(self) -> None:
        """Fassungstabellen machen die exportierte Datenspur selbsttragend."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erste_konfiguration: ModellKonfiguration = _forschungskonfiguration(
            "erstes-modell", parameter={"temperature": 0.2}
        )
        ModellKonfiguration.objects.aktivieren(erste_konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        erhebung.finalisieren()
        zweite_konfiguration: ModellKonfiguration = _forschungskonfiguration(
            "zweites-modell", parameter={"temperature": 0.7}
        )
        ungenutzte_konfiguration: ModellKonfiguration = _forschungskonfiguration(
            "nicht-exportieren"
        )
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
        erster_kern: Simulationskern = Simulationskern.objects.anlegen(
            system_prompt_vorlage="System Zeile eins\nSystem Zeile zwei",
            user_prompt_vorlage="User $lernauftrag",
            rahmenhandlung_einleitung="Einleitung\nmehrzeilig",
            rahmenhandlung_gespraechseinleitung="Gespräch",
            rahmenhandlung_debrief="Debrief",
        )
        erster_kern.finalisieren()
        zweiter_kern: Simulationskern = erster_kern.bearbeiten()
        zweiter_kern.system_prompt_vorlage = "Verwendeter System-Prompt\nZeile zwei"
        zweiter_kern.save()
        zweiter_kern.finalisieren()
        erste_vignette: Vignette = _finale_vignette_anlegen(ada, "Mathematik")
        erste_vignette = erste_vignette.bearbeiten()
        erste_vignette.lernauftrag_text = "Addiere [bild] die Brüche."
        erste_vignette.lernauftrag_bild = "vignettenbilder/lernauftrag.png"
        erste_vignette.lernauftrag_bildbeschreibung = "Ein Bruch-Arbeitsblatt"
        erste_vignette.lernauftrag_simulationshinweise = "Hinweis zum Lernauftrag"
        erste_vignette.arbeitsheft_simulationshinweise = "Hinweis zum Arbeitsheft"
        erste_vignette.save()
        erste_vignette.finalisieren()
        zweite_vignette: Vignette = erste_vignette.bearbeiten()
        zweite_vignette.arbeitsheft_text = "1/2 + [bild] 1/3 = 2/5"
        zweite_vignette.arbeitsheft_bild = "vignettenbilder/bruchbild.png"
        zweite_vignette.arbeitsheft_bildbeschreibung = (
            "Bildbeschreibung des Arbeitshefts"
        )
        zweite_vignette.referenzdiagnose = "Mehrzeilige\nReferenzdiagnose"
        zweite_vignette.save()
        zweite_vignette.finalisieren()
        ungenutzte_vignette: Vignette = _finale_vignette_anlegen(ada, "Physik")
        Vignettenziehung.objects.create(
            erhebungsbindung=bindung, vignette=erste_vignette, position=1
        )
        sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=bindung.teilnahme,
            vignette=zweite_vignette,
            simulationskern=zweiter_kern,
            modell_konfiguration=zweite_konfiguration,
        )
        Vignettenposition.objects.create(
            teilnahme=bindung.teilnahme,
            sitzung=sitzung,
            vignette=zweite_vignette,
            position=2,
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            vignetten: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(
                        zip_datei.open("vignettenfassungen.csv"), encoding="utf-8"
                    )
                )
            )
            kerne: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(
                        zip_datei.open("simulationskerne.csv"), encoding="utf-8"
                    )
                )
            )
            konfigurationen: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(
                        zip_datei.open("modellkonfigurationen.csv"), encoding="utf-8"
                    )
                )
            )

        vignetten_nach_id: dict[str, dict[str, str]] = {
            vignette["id"]: vignette for vignette in vignetten
        }
        self.assertEqual(
            list(vignetten[0].keys()),
            [
                "id",
                "historie_id",
                "finalisiert_am",
                "fehlermuster_beschreibung",
                "lernauftrag_text",
                "lernauftrag_bild",
                "lernauftrag_bildbeschreibung",
                "lernauftrag_simulationshinweise",
                "arbeitsheft_text",
                "arbeitsheft_bild",
                "arbeitsheft_bildbeschreibung",
                "arbeitsheft_simulationshinweise",
                "schuelerin_name",
                "schuelerin_geschlecht",
                "lehrperson_name",
                "lehrperson_geschlecht",
                "fach",
                "thema",
                "klassenstufe",
                "referenzdiagnose",
                "budget_typ",
                "budget_wert",
            ],
        )
        self.assertEqual(
            set(vignetten_nach_id),
            {str(erste_vignette.pk), str(zweite_vignette.pk)},
        )
        self.assertEqual(
            {vignette["historie_id"] for vignette in vignetten},
            {str(zweite_vignette.historie_id)},
        )
        self.assertEqual(
            vignetten_nach_id[str(erste_vignette.pk)]["lernauftrag_text"],
            "Addiere [bild] die Brüche.",
        )
        self.assertEqual(
            vignetten_nach_id[str(erste_vignette.pk)]["lernauftrag_bild"],
            "vignettenbilder/lernauftrag.png",
        )
        self.assertEqual(
            vignetten_nach_id[str(erste_vignette.pk)]["lernauftrag_bildbeschreibung"],
            "Ein Bruch-Arbeitsblatt",
        )
        self.assertEqual(
            vignetten_nach_id[str(erste_vignette.pk)][
                "lernauftrag_simulationshinweise"
            ],
            "Hinweis zum Lernauftrag",
        )
        self.assertEqual(
            vignetten_nach_id[str(erste_vignette.pk)][
                "arbeitsheft_simulationshinweise"
            ],
            "Hinweis zum Arbeitsheft",
        )
        self.assertEqual(
            vignetten_nach_id[str(zweite_vignette.pk)]["arbeitsheft_text"],
            "1/2 + [bild] 1/3 = 2/5",
        )
        self.assertEqual(
            vignetten_nach_id[str(zweite_vignette.pk)]["referenzdiagnose"],
            "Mehrzeilige\nReferenzdiagnose",
        )
        self.assertEqual(
            vignetten_nach_id[str(erste_vignette.pk)]["arbeitsheft_bild"],
            "",
        )
        self.assertEqual(
            vignetten_nach_id[str(zweite_vignette.pk)]["arbeitsheft_bild"],
            "vignettenbilder/bruchbild.png",
        )
        self.assertEqual(
            vignetten_nach_id[str(zweite_vignette.pk)]["arbeitsheft_bildbeschreibung"],
            "Bildbeschreibung des Arbeitshefts",
        )
        self.assertNotIn(
            str(ungenutzte_vignette.pk),
            vignetten_nach_id,
        )
        self.assertEqual(
            kerne,
            [
                {
                    "id": str(zweiter_kern.pk),
                    "historie_id": str(zweiter_kern.historie_id),
                    "finalisiert_am": zweiter_kern.finalisiert_am.isoformat(
                        timespec="seconds"
                    ),
                    "system_prompt_vorlage": "Verwendeter System-Prompt\nZeile zwei",
                    "user_prompt_vorlage": "User $lernauftrag",
                    "rahmenhandlung_einleitung": "Einleitung\nmehrzeilig",
                    "rahmenhandlung_gespraechseinleitung": "Gespräch",
                    "rahmenhandlung_debrief": "Debrief",
                }
            ],
        )
        self.assertEqual(
            {konfiguration["id"] for konfiguration in konfigurationen},
            {str(erste_konfiguration.pk), str(zweite_konfiguration.pk)},
        )
        self.assertNotIn(
            str(ungenutzte_konfiguration.pk),
            {konfiguration["id"] for konfiguration in konfigurationen},
        )
        self.assertEqual(
            {
                konfiguration["id"]: json.loads(konfiguration["parameter"])
                for konfiguration in konfigurationen
            },
            {
                str(erste_konfiguration.pk): {"temperature": 0.2},
                str(zweite_konfiguration.pk): {"temperature": 0.7},
            },
        )

    def test_exportiert_den_anbieter_und_kein_zugangsdatum(self) -> None:
        """Der Anbieter macht den Modellnamen lesbar; Token und URL bleiben draußen."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = _infomaniak_konfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        erhebung.finalisieren()
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            konfigurationen: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(
                        zip_datei.open("modellkonfigurationen.csv"), encoding="utf-8"
                    )
                )
            )
            archivinhalt: str = "".join(
                zip_datei.read(name).decode("utf-8") for name in zip_datei.namelist()
            )

        self.assertEqual(
            list(konfigurationen[0].keys()),
            ["id", "anbieter", "sprachmodell", "parameter"],
        )
        self.assertEqual(
            konfigurationen,
            [
                {
                    "id": str(konfiguration.pk),
                    "anbieter": "infomaniak",
                    "sprachmodell": "openai/mistral24b",
                    "parameter": '{"temperature": 0.2}',
                }
            ],
        )
        self.assertNotIn(konfiguration.anbieter_token, archivinhalt)
        self.assertNotIn(konfiguration.anbieter_basis_url, archivinhalt)
        self.assertNotIn("infomaniak.com", archivinhalt)

    def test_exportiert_die_transkriptions_konfiguration_nicht(self) -> None:
        """Die Transkription gehört nicht in den Datensatz (ADR-0026)."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        ModellKonfiguration.objects.aktivieren(_forschungskonfiguration())
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        erhebung.finalisieren()
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            dateinamen: list[str] = zip_datei.namelist()

        self.assertEqual([name for name in dateinamen if "transkription" in name], [])

    def test_exportiert_ziehungen_und_alle_erhebungssitzungen(self) -> None:
        """Die Ziehung zeigt den Plan, Sitzungen zeigen jeden tatsächlichen Ausgang."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
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
                teilnahme=bindung.teilnahme,
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

    def test_exportiert_die_verbrauchte_zeit_ohne_die_offene_spanne(self) -> None:
        """Die verbrauchte Zeit ist Datenspur (ADR-0012), der Spannenstart nicht."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        erhebung.finalisieren()
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        zeitvignette: Vignette = _finale_vignette_anlegen(
            ada, "Mathematik", budget_typ=Vignette.BudgetTyp.ZEIT, budget_wert=600
        )
        schrittvignette: Vignette = _finale_vignette_anlegen(ada, "Physik")
        # Nur die Zeitsitzung traegt eine offene Spanne: Bei schrittbasiertem
        # Budget laeuft nach ADR-0012 keine Uhr, die eine ansetzen koennte.
        for token, vignette, verbraucht, offene_spanne in (
            ("2345-6781", zeitvignette, 417.5, timezone.now()),
            ("2345-6782", schrittvignette, 0.0, None),
        ):
            bindung: Erhebungsbindung = _laufende_bindung(erhebung, token)
            sitzung: Sitzung = Sitzung.objects.create(
                teilnahme=bindung.teilnahme,
                vignette=vignette,
                simulationskern=kern,
                modell_konfiguration=konfiguration,
                verbrauchte_zeit=verbraucht,
                offene_spanne_seit=offene_spanne,
            )
            Vignettenposition.objects.create(
                teilnahme=bindung.teilnahme,
                sitzung=sitzung,
                vignette=vignette,
                position=1,
            )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            leser: csv.DictReader = csv.DictReader(
                TextIOWrapper(zip_datei.open("sitzungen.csv"), encoding="utf-8")
            )
            verbrauchte_zeiten: dict[str, str] = {
                zeile["vignette_id"]: zeile["verbrauchte_zeit"] for zeile in leser
            }
            spalten: list[str] = list(leser.fieldnames or [])

        self.assertNotIn("offene_spanne_seit", spalten)
        self.assertEqual(
            verbrauchte_zeiten,
            {str(zeitvignette.pk): "417.5", str(schrittvignette.pk): "0.0"},
        )

    def test_exportiert_gespraechsschritte_fehlversuche_und_diagnosen(self) -> None:
        """Der Export bewahrt die vollständige Datenspur einschließlich Abbrüchen."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
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
            teilnahme=bindung.teilnahme,
            sitzung=sitzung,
            vignette=vignette,
            position=1,
        )
        erfolgreicher_schritt: Gespraechsschritt = Gespraechsschritt.objects.create(
            sitzung=sitzung,
            reihenfolge=1,
            eingabe="Warum?",
            denkspur="Zeile eins\nZeile zwei",
            aeusserung="Antwort eins\nAntwort zwei",
            eingabemodus=Eingabemodus.TRANSKRIBIERT,
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
        abbruchschritt: Gespraechsschritt = (
            Gespraechsschritt.objects.answerless_anlegen(
                sitzung=sitzung,
                reihenfolge=3,
                eingabe="Noch einmal?",
                fehlversuche=[
                    Fehlversuch(grund="Anbieterfehler", rohantwort="timeout")
                ],
            )
        )
        Diagnose.objects.create(
            sitzung=sitzung, text="Bruchfehler", eingabemodus=Eingabemodus.GEMISCHT
        )
        training: Training = Training.objects.anlegen(ada, name="Nicht exportieren")
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
            schritt_leser: csv.DictReader[str] = csv.DictReader(
                TextIOWrapper(
                    zip_datei.open("gespraechsschritte.csv"), encoding="utf-8"
                )
            )
            schritte: list[dict[str, str]] = list(schritt_leser)
            kopfzeile: list[str] = list(schritt_leser.fieldnames or [])
            fehlversuche: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("fehlversuche.csv"), encoding="utf-8")
                )
            )
            diagnose_leser: csv.DictReader[str] = csv.DictReader(
                TextIOWrapper(zip_datei.open("diagnosen.csv"), encoding="utf-8")
            )
            diagnosen: list[dict[str, str]] = list(diagnose_leser)
            diagnose_kopfzeile: list[str] = list(diagnose_leser.fieldnames or [])

        self.assertEqual(
            kopfzeile,
            [
                "id",
                "sitzung_id",
                "reihenfolge",
                "eingabe",
                "denkspur",
                "aeusserung",
                "erstellt_am",
                "eingabemodus",
            ],
        )
        self.assertEqual(
            [
                {name: wert for name, wert in schritt.items() if name != "erstellt_am"}
                for schritt in schritte
            ],
            [
                {
                    "id": str(erfolgreicher_schritt.pk),
                    "sitzung_id": str(sitzung.pk),
                    "reihenfolge": "1",
                    "eingabe": "Warum?",
                    "denkspur": "Zeile eins\nZeile zwei",
                    "aeusserung": "Antwort eins\nAntwort zwei",
                    "eingabemodus": "transkribiert",
                },
                {
                    "id": str(leerer_schritt.pk),
                    "sitzung_id": str(sitzung.pk),
                    "reihenfolge": "2",
                    "eingabe": "Bitte knapp.",
                    "denkspur": "",
                    "aeusserung": "",
                    "eingabemodus": "getippt",
                },
                {
                    "id": str(abbruchschritt.pk),
                    "sitzung_id": str(sitzung.pk),
                    "reihenfolge": "3",
                    "eingabe": "Noch einmal?",
                    "denkspur": "NA",
                    "aeusserung": "NA",
                    "eingabemodus": "getippt",
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
            diagnose_kopfzeile,
            ["sitzung_id", "text", "erstellt_am", "eingabemodus"],
        )
        self.assertEqual(
            [
                {name: wert for name, wert in diagnose.items() if name != "erstellt_am"}
                for diagnose in diagnosen
            ],
            [
                {
                    "sitzung_id": str(sitzung.pk),
                    "text": "Bruchfehler",
                    "eingabemodus": "gemischt",
                }
            ],
        )
        self.assertRegex(
            diagnosen[0]["erstellt_am"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$",
        )

    def test_exportiert_itembloecke_mit_vorlage_und_erledigt_zeitstempel(self) -> None:
        """Erst der Blockdatensatz trennt »nie vorgelegt« von »leer abgeschickt«."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        erhebung.finalisieren()
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        vignette: Vignette = _finale_vignette_anlegen(ada, "Mathematik")
        bindungen: list[Erhebungsbindung] = [
            _laufende_bindung(erhebung, f"2345-678{nummer}") for nummer in range(1, 3)
        ]
        bloecke: list[Itemblock] = []
        for bindung in bindungen:
            sitzung: Sitzung = Sitzung.objects.create(
                teilnahme=bindung.teilnahme,
                vignette=vignette,
                simulationskern=kern,
                modell_konfiguration=konfiguration,
            )
            bloecke.append(
                Itemblock.objects.create(
                    erhebungsbindung=bindung,
                    andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                    sitzung=sitzung,
                    erledigt_am=timezone.now(),
                )
            )
            bloecke.append(
                Itemblock.objects.create(
                    erhebungsbindung=bindung,
                    andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
                )
            )
        fremde_erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fremd")
        fremde_erhebung.finalisieren()
        Itemblock.objects.create(
            erhebungsbindung=_laufende_bindung(fremde_erhebung, "9999-9999"),
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        )
        self.client.force_login(ada)

        with CaptureQueriesContext(connection) as abfragen:
            response: HttpResponse = self.client.get(
                reverse("erhebungen:export", args=[erhebung.pk])
            )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            zeilen: list[dict[str, str]] = list(
                csv.DictReader(
                    TextIOWrapper(zip_datei.open("itembloecke.csv"), encoding="utf-8")
                )
            )

        self.assertEqual(
            zeilen,
            [
                {
                    "id": str(block.pk),
                    "teilnahme_token": block.erhebungsbindung.token,
                    "andockpunkt": block.andockpunkt,
                    "sitzung_id": (str(block.sitzung_id) if block.sitzung_id else "NA"),
                    "vorgelegt_am": _zeitstempel(block.vorgelegt_am),
                    "erledigt_am": (
                        _zeitstempel(block.erledigt_am) if block.erledigt_am else "NA"
                    ),
                }
                for block in bloecke
            ],
        )
        # Vier Blöcke, eine Abfrage: der Export zerfällt nicht in N+1-Abfragen.
        self.assertEqual(
            sum(
                1
                for abfrage in abfragen.captured_queries
                if "erhebungen_itemblock" in abfrage["sql"]
            ),
            1,
        )

    def test_exportiert_item_antworten_mit_erhaltener_null_semantik(self) -> None:
        """Die Antwortdatei trennt »nicht beantwortet« von »leer abgeschickt«."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fragebogen")
        freitext_item: FragebogenItem = _finales_item_anlegen(
            ada, "Was ist Ihnen aufgefallen?"
        )
        likert_item: FragebogenItem = _finales_item_anlegen(
            ada, "Ich fühlte mich sicher.", typ=FragebogenItem.Typ.LIKERT
        )
        # Dasselbe Paar an beiden Andockpunkten: erst »item_id« plus
        # »andockpunkt« macht eine Antwortzeile eindeutig lesbar.
        freitext_nach_sitzung: Erhebungsitem = _item_zuordnen(
            erhebung, freitext_item, Erhebungsitem.Andockpunkt.NACH_SITZUNG, 1
        )
        likert_nach_sitzung: Erhebungsitem = _item_zuordnen(
            erhebung, likert_item, Erhebungsitem.Andockpunkt.NACH_SITZUNG, 2
        )
        freitext_am_ende: Erhebungsitem = _item_zuordnen(
            erhebung, freitext_item, Erhebungsitem.Andockpunkt.AM_ENDE, 1
        )
        likert_am_ende: Erhebungsitem = _item_zuordnen(
            erhebung, likert_item, Erhebungsitem.Andockpunkt.AM_ENDE, 2
        )
        kern: Simulationskern = Simulationskern.objects.anlegen()
        kern.finalisieren()
        vignette: Vignette = _finale_vignette_anlegen(ada, "Mathematik")
        bindung: Erhebungsbindung = _laufende_bindung(erhebung, "2345-6789")
        sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=bindung.teilnahme,
            vignette=vignette,
            simulationskern=kern,
            modell_konfiguration=konfiguration,
        )
        block_nach_sitzung: Itemblock = Itemblock.objects.create(
            erhebungsbindung=bindung,
            andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
            sitzung=sitzung,
        )
        block_am_ende: Itemblock = Itemblock.objects.create(
            erhebungsbindung=bindung, andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE
        )
        ItemAntwort.objects.create(
            itemblock=block_nach_sitzung,
            erhebungsbindung=bindung,
            erhebungsitem=freitext_nach_sitzung,
            sitzung=sitzung,
            freitext="Zeile eins\nZeile zwei",
        )
        ItemAntwort.objects.create(
            itemblock=block_nach_sitzung,
            erhebungsbindung=bindung,
            erhebungsitem=likert_nach_sitzung,
            sitzung=sitzung,
            likert_stufe=5,
        )
        ItemAntwort.objects.create(
            itemblock=block_am_ende,
            erhebungsbindung=bindung,
            erhebungsitem=freitext_am_ende,
            freitext="",
        )
        # Vorgelegt, aber nicht beantwortet: beide Wertspalten bleiben leer.
        ItemAntwort.objects.create(
            itemblock=block_am_ende,
            erhebungsbindung=bindung,
            erhebungsitem=likert_am_ende,
        )
        fremde_erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fremd")
        fremde_bindung: Erhebungsbindung = _laufende_bindung(
            fremde_erhebung, "9999-9999"
        )
        fremder_block: Itemblock = Itemblock.objects.create(
            erhebungsbindung=fremde_bindung,
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        )
        ItemAntwort.objects.create(
            itemblock=fremder_block,
            erhebungsbindung=fremde_bindung,
            erhebungsitem=_item_zuordnen(
                fremde_erhebung,
                freitext_item,
                Erhebungsitem.Andockpunkt.AM_ENDE,
                1,
            ),
            freitext="Gehört nicht in diesen Export.",
        )
        self.client.force_login(ada)

        with CaptureQueriesContext(connection) as abfragen:
            response: HttpResponse = self.client.get(
                reverse("erhebungen:export", args=[erhebung.pk])
            )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            antwort_leser: csv.DictReader[str] = csv.DictReader(
                TextIOWrapper(zip_datei.open("item_antworten.csv"), encoding="utf-8")
            )
            antworten: list[dict[str, str]] = list(antwort_leser)
            kopfzeile: list[str] = list(antwort_leser.fieldnames or [])

        self.assertEqual(
            kopfzeile,
            [
                "itemblock_id",
                "teilnahme_token",
                "item_id",
                "item_typ",
                "andockpunkt",
                "sitzung_id",
                "position",
                "freitext",
                "likert_stufe",
            ],
        )
        self.assertEqual(
            antworten,
            [
                {
                    "itemblock_id": str(block_nach_sitzung.pk),
                    "teilnahme_token": "2345-6789",
                    "item_id": str(freitext_item.pk),
                    "item_typ": "freitext",
                    "andockpunkt": "nach_sitzung",
                    "sitzung_id": str(sitzung.pk),
                    "position": "1",
                    "freitext": "Zeile eins\nZeile zwei",
                    "likert_stufe": "NA",
                },
                {
                    "itemblock_id": str(block_nach_sitzung.pk),
                    "teilnahme_token": "2345-6789",
                    "item_id": str(likert_item.pk),
                    "item_typ": "likert",
                    "andockpunkt": "nach_sitzung",
                    "sitzung_id": str(sitzung.pk),
                    "position": "2",
                    "freitext": "NA",
                    "likert_stufe": "5",
                },
                {
                    "itemblock_id": str(block_am_ende.pk),
                    "teilnahme_token": "2345-6789",
                    "item_id": str(freitext_item.pk),
                    "item_typ": "freitext",
                    "andockpunkt": "am_ende",
                    "sitzung_id": "NA",
                    "position": "1",
                    "freitext": "",
                    "likert_stufe": "NA",
                },
                {
                    "itemblock_id": str(block_am_ende.pk),
                    "teilnahme_token": "2345-6789",
                    "item_id": str(likert_item.pk),
                    "item_typ": "likert",
                    "andockpunkt": "am_ende",
                    "sitzung_id": "NA",
                    "position": "2",
                    "freitext": "NA",
                    "likert_stufe": "NA",
                },
            ],
        )
        # Vier Antwortzeilen, eine Abfrage: der Export zerfällt nicht in N+1.
        self.assertEqual(
            sum(
                1
                for abfrage in abfragen.captured_queries
                if "erhebungen_itemantwort" in abfrage["sql"]
            ),
            1,
        )

    def test_export_ist_eigentumsgebunden_und_auch_ohne_daten_wohlgeformt(self) -> None:
        """Entwürfe exportieren Kopfzeilen; fremde Erhebungen bleiben verborgen."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        grace: Konto = get_user_model().objects.create_user(username="grace")
        grace.groups.add(Group.objects.get(name="Forschende:r"))
        entwurf: Erhebung = Erhebung.objects.anlegen(ada, name="Leerer Entwurf")
        fremde_erhebung: Erhebung = Erhebung.objects.anlegen(
            grace, name="Fremde Erhebung"
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
        # Die Kopfzeile steht auch ohne Datenzeile; die Erhebung selbst und die
        # global festgelegte Likert-Kodierung hängen nicht am Datenbestand.
        zeilen_ohne_datenbestand: dict[str, int] = {
            "erhebung.csv": 2,
            "likert_skala.csv": 7,
        }
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
                "itembloecke.csv",
                "item_antworten.csv",
                "vignettenfassungen.csv",
                "simulationskerne.csv",
                "modellkonfigurationen.csv",
                "fragebogen_items.csv",
                "likert_skala.csv",
            ):
                with TextIOWrapper(
                    zip_datei.open(dateiname), encoding="utf-8"
                ) as csv_datei:
                    self.assertEqual(
                        len(list(csv.reader(csv_datei))),
                        zeilen_ohne_datenbestand.get(dateiname, 1),
                    )

    def test_exportiert_die_vorgelegten_items_mit_vollem_wortlaut(self) -> None:
        """Die Item-Tabelle macht den Fragebogen-Teil interpretierbar."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fragebogen")
        beidseitiges_item: FragebogenItem = _finales_item_anlegen(
            ada, "Zeile eins\nZeile zwei"
        )
        likert_item: FragebogenItem = FragebogenItem.objects.anlegen(
            ada, typ=FragebogenItem.Typ.LIKERT, wortlaut="Ich fühlte mich sicher."
        )
        likert_item.finalisieren()
        _finales_item_anlegen(ada, "Nicht zugeordnet")
        Erhebungsitem.objects.create(
            erhebung=erhebung,
            item=beidseitiges_item,
            andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
            position=1,
        )
        Erhebungsitem.objects.create(
            erhebung=erhebung,
            item=beidseitiges_item,
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
            position=1,
        )
        Erhebungsitem.objects.create(
            erhebung=erhebung,
            item=likert_item,
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
            position=2,
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            item_leser: csv.DictReader[str] = csv.DictReader(
                TextIOWrapper(zip_datei.open("fragebogen_items.csv"), encoding="utf-8")
            )
            items: list[dict[str, str]] = list(item_leser)
            kopfzeile: list[str] = list(item_leser.fieldnames or [])

        self.assertEqual(kopfzeile, ["id", "typ", "wortlaut"])
        self.assertEqual(
            items,
            [
                {
                    "id": str(beidseitiges_item.pk),
                    "typ": "freitext",
                    "wortlaut": "Zeile eins\nZeile zwei",
                },
                {
                    "id": str(likert_item.pk),
                    "typ": "likert",
                    "wortlaut": "Ich fühlte mich sicher.",
                },
            ],
        )

    def test_exportiert_die_kodierung_der_likert_skala(self) -> None:
        """Die Skalentabelle nennt zu jeder Stufe ihren Wortlaut."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fragebogen")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(response.content)) as zip_datei:
            skala_leser: csv.DictReader[str] = csv.DictReader(
                TextIOWrapper(zip_datei.open("likert_skala.csv"), encoding="utf-8")
            )
            stufen: list[dict[str, str]] = list(skala_leser)
            kopfzeile: list[str] = list(skala_leser.fieldnames or [])

        self.assertEqual(kopfzeile, ["stufe", "pol"])
        self.assertEqual(
            stufen,
            [
                {"stufe": "1", "pol": "Stimme gar nicht zu"},
                {"stufe": "2", "pol": "Stimme nicht zu"},
                {"stufe": "3", "pol": "Stimme eher nicht zu"},
                {"stufe": "4", "pol": "Stimme eher zu"},
                {"stufe": "5", "pol": "Stimme zu"},
                {"stufe": "6", "pol": "Stimme voll zu"},
            ],
        )

    def test_export_braucht_unabhaengig_von_der_itemzahl_gleich_viele_abfragen(
        self,
    ) -> None:
        """Die Item-Tabelle zerlegt den Export nicht in N+1-Abfragen."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fragebogen")
        for position in range(1, 4):
            Erhebungsitem.objects.create(
                erhebung=erhebung,
                item=_finales_item_anlegen(ada, f"Item {position}"),
                andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
                position=position,
            )
        self.client.force_login(ada)
        with CaptureQueriesContext(connection) as mit_drei_items:
            self.client.get(reverse("erhebungen:export", args=[erhebung.pk]))
        erhebung.itemzugehoerigkeiten.exclude(position=1).delete()
        with CaptureQueriesContext(connection) as mit_einem_item:
            self.client.get(reverse("erhebungen:export", args=[erhebung.pk]))

        self.assertEqual(len(mit_drei_items), len(mit_einem_item))

    def test_detail_zeigt_export_mit_stichprobe_auch_nach_archivierung(self) -> None:
        """Der Daten-Download folgt dem Datenbestand statt dem Erhebungsstatus."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration)
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Archiv")
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

    def test_die_dateiliste_folgt_dem_kontrakt_aus_adr_0029(self) -> None:
        """Der veröffentlichte Kontrakt nennt genau die gelieferten Dateien."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Kontrakt")
        self.client.force_login(ada)

        export: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        with ZipFile(BytesIO(export.content)) as zip_datei:
            self.assertEqual(
                sorted(zip_datei.namelist()), sorted(exportdateien_aus_adr_0029())
            )


class ErhebungenGesperrteItemzuordnungTests(TestCase):
    """Finale Erhebungen zeigen ihre Itemzuordnung ohne Änderungswege."""

    def test_finale_erhebung_zeigt_items_je_andockpunkt_ohne_bibliothek_oder_aktionen(
        self,
    ) -> None:
        """Das eingefrorene Design bleibt in seiner Reihenfolge lesbar."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        nach_sitzung_zwei: FragebogenItem = _finales_item_anlegen(
            ada, "Nach Sitzung zwei"
        )
        nach_sitzung_eins: FragebogenItem = _finales_item_anlegen(
            ada, "Nach Sitzung eins"
        )
        am_ende: FragebogenItem = _finales_item_anlegen(ada, "Am Ende")
        erste_bindung: Erhebungsitem = Erhebungsitem.objects.create(
            erhebung=erhebung,
            item=nach_sitzung_eins,
            andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
            position=1,
        )
        zweite_bindung: Erhebungsitem = Erhebungsitem.objects.create(
            erhebung=erhebung,
            item=nach_sitzung_zwei,
            andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
            position=2,
        )
        ende_bindung: Erhebungsitem = Erhebungsitem.objects.create(
            erhebung=erhebung,
            item=am_ende,
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
            position=1,
        )
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(sprachmodell="fake")
        )
        erhebung.finalisieren()
        self.client.force_login(ada)

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[erhebung.pk])
        )

        inhalt: str = detail.content.decode()
        self.assertContains(detail, "Nach jeder Vignettensitzung")
        self.assertContains(detail, "Am Ende")
        self.assertLess(
            inhalt.index("Nach Sitzung eins"), inhalt.index("Nach Sitzung zwei")
        )
        self.assertNotContains(detail, "Finale Items aufnehmen")
        for url in (
            reverse("erhebungen:item_entfernen", args=[erhebung.pk, erste_bindung.pk]),
            reverse("erhebungen:item_hoch", args=[erhebung.pk, zweite_bindung.pk]),
            reverse("erhebungen:item_runter", args=[erhebung.pk, erste_bindung.pk]),
            reverse("erhebungen:item_entfernen", args=[erhebung.pk, ende_bindung.pk]),
        ):
            self.assertNotContains(detail, url)

    def test_archivierte_erhebung_zeigt_leere_andockpunktbereiche_gesperrt(
        self,
    ) -> None:
        """Auch ohne Items bleibt die archivierte Zuordnung als leere Ansicht lesbar."""

        ada: Konto = get_user_model().objects.create_user(username="ada")
        ada.groups.add(Group.objects.get(name="Forschende:r"))
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(sprachmodell="fake")
        )
        erhebung.finalisieren()
        erhebung.archivieren()
        self.client.force_login(ada)

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[erhebung.pk])
        )

        self.assertContains(detail, "Nach jeder Vignettensitzung")
        self.assertContains(detail, "Am Ende")
        self.assertContains(detail, "Keine Fragebogen-Items aufgenommen.", count=2)
        self.assertNotContains(detail, "Finale Items aufnehmen")

"""HTTP-Tests für die Forschenden-UI der Erhebungen."""

import json
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.db import connection
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains, assertRedirects

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    finaler_kern,
    konto_mit_rollen,
)
from config.tests.exportkontrakt import exportkontrakt_aus_adr_0029
from config.tests.formular import submit_knoepfe
from erhebungen import urls as erhebungen_urls
from erhebungen.tests.aufbau import finale_erhebung, forschende
from erhebungen.tests.exportarchiv import export_kopfzeilen, export_lesen
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
from simulation.models import Anbieter, ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.models import (
    Diagnose,
    Eingabemodus,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
    Vignettenposition,
)
from sitzungen.durchlauf import gespraechsschritt_ausfuehren, sitzung_starten
from sitzungen.sink import FluechtigerSink
from training.models import Training, Trainingsbindung
from vignetten.models import Vignette


# Ein Zeitpunkt in Sommerzeit: Der Export schreibt ihn zwei Stunden früher in UTC.
_SOMMERZEIT: datetime = datetime(2026, 7, 1, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))


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
        bezeichnung="Test",
        anbieter=Anbieter.OPENROUTER,
        sprachmodell=f"openrouter/{name}",
        anbieter_token="sk-or-geheim",
        parameter=parameter or {},
    )


def _infomaniak_konfiguration() -> ModellKonfiguration:
    """Legt eine Konfiguration an, die Basis-URL und Token wirklich trägt."""

    return ModellKonfiguration.objects.create(
        bezeichnung="Mistral bei Infomaniak",
        anbieter=Anbieter.INFOMANIAK,
        sprachmodell="openai/mistral24b",
        anbieter_basis_url="https://api.infomaniak.com/1/ai/4711/openai",
        anbieter_token="sk-infomaniak-geheim",
        parameter={"temperature": 0.2},
    )


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


def _forschenden_routen() -> list[tuple[str, dict[str, object]]]:
    """Liefert Name und Platzhalter-Argumente jeder Route unter ``eigene/``."""

    return [
        (
            muster.name,
            {
                name: "am_ende" if name == "andockpunkt" else 1
                for name in muster.pattern.converters
            },
        )
        for muster in erhebungen_urls.urlpatterns
        if str(muster.pattern).startswith("eigene/") and muster.name
    ]


_FORSCHENDEN_ROUTEN: list[tuple[str, dict[str, object]]] = _forschenden_routen()
# Routen unter ``eigene/``, die GET annehmen; jede andere muss POST verlangen.
_LESEROUTEN: set[str] = {"liste", "anlegen", "detail", "export"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route", "argumente"), _FORSCHENDEN_ROUTEN, ids=[r for r, _ in _FORSCHENDEN_ROUTEN]
)
def test_anonymer_zugriff_fuehrt_auf_jeder_forschenden_route_zum_login(
    client: Client, route: str, argumente: dict[str, object]
) -> None:
    """Ohne Anmeldung gibt keine Route der Forschenden-UI etwas preis."""

    antwort: HttpResponse = client.get(reverse(f"erhebungen:{route}", kwargs=argumente))

    assert antwort.status_code == 302
    assert antwort["Location"].startswith("/accounts/login/?next=")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route", "argumente"), _FORSCHENDEN_ROUTEN, ids=[r for r, _ in _FORSCHENDEN_ROUTEN]
)
def test_konto_ohne_forschendenrolle_erhaelt_auf_alle_forschenden_views_403(
    client: Client, route: str, argumente: dict[str, object]
) -> None:
    """Die Erhebungs-UI ist von der öffentlichen Teilnahme getrennt geschützt."""

    client.force_login(konto_mit_rollen("grace"))
    # Jede Route mit der Methode, die sie annimmt: Leserouten per GET.
    anfragen = client.get if route in _LESEROUTEN else client.post

    antwort: HttpResponse = anfragen(reverse(f"erhebungen:{route}", kwargs=argumente))

    assert antwort.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route", "argumente"),
    [(r, a) for r, a in _FORSCHENDEN_ROUTEN if r not in _LESEROUTEN],
    ids=[r for r, _ in _FORSCHENDEN_ROUTEN if r not in _LESEROUTEN],
)
def test_schreibroute_nimmt_kein_get_an(
    client: Client, route: str, argumente: dict[str, object]
) -> None:
    """Ein Link oder Neuladen ändert nichts: Schreibrouten wollen POST."""

    client.force_login(forschende("ada"))

    antwort: HttpResponse = client.get(reverse(f"erhebungen:{route}", kwargs=argumente))

    assert antwort.status_code == 405


class ErhebungenAnlegenUndListeTests(TestCase):
    """Forschende verwalten ihre eigenen Entwürfe über die Liste."""

    def test_anlegen_erstellt_eigenen_entwurf_und_liste_versteckt_fremde(self) -> None:
        """Die Liste ist der sichtbare Einstieg für eigene Erhebungen."""
        ada: Konto = forschende("ada")
        grace: Konto = konto_mit_rollen("grace")
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

    def test_liste_traegt_bekannte_badge_klassen(self) -> None:
        """Jeder Status bildet auf eine im Stylesheet definierte Badge-Klasse ab."""

        ada: Konto = forschende("ada")
        Erhebung.objects.anlegen(ada, name="Noch Entwurf")
        finale_erhebung(ada, name="Schon final")
        finale_erhebung(ada, name="Längst abgelegt").archivieren()
        self.client.force_login(ada)

        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))

        self.assertContains(liste, "badge--draft")
        self.assertContains(liste, "badge--final")
        self.assertContains(liste, "badge--archived")

    def test_zeilen_sind_ueber_den_namen_verlinkt_und_nur_entwuerfe_haben_loeschknopf(
        self,
    ) -> None:
        """Der Name ist der Link der Zeile; nur Entwürfe tragen den Lösch-Icon-Knopf."""

        ada: Konto = forschende("ada")
        entwurf: Erhebung = Erhebung.objects.anlegen(ada, name="Noch Entwurf")
        finale: Erhebung = finale_erhebung(ada, name="Schon final")
        self.client.force_login(ada)

        liste: HttpResponse = self.client.get(reverse("erhebungen:liste"))

        self.assertContains(liste, "table--zeilenlink")
        for erhebung in (entwurf, finale):
            detail: str = reverse("erhebungen:detail", args=[erhebung.pk])
            self.assertContains(
                liste, f'<a class="zeilenlink" href="{detail}">{erhebung.name}</a>'
            )
        self.assertContains(liste, 'aria-label="Noch Entwurf löschen"')
        self.assertNotContains(liste, 'aria-label="Schon final löschen"')
        self.assertContains(liste, "zeilenaktion--gefahr", count=1)

    def test_liste_zeigt_kein_teilnahme_token_aus_der_browsersession(self) -> None:
        """Ein selbst getesteter Teilnahme-Link spielt kein Token in die Sidebar."""

        ada: Konto = forschende("ada")
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
        administratorin: Konto = konto_mit_rollen("linus", is_superuser=True)
        self.client.force_login(administratorin)

        angelegt: HttpResponse = self.client.post(
            reverse("erhebungen:anlegen"), {"name": "Brüche erforschen"}
        )

        erhebung: Erhebung = Erhebung.objects.get(eigentuemerinnen=administratorin)
        self.assertRedirects(angelegt, reverse("erhebungen:detail", args=[erhebung.pk]))

    def test_anlegen_speichert_den_namen_ohne_randleerzeichen(self) -> None:
        """Leerzeichen am Rand gehören nicht zum Namen der Erhebung."""
        ada: Konto = forschende("ada")
        self.client.force_login(ada)

        angelegt: HttpResponse = self.client.post(
            reverse("erhebungen:anlegen"), {"name": "  Brüche erforschen  "}
        )

        erhebung: Erhebung = Erhebung.objects.get(eigentuemerinnen=ada)
        self.assertEqual(erhebung.name, "Brüche erforschen")
        self.assertRedirects(angelegt, reverse("erhebungen:detail", args=[erhebung.pk]))

    def test_anlegen_lehnt_ungueltige_namen_mit_meldung_am_feld_ab(self) -> None:
        """Leere und zu lange Namen enden in einer Meldung statt im Serverfehler."""
        ada: Konto = forschende("ada")
        self.client.force_login(ada)

        for eingabe, meldung in (
            ("   ", "Bitte geben Sie einen Namen ein."),
            ("x" * 256, "Höchstens 255 Zeichen."),
        ):
            with self.subTest(eingabe=eingabe[:10]):
                abgelehnt: HttpResponse = self.client.post(
                    reverse("erhebungen:anlegen"), {"name": eingabe}
                )

                self.assertEqual(abgelehnt.status_code, 200)
                self.assertFalse(Erhebung.objects.filter(eigentuemerinnen=ada).exists())
                self.assertEqual(
                    abgelehnt.context["formular"]["name"].errors, [meldung]
                )
                self.assertContains(abgelehnt, meldung)

    def test_anlegen_laesst_die_eingabe_nach_einem_fehler_stehen(self) -> None:
        """Wer sich um ein Zeichen vertippt, muss den Namen nicht neu schreiben."""
        ada: Konto = forschende("ada")
        self.client.force_login(ada)
        zu_lang: str = "Brüche " + "x" * 250

        abgelehnt: HttpResponse = self.client.post(
            reverse("erhebungen:anlegen"), {"name": zu_lang}
        )

        self.assertContains(abgelehnt, f'value="{zu_lang}"')

    def test_anlegen_nennt_am_feld_wo_der_name_erscheint(self) -> None:
        """Der Hilfetext hängt per aria-describedby am Namensfeld."""
        ada: Konto = forschende("ada")
        self.client.force_login(ada)

        seite: HttpResponse = self.client.get(reverse("erhebungen:anlegen"))

        self.assertContains(
            seite,
            "Erscheint in Ihrer Erhebungsliste, im Dateinamen der Datenspur und "
            "in den Abschriften der Teilnehmenden.",
        )
        self.assertContains(seite, 'aria-describedby="id_name_helptext"')
        self.assertContains(seite, 'id="id_name_helptext"')


class ErhebungenSichtbarkeitUndLoeschenTests(TestCase):
    """Die Detail- und Lösch-URLs folgen der Eigentümersicht."""

    def setUp(self) -> None:
        """Legt eine Forschende mit einem Entwurf an."""
        self.ada: Konto = forschende("ada")
        self.entwurf: Erhebung = Erhebung.objects.anlegen(
            self.ada, name="Eigener Entwurf"
        )
        self.client.force_login(self.ada)

    def test_fremde_erhebung_ist_nicht_erreichbar(self) -> None:
        """Andere Eigentümerinnen erhalten keine Information über eine Erhebung."""
        grace: Konto = konto_mit_rollen("grace")
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

    def test_loeschen_trifft_nur_den_entwurf(self) -> None:
        """Die physische Löschaktion bleibt auf Entwürfe beschränkt."""
        finale: Erhebung = finale_erhebung(self.ada, name="Finale Erhebung")

        geloescht: HttpResponse = self.client.post(
            reverse("erhebungen:loeschen", args=[self.entwurf.pk])
        )
        abgewiesen: HttpResponse = self.client.post(
            reverse("erhebungen:loeschen", args=[finale.pk])
        )

        self.assertRedirects(geloescht, reverse("erhebungen:liste"))
        self.assertRedirects(abgewiesen, reverse("erhebungen:liste"))
        self.assertEqual(
            self.client.get(
                reverse("erhebungen:detail", args=[self.entwurf.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("erhebungen:detail", args=[finale.pk])).status_code,
            200,
        )


class ErhebungenKoForschendenViewTests(TestCase):
    """Forschende teilen Erhebungen mit gleichrangigen Ko-Forschenden."""

    def test_detail_nennt_die_erhebung(self) -> None:
        """Unterzeile und Erklärung sprechen von der Erhebung."""
        ada: Konto = forschende("ada")
        grace: Konto = forschende("grace")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Geteilte Erhebung")
        erhebung.eigentuemerinnen.add(grace)
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[erhebung.pk])
        )

        self.assertContains(response, "Wer diese Erhebung sehen und bearbeiten darf")
        self.assertContains(
            response,
            "Sie verlieren den Zugriff; die Erhebung bleibt bei den übrigen "
            "Eigentümer:innen.",
        )

    def test_hinzufuegen_gibt_ko_forschender_listen_und_detailzugriff(self) -> None:
        """Eine eingetragene Ko-Forschende findet und öffnet den Entwurf."""
        ada: Konto = forschende("ada")
        grace: Konto = forschende("grace")
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
        self.assertEqual(
            self.client.get(
                reverse("erhebungen:detail", args=[erhebung.pk])
            ).status_code,
            200,
        )

    def test_selbstentfernung_uebergibt_finale_und_laufende_erhebung(self) -> None:
        """Eine Forschende kann die Verantwortung auch im Erhebungszeitraum abgeben."""
        ada: Konto = forschende("ada")
        grace: Konto = forschende("grace")
        erhebung: Erhebung = finale_erhebung(ada, name="Laufende Erhebung")
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
        ada: Konto = forschende("ada")
        grace: Konto = forschende("grace")
        administratorin: Konto = konto_mit_rollen("linus", is_superuser=True)
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
        ada: Konto = forschende("ada")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Geschützte Erhebung")
        self.client.force_login(ada)

        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:eigentuemerin_entfernen", args=[erhebung.pk, ada.pk])
        )

        self.assertRedirects(antwort, reverse("erhebungen:detail", args=[erhebung.pk]))

    def test_teilen_laesst_nur_forschende_oder_administration_zu(self) -> None:
        """Das Eintragen vergibt keine Rolle und lässt Unberechtigte außen vor."""
        ada: Konto = forschende("ada")
        ohne_rolle: Konto = konto_mit_rollen("linus")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Geschützte Erhebung")
        self.client.force_login(ada)

        hinzufuegen: HttpResponse = self.client.post(
            reverse("erhebungen:eigentuemerin_hinzufuegen", args=[erhebung.pk]),
            {"konto": ohne_rolle.pk},
        )

        self.assertEqual(hinzufuegen.status_code, 404)
        self.assertFalse(erhebung.eigentuemerinnen.filter(pk=ohne_rolle.pk).exists())
        self.assertFalse(ohne_rolle.groups.exists())

    def test_teilen_mit_unlesbarem_konto_findet_niemanden(self) -> None:
        """Ein Konto-Feld ohne Zahl endet wie ein unbekanntes Konto, nicht im 500."""
        ada: Konto = forschende("ada")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Geteilte Erhebung")
        self.client.force_login(ada)

        hinzufuegen: HttpResponse = self.client.post(
            reverse("erhebungen:eigentuemerin_hinzufuegen", args=[erhebung.pk]),
            {"konto": "ada"},
        )

        self.assertEqual(hinzufuegen.status_code, 404)

    def test_administration_kann_fremde_erhebung_uebergeben(self) -> None:
        """Die Administration kann eine fremde Forschende durch eine andere ablösen."""
        grace: Konto = forschende("grace")
        ada: Konto = forschende("ada")
        administratorin: Konto = konto_mit_rollen("linus", is_superuser=True)
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

        self.ada: Konto = forschende("ada")
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
        self.eigene_finale: Vignette = finale_vignette(self.ada, fach="Mathematik")
        self.client.force_login(self.ada)

    def test_lehnt_fremde_und_unfertige_vignetten_ab(self) -> None:
        """Nur eigene finale Vignetten lassen sich in den Entwurf aufnehmen."""

        grace: Konto = konto_mit_rollen("grace")
        fremde_finale: Vignette = finale_vignette(grace, fach="Physik")
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
        self.assertEqual(
            [zeile["pk"] for zeile in aufgenommen.context["aufgenommene_daten"]],
            [self.eigene_finale.pk],
        )
        self.assertEqual(
            Erhebungsvignette.objects.get(erhebung=self.erhebung).position, 1
        )

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
            ),
            follow=True,
        )

        self.assertRedirects(
            aufnehmen, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
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
            ),
            follow=True,
        )
        self.assertRedirects(
            andere_bindung, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(
            Erhebungsitem.objects.filter(erhebung=self.erhebung).count(), 2
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
        """Verschieben ändert nur die Reihenfolge am eigenen Andockpunkt."""

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
                "erhebungen:item_verschieben",
                args=[self.erhebung.pk, zweite_zuordnung.pk],
            ),
            {"position": 1},
            follow=True,
        )

        self.assertRedirects(
            verschieben, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
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
            verschieben.context["nach_sitzung_aufgenommene_daten"][0][
                "verschieben_url"
            ],
            reverse(
                "erhebungen:item_verschieben",
                args=[self.erhebung.pk, zweite_zuordnung.pk],
            ),
        )

    def test_stellt_zuordnungszeilen_mit_ihren_aktions_urls_bereit(self) -> None:
        """Auswahl und Liste tragen ihre passenden Aktions-URLs."""

        verfuegbar: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(verfuegbar.context["aufgenommene_daten"], [])
        self.assertEqual(
            verfuegbar.context["verfuegbare_daten"],
            [
                {
                    "pk": self.eigene_finale.pk,
                    "label": self.eigene_finale.anzeigename,
                    "fach": "Mathematik",
                    "thema": self.eigene_finale.thema,
                    "einfuegen_url": reverse(
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
        zeile: dict[str, object] = aufgenommen.context["aufgenommene_daten"][0]
        self.assertEqual(
            zeile["entfernen_url"],
            reverse(
                "erhebungen:vignette_entfernen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            ),
        )
        self.assertEqual(
            zeile["verschieben_url"],
            reverse(
                "erhebungen:vignette_verschieben",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            ),
        )

    def test_haelt_fremde_und_unfertige_fassungen_aus_den_zeilen_heraus(self) -> None:
        """Die anbietende Spalte zeigt weder fremde noch nicht-finale Fassungen."""

        grace: Konto = konto_mit_rollen("grace")
        fremde_finale: Vignette = finale_vignette(grace, fach="Physik")
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

    def test_detailseite_traegt_bekannte_badge_klasse(self) -> None:
        """Die Detailseite nutzt die im Stylesheet definierte Badge-Klasse."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(detail, "badge--draft")

    def test_texte_erscheinen_gerendert_mit_bearbeiten_oder_text_schreiben(
        self,
    ) -> None:
        """Gefüllte Texte stehen gerendert zum Lesen, leere laden zum Schreiben ein."""

        self.erhebung.instruktionstext = "Bitte **genau** lesen."
        self.erhebung.save(update_fields=["instruktionstext"])

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(detail, "Bitte <strong>genau</strong> lesen.")
        self.assertContains(detail, "Noch kein Text", count=2)
        self.assertContains(detail, ">Text schreiben</button>", count=2)
        self.assertContains(detail, "Ganz anzeigen")
        self.assertContains(
            detail, '<textarea id="id_instruktionstext" name="instruktionstext"'
        )

    def test_jeder_speichern_knopf_speichert_die_ganze_erhebung(self) -> None:
        """Alle Speichern-Knöpfe senden dasselbe Formular mit allen Feldern."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        speichern: list[str | None] = [
            formular
            for beschriftung, formular in submit_knoepfe(detail)
            if "speichern" in beschriftung.lower()
        ]
        self.assertEqual(len(speichern), 3 + 1)
        self.assertEqual(set(speichern), {"erhebung-konfiguration"})

        gespeichert: HttpResponse = self.client.post(
            reverse("erhebungen:konfiguration_speichern", args=[self.erhebung.pk]),
            {
                "instruktionstext": "Neue *Instruktion*",
                "einwilligungstext": "Neue *Einwilligung*",
                "abschlusstext": "Neuer *Abschluss*",
            },
            follow=True,
        )

        for text in (
            "Neue <em>Instruktion</em>",
            "Neue <em>Einwilligung</em>",
            "Neuer <em>Abschluss</em>",
        ):
            self.assertContains(gespeichert, text)

    def test_seite_warnt_vor_dem_verlassen_mit_ungespeicherten_aenderungen(
        self,
    ) -> None:
        """Das Konfigurationsformular meldet sich für die Verlassen-Warnung an."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(detail, "js/ungespeichert.js")
        self.assertContains(detail, "data-ungespeichert-warnen")

    def _vignetten_aufnehmen(self, *vignetten: Vignette) -> None:
        """Nimmt Vignetten nacheinander am Ende der Liste auf."""

        for vignette in vignetten:
            self.client.post(
                reverse(
                    "erhebungen:vignette_hinzufuegen",
                    args=[self.erhebung.pk, vignette.pk],
                )
            )

    def _vignettenpositionen(self) -> list[tuple[int, int]]:
        """Liefert Vignette und Position der Liste in ihrer Reihenfolge."""

        return list(
            Erhebungsvignette.objects.filter(erhebung=self.erhebung).values_list(
                "vignette_id", "position"
            )
        )

    def _items_aufnehmen(self, andockpunkt: str, *items: FragebogenItem) -> None:
        """Nimmt Items nacheinander am Ende eines Andockpunkts auf."""

        for item in items:
            self.client.post(
                reverse(
                    "erhebungen:item_hinzufuegen",
                    args=[self.erhebung.pk, item.pk, andockpunkt],
                )
            )

    def test_verschiebt_vignette_an_eine_neue_position(self) -> None:
        """Die Liste ist die Reihenfolge; Verschieben schreibt die Positionen neu."""

        zweite: Vignette = finale_vignette(self.ada, fach="Chemie")
        self._vignetten_aufnehmen(self.eigene_finale, zweite)

        verschieben: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_verschieben",
                args=[self.erhebung.pk, zweite.pk],
            ),
            {"position": 1},
        )

        self.assertRedirects(
            verschieben, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(
            [zeile["pk"] for zeile in detail.context["aufgenommene_daten"]],
            [zweite.pk, self.eigene_finale.pk],
        )
        self.assertEqual(
            self._vignettenpositionen(),
            [(zweite.pk, 1), (self.eigene_finale.pk, 2)],
        )

    def test_verschieben_ohne_position_wird_abgelehnt(self) -> None:
        """Ohne Zielposition bleibt die Liste unverändert."""

        self._vignetten_aufnehmen(self.eigene_finale)

        antwort: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_verschieben",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            ),
            {"position": "oben"},
        )

        self.assertEqual(antwort.status_code, 400)

    def test_schalter_setzt_nur_die_reihenfolgeregel(self) -> None:
        """Der Schalter speichert die Regel sofort und zeigt sie der Liste an."""

        self._vignetten_aufnehmen(self.eigene_finale)

        zufaellig: HttpResponse = self.client.post(
            reverse("erhebungen:reihenfolge_umschalten", args=[self.erhebung.pk]),
            {"randomisierung": "zufällig"},
        )

        self.assertRedirects(
            zufaellig, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(detail, "Zufällige Reihenfolge")
        self.assertContains(
            detail,
            '<script id="randomisierung-daten" type="application/json">'
            '"zuf\\u00e4llig"</script>',
            html=False,
        )

    def test_umschalten_bewahrt_die_reihenfolge_hin_und_zurueck(self) -> None:
        """Die Regel wechselt, die festgelegte Reihenfolge bleibt erhalten."""

        zweite: Vignette = finale_vignette(self.ada, fach="Chemie")
        self._vignetten_aufnehmen(self.eigene_finale, zweite)
        self.client.post(
            reverse(
                "erhebungen:vignette_verschieben", args=[self.erhebung.pk, zweite.pk]
            ),
            {"position": 1},
        )
        erwartet: list[tuple[int, int]] = [(zweite.pk, 1), (self.eigene_finale.pk, 2)]

        for regel, json_wert in (("zufällig", '"zuf\\u00e4llig"'), ("fest", '"fest"')):
            detail: HttpResponse = self.client.post(
                reverse("erhebungen:reihenfolge_umschalten", args=[self.erhebung.pk]),
                {"randomisierung": regel},
                follow=True,
            )
            self.assertContains(
                detail,
                f'<script id="randomisierung-daten" type="application/json">'
                f"{json_wert}</script>",
            )
            self.assertEqual(self._vignettenpositionen(), erwartet)

    def test_umschalten_lehnt_unbekannte_regel_ab(self) -> None:
        """Nur die zwei bekannten Reihenfolgeregeln sind wählbar."""

        antwort: HttpResponse = self.client.post(
            reverse("erhebungen:reihenfolge_umschalten", args=[self.erhebung.pk]),
            {"randomisierung": "rückwärts"},
        )

        self.assertEqual(antwort.status_code, 400)

    def test_fuegt_vignette_an_gewuenschter_position_ein(self) -> None:
        """Eine neue Vignette landet an der gewählten Stelle der Liste."""

        zweite: Vignette = finale_vignette(self.ada, fach="Chemie")
        dritte: Vignette = finale_vignette(self.ada, fach="Physik")
        self._vignetten_aufnehmen(self.eigene_finale, zweite)

        self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen", args=[self.erhebung.pk, dritte.pk]
            ),
            {"position": 2},
        )

        self.assertEqual(
            self._vignettenpositionen(),
            [(self.eigene_finale.pk, 1), (dritte.pk, 2), (zweite.pk, 3)],
        )

    def test_entfernen_schliesst_die_vignettenreihenfolge_lueckenlos(self) -> None:
        """Nach dem Entfernen rücken die folgenden Vignetten nach."""

        zweite: Vignette = finale_vignette(self.ada, fach="Chemie")
        dritte: Vignette = finale_vignette(self.ada, fach="Physik")
        self._vignetten_aufnehmen(self.eigene_finale, zweite, dritte)
        self.client.post(
            reverse(
                "erhebungen:vignette_verschieben", args=[self.erhebung.pk, dritte.pk]
            ),
            {"position": 1},
        )

        self.client.post(
            reverse(
                "erhebungen:vignette_entfernen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )

        self.assertEqual(self._vignettenpositionen(), [(dritte.pk, 1), (zweite.pk, 2)])

    def test_fuegt_item_an_gewuenschter_position_ein(self) -> None:
        """Ein neues Item landet an der gewählten Stelle seines Andockpunkts."""

        erstes: FragebogenItem = _finales_item_anlegen(self.ada, "Erstes Item")
        zweites: FragebogenItem = _finales_item_anlegen(self.ada, "Zweites Item")
        self._items_aufnehmen(Erhebungsitem.Andockpunkt.AM_ENDE, erstes, zweites)
        neues: FragebogenItem = _finales_item_anlegen(self.ada, "Neues Item")

        einfuegen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_hinzufuegen",
                args=[self.erhebung.pk, neues.pk, Erhebungsitem.Andockpunkt.AM_ENDE],
            ),
            {"position": 1},
            follow=True,
        )

        self.assertEqual(
            [
                (zeile["pk"], zeile["position"])
                for zeile in einfuegen.context["am_ende_aufgenommene_daten"]
            ],
            [(neues.pk, 1), (erstes.pk, 2), (zweites.pk, 3)],
        )

    def test_haengt_item_an_den_anderen_andockpunkt_um(self) -> None:
        """Umhängen setzt das Item ans Ende des anderen Andockpunkts."""

        erstes: FragebogenItem = _finales_item_anlegen(self.ada, "Erstes Item")
        zweites: FragebogenItem = _finales_item_anlegen(self.ada, "Zweites Item")
        schon_am_ende: FragebogenItem = _finales_item_anlegen(self.ada, "Am Ende")
        self._items_aufnehmen(Erhebungsitem.Andockpunkt.NACH_SITZUNG, erstes, zweites)
        self._items_aufnehmen(Erhebungsitem.Andockpunkt.AM_ENDE, schon_am_ende)
        zuordnung: Erhebungsitem = Erhebungsitem.objects.get(
            erhebung=self.erhebung, item=erstes
        )

        umhaengen: HttpResponse = self.client.post(
            reverse("erhebungen:item_umhaengen", args=[self.erhebung.pk, zuordnung.pk]),
            follow=True,
        )

        self.assertRedirects(
            umhaengen, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(
            [
                (zeile["pk"], zeile["position"])
                for zeile in umhaengen.context["nach_sitzung_aufgenommene_daten"]
            ],
            [(zweites.pk, 1)],
        )
        self.assertEqual(
            [
                (zeile["pk"], zeile["position"])
                for zeile in umhaengen.context["am_ende_aufgenommene_daten"]
            ],
            [(schon_am_ende.pk, 1), (erstes.pk, 2)],
        )

    def test_umhaengen_lehnt_doppelte_bindung_ab(self) -> None:
        """Hängt ein Item schon am anderen Andockpunkt, gibt es kein Umhängen."""

        item: FragebogenItem = _finales_item_anlegen(self.ada, "Überall")
        for andockpunkt in Erhebungsitem.Andockpunkt.values:
            self._items_aufnehmen(andockpunkt, item)
        zuordnung: Erhebungsitem = Erhebungsitem.objects.get(
            erhebung=self.erhebung,
            item=item,
            andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertNotIn(
            "umhaengen_url", detail.context["nach_sitzung_aufgenommene_daten"][0]
        )
        umhaengen: HttpResponse = self.client.post(
            reverse("erhebungen:item_umhaengen", args=[self.erhebung.pk, zuordnung.pk])
        )
        self.assertEqual(umhaengen.status_code, 409)

    def test_entfernen_und_umhaengen_nach_umsortieren_gelingen(self) -> None:
        """Auch umsortierte Listen rücken beim Entfernen und Umhängen nach."""

        items: list[FragebogenItem] = [
            _finales_item_anlegen(self.ada, f"Item {nummer}") for nummer in range(4)
        ]
        self._items_aufnehmen(Erhebungsitem.Andockpunkt.AM_ENDE, *items)
        zuordnungen: list[Erhebungsitem] = [
            Erhebungsitem.objects.get(erhebung=self.erhebung, item=item)
            for item in items
        ]
        # Umgekehrte Reihenfolge: Die zuerst angelegten Zeilen stehen jetzt hinten.
        for zuordnung in zuordnungen[1:]:
            self.client.post(
                reverse(
                    "erhebungen:item_verschieben",
                    args=[self.erhebung.pk, zuordnung.pk],
                ),
                {"position": 1},
            )

        entfernen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_entfernen",
                args=[self.erhebung.pk, zuordnungen[3].pk],
            ),
            follow=True,
        )
        umhaengen: HttpResponse = self.client.post(
            reverse(
                "erhebungen:item_umhaengen",
                args=[self.erhebung.pk, zuordnungen[2].pk],
            ),
            follow=True,
        )

        self.assertRedirects(
            entfernen, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertRedirects(
            umhaengen, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertEqual(
            [
                (zeile["pk"], zeile["position"])
                for zeile in umhaengen.context["am_ende_aufgenommene_daten"]
            ],
            [(items[1].pk, 1), (items[0].pk, 2)],
        )
        self.assertEqual(
            [
                (zeile["pk"], zeile["position"])
                for zeile in umhaengen.context["nach_sitzung_aufgenommene_daten"]
            ],
            [(items[2].pk, 1)],
        )

    def test_zufaellige_reihenfolge_nimmt_am_ende_der_liste_auf(self) -> None:
        """Auch bei zufälliger Reihenfolge bekommt eine neue Vignette die letzte Position."""

        self.client.post(
            reverse("erhebungen:reihenfolge_umschalten", args=[self.erhebung.pk]),
            {"randomisierung": "zufällig"},
        )
        zweite: Vignette = finale_vignette(self.ada, fach="Chemie")
        dritte: Vignette = finale_vignette(self.ada, fach="Physik")
        for vignette in (self.eigene_finale, zweite):
            self.client.post(
                reverse(
                    "erhebungen:vignette_hinzufuegen",
                    args=[self.erhebung.pk, vignette.pk],
                )
            )
        self.client.post(
            reverse(
                "erhebungen:vignette_entfernen",
                args=[self.erhebung.pk, self.eigene_finale.pk],
            )
        )
        detail: HttpResponse = self.client.post(
            reverse(
                "erhebungen:vignette_hinzufuegen", args=[self.erhebung.pk, dritte.pk]
            ),
            follow=True,
        )

        self.assertEqual(
            [zeile["pk"] for zeile in detail.context["aufgenommene_daten"]],
            [zweite.pk, dritte.pk],
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("aufgenommen_an", "angeboten_an", "badge"),
    [
        pytest.param("am_ende", "nach_sitzung", "schon am Ende", id="am_ende"),
        pytest.param(
            "nach_sitzung", "am_ende", "schon nach jeder Sitzung", id="nach_sitzung"
        ),
    ],
)
def test_bibliothek_kennzeichnet_item_vom_anderen_andockpunkt(
    client: Client, aufgenommen_an: str, angeboten_an: str, badge: str
) -> None:
    """Ein Item am einen Andockpunkt bleibt am anderen angeboten, mit Badge."""

    ada: Konto = forschende("ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    item: FragebogenItem = _finales_item_anlegen(ada, "Wie sicher fühlten Sie sich?")
    client.force_login(ada)

    detail: HttpResponse = client.post(
        reverse(
            "erhebungen:item_hinzufuegen", args=[erhebung.pk, item.pk, aufgenommen_an]
        ),
        follow=True,
    )

    angeboten: dict[str, object] = detail.context[f"{angeboten_an}_verfuegbare_daten"][
        0
    ]
    assert angeboten["badge"] == badge
    assert angeboten["einfuegen_url"] == reverse(
        "erhebungen:item_hinzufuegen", args=[erhebung.pk, item.pk, angeboten_an]
    )


_KEIN_ENTWURF_MELDUNG: str = (
    "Die Erhebung ist kein Entwurf mehr. Es wurde nichts geändert."
)
_SCHREIBROUTEN: list[str] = [
    "vignette_hinzufuegen",
    "vignette_entfernen",
    "vignette_verschieben",
    "reihenfolge_umschalten",
    "item_hinzufuegen",
    "item_entfernen",
    "item_verschieben",
    "item_umhaengen",
    "konfiguration_speichern",
]


def _erhebung_mit_design(konto: Konto) -> Erhebung:
    """Legt einen Entwurf mit je zwei Vignetten und Items nach jeder Sitzung an."""

    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    for position, fach in enumerate(("Mathematik", "Chemie"), start=1):
        Erhebungsvignette.objects.create(
            erhebung=erhebung,
            vignette=finale_vignette(konto, fach=fach),
            position=position,
        )
    for position, wortlaut in enumerate(("Erstes Item", "Zweites Item"), start=1):
        _item_zuordnen(
            erhebung,
            _finales_item_anlegen(konto, wortlaut),
            Erhebungsitem.Andockpunkt.NACH_SITZUNG,
            position,
        )
    return erhebung


def _schreibaufruf(
    route: str, erhebung: Erhebung, konto: Konto
) -> tuple[str, dict[str, object]]:
    """Liefert URL und Formulardaten einer Aktion, die im Entwurf etwas änderte."""

    zweite_vignette: Vignette = erhebung.vignettenzugehoerigkeiten.get(
        position=2
    ).vignette
    zweite_zuordnung: Erhebungsitem = erhebung.itemzugehoerigkeiten.get(position=2)
    argumente: dict[str, list[object]] = {
        "vignette_hinzufuegen": [
            erhebung.pk,
            finale_vignette(konto, fach="Physik").pk,
        ],
        "vignette_entfernen": [erhebung.pk, zweite_vignette.pk],
        "vignette_verschieben": [erhebung.pk, zweite_vignette.pk],
        "reihenfolge_umschalten": [erhebung.pk],
        "item_hinzufuegen": [
            erhebung.pk,
            _finales_item_anlegen(konto, "Neues Item").pk,
            Erhebungsitem.Andockpunkt.AM_ENDE,
        ],
        "item_entfernen": [erhebung.pk, zweite_zuordnung.pk],
        "item_verschieben": [erhebung.pk, zweite_zuordnung.pk],
        "item_umhaengen": [erhebung.pk, zweite_zuordnung.pk],
        "konfiguration_speichern": [erhebung.pk],
    }
    daten: dict[str, object] = {
        "position": 1,
        "randomisierung": Erhebung.Randomisierung.ZUFAELLIG,
        "instruktionstext": "Nicht speichern",
    }
    return reverse(f"erhebungen:{route}", args=argumente[route]), daten


def _zeilen(antwort: HttpResponse) -> dict[str, object]:
    """Liest die Zeilen, die die Detailseite an die Zuordnungslisten gibt."""

    return {
        schluessel: antwort.context[schluessel]
        for schluessel in (
            "aufgenommene_daten",
            "nach_sitzung_aufgenommene_daten",
            "am_ende_aufgenommene_daten",
        )
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "badge"),
    [
        pytest.param(
            Erhebung.Status.FINAL,
            '<span class="badge badge--final">Final</span>',
            id="final",
        ),
        pytest.param(
            Erhebung.Status.ARCHIVIERT,
            '<span class="badge badge--archived">Archiviert</span>',
            id="archiviert",
        ),
    ],
)
@pytest.mark.parametrize("route", _SCHREIBROUTEN)
def test_schreibaktion_ausserhalb_des_entwurfs_leitet_mit_meldung_zurueck(
    client: Client, route: str, status: str, badge: str
) -> None:
    """Eine veraltete Schaltfläche führt auf die unveränderte Detailseite (ADR-0051)."""

    ada: Konto = forschende("ada")
    erhebung: Erhebung = _erhebung_mit_design(ada)
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung.finalisieren()
    if status == Erhebung.Status.ARCHIVIERT:
        erhebung.archivieren()
    client.force_login(ada)
    detail_url: str = reverse("erhebungen:detail", args=[erhebung.pk])
    url, daten = _schreibaufruf(route, erhebung, ada)
    vorher: HttpResponse = client.get(detail_url)

    antwort: HttpResponse = client.post(url, daten, follow=True)

    assertRedirects(antwort, detail_url)
    assertContains(antwort, _KEIN_ENTWURF_MELDUNG)
    assertContains(antwort, badge, html=True)
    assertContains(
        antwort,
        '<script id="randomisierung-daten" type="application/json">"fest"</script>',
        html=False,
    )
    assertNotContains(antwort, "Nicht speichern")
    assert _zeilen(antwort) == _zeilen(vorher)


@pytest.mark.django_db
@pytest.mark.parametrize("route", _SCHREIBROUTEN)
def test_schreibaktion_auf_fremder_erhebung_findet_nichts(
    client: Client, route: str
) -> None:
    """Wer die Erhebung nicht sehen darf, erfährt nicht, dass es sie gibt."""

    grace: Konto = forschende("grace")
    fremde: Erhebung = _erhebung_mit_design(grace)
    ada: Konto = forschende("ada")
    client.force_login(ada)
    # Neue Fassungen gehören ada: Das 404 kommt allein von der fremden Erhebung.
    url, daten = _schreibaufruf(route, fremde, ada)

    antwort: HttpResponse = client.post(url, daten)

    assert antwort.status_code == 404


@pytest.mark.django_db
def test_loeschen_ausserhalb_des_entwurfs_leitet_mit_meldung_auf_die_liste(
    client: Client,
) -> None:
    """Eine finale Erhebung bleibt in der Liste, die Meldung nennt den Grund."""

    ada: Konto = forschende("ada")
    erhebung: Erhebung = finale_erhebung(ada, name="Finale Erhebung")
    client.force_login(ada)

    antwort: HttpResponse = client.post(
        reverse("erhebungen:loeschen", args=[erhebung.pk]), follow=True
    )

    assertRedirects(antwort, reverse("erhebungen:liste"))
    assertContains(antwort, _KEIN_ENTWURF_MELDUNG)
    assertContains(antwort, reverse("erhebungen:detail", args=[erhebung.pk]))


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("route", _SCHREIBROUTEN)
def test_zweiter_tab_finalisiert_nicht_zwischen_statuspruefung_und_aenderung(
    client: Client, route: str
) -> None:
    """Statusprüfung und Änderung bilden eine Einheit, die kein Tab unterbricht.

    Der zweite Tab versucht zu finalisieren, sobald die Aktion die Erhebung
    gelesen hat. Er wartet nicht, damit der Test nicht hängt.
    """

    ada: Konto = forschende("ada")
    erhebung: Erhebung = _erhebung_mit_design(ada)
    client.force_login(ada)
    url, daten = _schreibaufruf(route, erhebung, ada)
    gelesen: list[str] = []
    zweiter_tab: list[str] = []

    def nach_dem_lesen_finalisieren(
        execute: Any, sql: str, params: Any, many: bool, context: dict[str, Any]
    ) -> Any:
        # Erst bei der nächsten Anweisung ist das Lesen abgeschlossen.
        if gelesen and not zweiter_tab:
            try:
                with sqlite3.connect(
                    str(connection.settings_dict["NAME"]), uri=True, timeout=0
                ) as zweite:
                    zweite.execute(
                        "UPDATE erhebungen_erhebung SET status = 'final' WHERE id = ?",
                        [erhebung.pk],
                    )
                zweiter_tab.append("finalisiert")
            except sqlite3.OperationalError:
                zweiter_tab.append("gesperrt")
        if 'FROM "erhebungen_erhebung"' in sql:
            gelesen.append(sql)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(nach_dem_lesen_finalisieren):
        client.post(url, daten)

    assert zweiter_tab == ["gesperrt"]


@pytest.mark.django_db
def test_vom_modell_abgewiesene_schreibaktion_leitet_mit_meldung_zurueck(
    client: Client,
) -> None:
    """Die Administration bindet keine eigene Vignette in eine fremde Erhebung ein."""

    grace: Konto = forschende("grace")
    fremde: Erhebung = Erhebung.objects.anlegen(grace, name="Fremd")
    administratorin: Konto = konto_mit_rollen("ada", is_superuser=True)
    client.force_login(administratorin)
    detail_url: str = reverse("erhebungen:detail", args=[fremde.pk])

    antwort: HttpResponse = client.post(
        reverse(
            "erhebungen:vignette_hinzufuegen",
            args=[fremde.pk, finale_vignette(administratorin).pk],
        ),
        follow=True,
    )

    assertRedirects(antwort, detail_url)
    assertContains(antwort, "Erhebungen können nur eigene Vignetten einbinden.")
    assert antwort.context["aufgenommene_daten"] == []


class ErhebungsansichtAnbieterTests(TestCase):
    """Die gelbe Ansicht zeigt genau die Exportspalten der Konfiguration."""

    def setUp(self) -> None:
        # Pinnt eine Infomaniak-Konfiguration an eine finale Erhebung.

        self.ada: Konto = forschende("ada")
        self.konfiguration: ModellKonfiguration = _infomaniak_konfiguration()
        ModellKonfiguration.objects.aktivieren(
            self.konfiguration, Verwendung.SCHUELERIN
        )
        self.erhebung: Erhebung = finale_erhebung(self.ada)
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

        self.ada: Konto = forschende("ada")
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
        self.konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(
            self.konfiguration, Verwendung.SCHUELERIN
        )
        self.client.force_login(self.ada)

    def test_finalisieren_sperrt_design_und_zeigt_gepinnte_konfiguration(self) -> None:
        """Die Detailseite zeigt den finalen, gepinnten Zustand statt Editoren."""

        response: HttpResponse = self.client.post(
            reverse("erhebungen:finalisieren", args=[self.erhebung.pk]), follow=True
        )

        self.assertContains(
            response, '<span class="badge badge--final">Final</span>', html=True
        )
        self.assertContains(response, "openrouter/forschung")
        self.assertNotContains(response, "Konfiguration speichern")
        self.assertNotContains(response, "zuordnungsliste__einfuegen")

    def test_finalisieren_speichert_vorher_alle_felder(self) -> None:
        """Offene Texte und übrige Felder gehen beim Finalisieren nicht verloren."""

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertIn(
            ("Finalisieren", "erhebung-konfiguration"), submit_knoepfe(detail)
        )

        finalisiert: HttpResponse = self.client.post(
            reverse("erhebungen:finalisieren", args=[self.erhebung.pk]),
            {
                "instruktionstext": "Offene *Instruktion*",
                "einwilligungstext": "Offene *Einwilligung*",
                "abschlusstext": "Offener *Abschluss*",
            },
            follow=True,
        )

        self.assertContains(
            finalisiert, '<span class="badge badge--final">Final</span>', html=True
        )
        for text in (
            "Offene <em>Instruktion</em>",
            "Offene <em>Einwilligung</em>",
            "Offener <em>Abschluss</em>",
        ):
            self.assertContains(finalisiert, text)

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

        self.ada: Konto = forschende("ada")
        self.erhebung: Erhebung = finale_erhebung(self.ada)
        self.client.force_login(self.ada)

    def test_legt_stichprobe_mit_zeitraum_und_teilnahme_link_an(self) -> None:
        """Die Detailseite erzeugt den öffentlichen Link für den eingegebenen Zeitraum."""

        anlegen: HttpResponse = self.client.post(
            reverse("erhebungen:stichprobe_anlegen", args=[self.erhebung.pk]),
            {"beginn": "2026-08-01T09:00", "ende": "2026-08-31T17:00"},
            follow=True,
        )

        stichprobe: Stichprobe = Stichprobe.objects.get(erhebung=self.erhebung)
        self.assertRedirects(
            anlegen, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(
            anlegen,
            f"http://testserver/erhebungen/teilnahme/{stichprobe.teilnahme_link}/",
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
        self.assertContains(detail, "<td>Läuft</td>")
        self.assertContains(detail, '<th scope="col">Teilnahmen</th>')
        self.assertContains(detail, "<td>1</td>")

    def test_zaehlt_abgelehnte_sprachmodelle_und_speicherung_je_stichprobe(
        self,
    ) -> None:
        """Die Detailseite zeigt, wie viele a bzw. c nach aktuellem Stand ablehnen."""

        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        einwilligungen: list[tuple[bool | None, bool | None]] = [
            (False, None),
            (True, False),
            (True, False),
            (True, True),
            (None, None),
        ]
        for nummer, (sprachmodell, speicherung) in enumerate(einwilligungen):
            Erhebungsbindung.objects.create(
                stichprobe=stichprobe,
                teilnahme=Teilnahme.objects.create(
                    sprachmodell_eingewilligt=sprachmodell,
                    speicherung_eingewilligt=speicherung,
                ),
                token=f"2345-678{nummer}",
            )

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )

        self.assertContains(
            detail, '<th scope="col">Sprachmodelle abgelehnt</th>', html=True
        )
        self.assertContains(detail, '<th scope="col">Ohne Speicherung</th>', html=True)
        self.assertContains(detail, "<td>5</td><td>1</td><td>2</td>", html=True)

    def test_zeichnet_archivierte_stichproben_in_der_phasenspalte_aus(self) -> None:
        """Eine archivierte Stichprobe trägt ihren Zustand neben der Phase."""

        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=2),
            ende=timezone.now() - timedelta(days=1),
        )

        offen: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertNotContains(offen, "Archiviert<")

        stichprobe.archivieren()

        archiviert: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(
            archiviert,
            '<td>Abgeschlossen <span class="badge badge--archived">Archiviert</span></td>',
            html=True,
        )

    def test_laesst_stichproben_nur_auf_eigenen_finalen_erhebungen_an(self) -> None:
        """Entwürfe und fremde Erhebungen erhalten keine anlegbare Stichprobe."""

        entwurf: Erhebung = Erhebung.objects.anlegen(self.ada, name="Entwurf")
        grace: Konto = konto_mit_rollen("grace")
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

        self.ada: Konto = forschende("ada")
        self.erhebung: Erhebung = finale_erhebung(self.ada)
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
        archivieren: HttpResponse = self.client.post(archivieren_url, follow=True)

        self.assertContains(detail, archivieren_url)
        self.assertRedirects(
            archivieren, reverse("erhebungen:detail", args=[self.erhebung.pk])
        )
        self.assertContains(
            archivieren,
            '<td>Abgeschlossen <span class="badge badge--archived">Archiviert</span></td>',
            html=True,
        )

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
        self.assertNotContains(archivieren, "badge--archived")

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
        self.assertContains(
            archivieren,
            '<span class="badge badge--archived">Archiviert</span>',
            html=True,
        )
        self.assertContains(archivieren, entarchivieren_url)
        self.assertContains(
            entarchivieren, '<span class="badge badge--final">Final</span>', html=True
        )
        self.assertContains(entarchivieren, archivieren_url)

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
        self.assertContains(
            archivieren, '<span class="badge badge--final">Final</span>', html=True
        )

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
        self.assertContains(
            entarchivieren,
            '<span class="badge badge--archived">Archiviert</span>',
            html=True,
        )


class ErhebungsExportTests(TestCase):
    """Forschende laden die minimale relationale Datenspur als ZIP herunter."""

    def test_exportiert_erhebung_stichprobe_und_teilnahme_als_csvs(self) -> None:
        """Das ZIP bewahrt Freitext, NULL und Zeitstempel im festgelegten Format."""

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(
            ada,
            name="Brüche & Zahlen",
            instruktionstext="Zeile eins\nZeile zwei",
            einwilligungstext="",
        )
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=datetime(2026, 7, 1, 8, tzinfo=timezone.UTC),
            ende=datetime(2026, 7, 31, 17, tzinfo=timezone.UTC),
        )
        bindung: Erhebungsbindung = Erhebungsbindung.objects.create(
            stichprobe=stichprobe,
            teilnahme=Teilnahme.objects.create(
                sprachmodell_eingewilligt=True, speicherung_eingewilligt=False
            ),
            token="2345-6789",
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        archiv: dict[str, list[dict[str, str]]] = export_lesen(response)
        [erhebungszeile] = archiv["erhebung.csv"]
        [stichprobenzeile] = archiv["stichproben.csv"]
        [teilnahmezeile] = archiv["teilnahmen.csv"]

        self.assertEqual(erhebungszeile["instruktionstext"], "Zeile eins\nZeile zwei")
        self.assertEqual(erhebungszeile["einwilligungstext"], "")
        self.assertEqual(
            erhebungszeile["modell_konfiguration_id"], str(konfiguration.pk)
        )
        self.assertEqual(stichprobenzeile["id"], str(stichprobe.pk))
        self.assertEqual(stichprobenzeile["beginn"], "2026-07-01T08:00:00+00:00")
        self.assertEqual(teilnahmezeile["token"], bindung.token)
        self.assertEqual(teilnahmezeile["sprachmodell_eingewilligt"], "True")
        self.assertEqual(teilnahmezeile["audioverarbeitung_eingewilligt"], "NA")
        self.assertEqual(teilnahmezeile["speicherung_eingewilligt"], "False")
        self.assertRegex(
            teilnahmezeile["erstellt_am"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$",
        )

    def test_exportiert_nur_referenzierte_fassungen_mit_vollem_inhalt(self) -> None:
        """Fassungstabellen machen die exportierte Datenspur selbsttragend."""

        ada: Konto = forschende("ada")
        erste_konfiguration: ModellKonfiguration = _forschungskonfiguration(
            "erstes-modell", parameter={"temperature": 0.2}
        )
        ModellKonfiguration.objects.aktivieren(
            erste_konfiguration, Verwendung.SCHUELERIN
        )
        erhebung: Erhebung = finale_erhebung(ada, name="Brüche")
        zweite_konfiguration: ModellKonfiguration = _forschungskonfiguration(
            "zweites-modell", parameter={"temperature": 0.7}
        )
        # Weder gepinnt noch gespielt: fehlt in der Konfigurationstabelle.
        _forschungskonfiguration("nicht-exportieren")
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
        with time_machine.travel(_SOMMERZEIT, tick=False):
            zweiter_kern.finalisieren()
        erste_vignette: Vignette = finale_vignette(ada, fach="Mathematik")
        erste_vignette = erste_vignette.bearbeiten()
        erste_vignette.lernauftrag_text = (
            "Addiere **die** Brüche.\n[bild]\n- [Tipp](https://x.org)"
        )
        erste_vignette.lernauftrag_bild = "vignettenbilder/lernauftrag.png"
        erste_vignette.lernauftrag_bildbeschreibung = "Ein Bruch-Arbeitsblatt"
        erste_vignette.lernauftrag_simulationshinweise = "Hinweis zum Lernauftrag"
        erste_vignette.arbeitsheft_simulationshinweise = "Hinweis zum Arbeitsheft"
        erste_vignette.save()
        erste_vignette.finalisieren()
        zweite_vignette: Vignette = erste_vignette.bearbeiten()
        zweite_vignette.arbeitsheft_text = "1/2 + [bild] 1/3\n\\= 2/5 \\_"
        zweite_vignette.arbeitsheft_bild = "vignettenbilder/bruchbild.png"
        zweite_vignette.arbeitsheft_bildbeschreibung = (
            "Bildbeschreibung des Arbeitshefts"
        )
        zweite_vignette.referenzdiagnose = "Mehrzeilige\nReferenzdiagnose"
        zweite_vignette.save()
        zweite_vignette.finalisieren()
        # Weder gezogen noch gespielt: fehlt in der Fassungstabelle.
        finale_vignette(ada, fach="Physik")
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

        archiv: dict[str, list[dict[str, str]]] = export_lesen(response)
        vignetten: list[dict[str, str]] = archiv["vignettenfassungen.csv"]
        kerne: list[dict[str, str]] = archiv["simulationskerne.csv"]
        konfigurationen: list[dict[str, str]] = archiv["modellkonfigurationen.csv"]

        vignetten_nach_id: dict[str, dict[str, str]] = {
            vignette["id"]: vignette for vignette in vignetten
        }
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
            "Addiere **die** Brüche.\n[bild]\n- [Tipp](https://x.org)",
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
            "1/2 + [bild] 1/3\n\\= 2/5 \\_",
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
        self.assertEqual(
            kerne,
            [
                {
                    "id": str(zweiter_kern.pk),
                    "historie_id": str(zweiter_kern.historie_id),
                    "finalisiert_am": "2026-07-01T08:00:00+00:00",
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

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _infomaniak_konfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(ada, name="Brüche")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        archiv: dict[str, list[dict[str, str]]] = export_lesen(response)
        konfigurationen: list[dict[str, str]] = archiv["modellkonfigurationen.csv"]
        archivinhalt: str = "\n".join(
            wert
            for zeilen in archiv.values()
            for zeile in zeilen
            for wert in zeile.values()
        )

        self.assertEqual(
            konfigurationen,
            [
                {
                    "id": str(konfiguration.pk),
                    "bezeichnung": "Mistral bei Infomaniak",
                    "anbieter": "infomaniak",
                    "sprachmodell": "openai/mistral24b",
                    "parameter": '{"temperature": 0.2}',
                }
            ],
        )
        self.assertNotIn(konfiguration.anbieter_token, archivinhalt)
        self.assertNotIn(konfiguration.anbieter_basis_url, archivinhalt)

    def test_exportiert_ziehungen_und_alle_erhebungssitzungen(self) -> None:
        """Die Ziehung zeigt den Plan, Sitzungen zeigen jeden tatsächlichen Ausgang."""

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(ada, name="Brüche")
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        kern: Simulationskern = finaler_kern()
        vignette: Vignette = finale_vignette(ada, fach="Mathematik")
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
        status_je_bindung: list[tuple[Erhebungsbindung, str]] = list(
            zip(
                bindungen[:4],
                ("laufend", "abgeschlossen", "abgebrochen", "gescheitert"),
                strict=True,
            )
        )
        for bindung, status in status_je_bindung:
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

        archiv: dict[str, list[dict[str, str]]] = export_lesen(response)
        ziehungen: list[dict[str, str]] = archiv["vignettenziehungen.csv"]
        sitzungen: list[dict[str, str]] = archiv["sitzungen.csv"]

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
                    for bindung, status in status_je_bindung
                },
            },
        )

    def test_exportiert_die_verbrauchte_zeit_in_sekunden(self) -> None:
        """Die verbrauchte Zeit ist Datenspur (ADR-0012)."""

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(ada, name="Brüche")
        kern: Simulationskern = finaler_kern()
        zeitvignette: Vignette = finale_vignette(
            ada, fach="Mathematik", budget_typ=Vignette.BudgetTyp.ZEIT, budget_wert=600
        )
        schrittvignette: Vignette = finale_vignette(ada, fach="Physik")
        for token, vignette, verbraucht in (
            ("2345-6781", zeitvignette, 417.5),
            ("2345-6782", schrittvignette, 0.0),
        ):
            bindung: Erhebungsbindung = _laufende_bindung(erhebung, token)
            sitzung: Sitzung = Sitzung.objects.create(
                teilnahme=bindung.teilnahme,
                vignette=vignette,
                simulationskern=kern,
                modell_konfiguration=konfiguration,
                verbrauchte_zeit=verbraucht,
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

        self.assertEqual(
            {
                zeile["vignette_id"]: zeile["verbrauchte_zeit"]
                for zeile in export_lesen(response)["sitzungen.csv"]
            },
            {str(zeitvignette.pk): "417.5", str(schrittvignette.pk): "0.0"},
        )

    def test_exportiert_fluechtige_teilnahme_mit_geruest_ohne_inhaltszeilen(
        self,
    ) -> None:
        """Die flüchtige Teilnahme erscheint mit Sitzung, Uhr und Status, ohne Inhalte."""

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"fehler": "formatbruch", "rohantwort": "Kein JSON."},
                    {"denkspur": "Meine Regel.", "aeusserung": "2/5."},
                ]
            },
        )
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(ada, name="Brüche")
        kern: Simulationskern = finaler_kern()
        vignette: Vignette = finale_vignette(
            ada, fach="Mathematik", budget_typ=Vignette.BudgetTyp.ZEIT, budget_wert=600
        )
        bindung: Erhebungsbindung = _laufende_bindung(erhebung, "2345-6789")
        bindung.teilnahme.speicherung_eingewilligt = False
        bindung.teilnahme.save(update_fields=["speicherung_eingewilligt"])
        sink: FluechtigerSink = FluechtigerSink(bindung.teilnahme, {})
        sitzung_starten(sink, vignette, konfiguration, simulationskern=kern)
        Vignettenposition.objects.create(
            teilnahme=bindung.teilnahme,
            sitzung=sink.sitzung,
            vignette=vignette,
            position=1,
        )
        sink.zug_beginnen(datetime(2026, 9, 22, 10, 0, tzinfo=UTC))
        sink.zug_beenden(datetime(2026, 9, 22, 10, 0, 4, tzinfo=UTC))
        gespraechsschritt_ausfuehren(
            sink, vignette, kern, konfiguration, eingabe="Warum?"
        )
        sink.diagnose_setzen("Bruchfehler")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        archiv: dict[str, list[dict[str, str]]] = export_lesen(response)
        teilnahmen: list[dict[str, str]] = archiv["teilnahmen.csv"]
        sitzungen: list[dict[str, str]] = archiv["sitzungen.csv"]
        inhalte: dict[str, list[dict[str, str]]] = {
            name: archiv[name]
            for name in ("gespraechsschritte.csv", "fehlversuche.csv", "diagnosen.csv")
        }

        self.assertEqual(
            [
                (zeile["token"], zeile["speicherung_eingewilligt"])
                for zeile in teilnahmen
            ],
            [("2345-6789", "False")],
        )
        self.assertEqual(
            [
                (zeile["token"], zeile["status"], zeile["verbrauchte_zeit"])
                for zeile in sitzungen
            ],
            [("2345-6789", "abgeschlossen", "4.0")],
        )
        self.assertEqual(inhalte, {name: [] for name in inhalte})

    def test_exportiert_gespraechsschritte_fehlversuche_und_diagnosen(self) -> None:
        """Der Export bewahrt die vollständige Datenspur einschließlich Abbrüchen."""

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(ada, name="Brüche")
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
        kern: Simulationskern = finaler_kern()
        vignette: Vignette = finale_vignette(ada, fach="Mathematik")
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

        archiv: dict[str, list[dict[str, str]]] = export_lesen(response)
        schritte: list[dict[str, str]] = archiv["gespraechsschritte.csv"]
        fehlversuche: list[dict[str, str]] = archiv["fehlversuche.csv"]
        diagnosen: list[dict[str, str]] = archiv["diagnosen.csv"]

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

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(ada, name="Brüche")
        kern: Simulationskern = finaler_kern()
        vignette: Vignette = finale_vignette(ada, fach="Mathematik")
        bindungen: list[Erhebungsbindung] = [
            _laufende_bindung(erhebung, f"2345-678{nummer}") for nummer in range(1, 3)
        ]
        bloecke: list[Itemblock] = []
        with time_machine.travel(_SOMMERZEIT, tick=False):
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
                        erledigt_am=_SOMMERZEIT + timedelta(minutes=5),
                    )
                )
                bloecke.append(
                    Itemblock.objects.create(
                        erhebungsbindung=bindung,
                        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
                    )
                )
        fremde_erhebung: Erhebung = finale_erhebung(ada, name="Fremd")
        Itemblock.objects.create(
            erhebungsbindung=_laufende_bindung(fremde_erhebung, "9999-9999"),
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertEqual(
            export_lesen(response)["itembloecke.csv"],
            [
                {
                    "id": str(bloecke[0].pk),
                    "teilnahme_token": "2345-6781",
                    "andockpunkt": "nach_sitzung",
                    "sitzung_id": str(bloecke[0].sitzung_id),
                    "vorgelegt_am": "2026-07-01T08:00:00+00:00",
                    "erledigt_am": "2026-07-01T08:05:00+00:00",
                },
                {
                    "id": str(bloecke[1].pk),
                    "teilnahme_token": "2345-6781",
                    "andockpunkt": "am_ende",
                    "sitzung_id": "NA",
                    "vorgelegt_am": "2026-07-01T08:00:00+00:00",
                    "erledigt_am": "NA",
                },
                {
                    "id": str(bloecke[2].pk),
                    "teilnahme_token": "2345-6782",
                    "andockpunkt": "nach_sitzung",
                    "sitzung_id": str(bloecke[2].sitzung_id),
                    "vorgelegt_am": "2026-07-01T08:00:00+00:00",
                    "erledigt_am": "2026-07-01T08:05:00+00:00",
                },
                {
                    "id": str(bloecke[3].pk),
                    "teilnahme_token": "2345-6782",
                    "andockpunkt": "am_ende",
                    "sitzung_id": "NA",
                    "vorgelegt_am": "2026-07-01T08:00:00+00:00",
                    "erledigt_am": "NA",
                },
            ],
        )

    def test_exportiert_item_antworten_mit_erhaltener_null_semantik(self) -> None:
        """Die Antwortdatei trennt »nicht beantwortet« von »leer abgeschickt«."""

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
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
        kern: Simulationskern = finaler_kern()
        vignette: Vignette = finale_vignette(ada, fach="Mathematik")
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

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertEqual(
            export_lesen(response)["item_antworten.csv"],
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

    def test_export_ist_eigentumsgebunden_und_auch_ohne_daten_wohlgeformt(self) -> None:
        """Entwürfe exportieren Kopfzeilen; fremde Erhebungen bleiben verborgen."""

        ada: Konto = forschende("ada")
        grace: Konto = forschende("grace")
        entwurf: Erhebung = Erhebung.objects.anlegen(ada, name="Leerer Entwurf")
        fremde_erhebung: Erhebung = Erhebung.objects.anlegen(
            grace, name="Fremde Erhebung"
        )
        self.client.force_login(ada)

        detail_ohne_stichprobe: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[entwurf.pk])
        )
        with time_machine.travel(_SOMMERZEIT, tick=False):
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
        self.assertEqual(
            export["Content-Disposition"],
            f'attachment; filename="erhebung-{entwurf.pk}-leerer-entwurf-'
            '20260701T080000Z.zip"',
        )
        # Die Erhebung selbst und die global festgelegte Likert-Kodierung hängen
        # nicht am Datenbestand; jede andere Datei bleibt ohne Datenzeile.
        zeilenzahlen: dict[str, int] = {
            dateiname: len(zeilen) for dateiname, zeilen in export_lesen(export).items()
        }
        self.assertEqual(
            zeilenzahlen,
            {
                dateiname: {"erhebung.csv": 1, "likert_skala.csv": 6}.get(dateiname, 0)
                for dateiname in zeilenzahlen
            },
        )

    def test_exportiert_die_vorgelegten_items_mit_vollem_wortlaut(self) -> None:
        """Die Item-Tabelle macht den Fragebogen-Teil interpretierbar."""

        ada: Konto = forschende("ada")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fragebogen")
        beidseitiges_item: FragebogenItem = _finales_item_anlegen(
            ada, "Zeile eins\nZeile zwei"
        )
        likert_item: FragebogenItem = FragebogenItem.objects.anlegen(
            ada, typ=FragebogenItem.Typ.LIKERT, wortlaut="Ich fühlte mich sicher."
        )
        likert_item.finalisieren()
        _finales_item_anlegen(ada, "Nicht zugeordnet")
        nie_vorgelegtes_item: FragebogenItem = _finales_item_anlegen(
            ada, "Zugeordnet, aber nie vorgelegt"
        )
        _item_zuordnen(
            erhebung, beidseitiges_item, Erhebungsitem.Andockpunkt.NACH_SITZUNG, 1
        )
        beidseitig_am_ende: Erhebungsitem = _item_zuordnen(
            erhebung, beidseitiges_item, Erhebungsitem.Andockpunkt.AM_ENDE, 1
        )
        likert_am_ende: Erhebungsitem = _item_zuordnen(
            erhebung, likert_item, Erhebungsitem.Andockpunkt.AM_ENDE, 2
        )
        _item_zuordnen(
            erhebung, nie_vorgelegtes_item, Erhebungsitem.Andockpunkt.NACH_SITZUNG, 2
        )
        bindung: Erhebungsbindung = _laufende_bindung(erhebung, "2345-6789")
        block_am_ende: Itemblock = Itemblock.objects.create(
            erhebungsbindung=bindung, andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE
        )
        # Eine unbeantwortete Antwortzeile genügt: vorgelegt ist, was eine Zeile hat.
        for zuordnung in (beidseitig_am_ende, likert_am_ende):
            ItemAntwort.objects.create(
                itemblock=block_am_ende,
                erhebungsbindung=bindung,
                erhebungsitem=zuordnung,
            )
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertEqual(
            export_lesen(response)["fragebogen_items.csv"],
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

        ada: Konto = forschende("ada")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Fragebogen")
        self.client.force_login(ada)

        response: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertEqual(
            export_lesen(response)["likert_skala.csv"],
            [
                {"stufe": "1", "pol": "Stimme gar nicht zu"},
                {"stufe": "2", "pol": "Stimme nicht zu"},
                {"stufe": "3", "pol": "Stimme eher nicht zu"},
                {"stufe": "4", "pol": "Stimme eher zu"},
                {"stufe": "5", "pol": "Stimme zu"},
                {"stufe": "6", "pol": "Stimme voll zu"},
            ],
        )

    def test_export_braucht_unabhaengig_vom_datenbestand_gleich_viele_abfragen(
        self,
    ) -> None:
        """Items, Bindungen und Itemblöcke zerlegen den Export nicht in N+1-Abfragen."""

        ada: Konto = forschende("ada")
        self.client.force_login(ada)

        def abfragen_beim_export(anzahl: int) -> int:
            # Je eine Bindung mit einem Block, der jedes der Items beantwortet.

            erhebung: Erhebung = Erhebung.objects.anlegen(ada, name=f"{anzahl} Items")
            zuordnungen: list[Erhebungsitem] = [
                _item_zuordnen(
                    erhebung,
                    _finales_item_anlegen(ada, f"Item {position} von {anzahl}"),
                    Erhebungsitem.Andockpunkt.AM_ENDE,
                    position,
                )
                for position in range(1, anzahl + 1)
            ]
            for nummer in range(anzahl):
                bindung: Erhebungsbindung = _laufende_bindung(
                    erhebung, f"{anzahl}{nummer}00-0000"
                )
                block: Itemblock = Itemblock.objects.create(
                    erhebungsbindung=bindung,
                    andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
                )
                for zuordnung in zuordnungen:
                    ItemAntwort.objects.create(
                        itemblock=block,
                        erhebungsbindung=bindung,
                        erhebungsitem=zuordnung,
                    )
            with CaptureQueriesContext(connection) as abfragen:
                self.client.get(reverse("erhebungen:export", args=[erhebung.pk]))
            return len(abfragen)

        self.assertEqual(abfragen_beim_export(3), abfragen_beim_export(1))

    def test_detail_zeigt_export_mit_stichprobe_auch_nach_archivierung(self) -> None:
        """Der Daten-Download folgt dem Datenbestand statt dem Erhebungsstatus."""

        ada: Konto = forschende("ada")
        konfiguration: ModellKonfiguration = _forschungskonfiguration()
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
        erhebung: Erhebung = finale_erhebung(ada, name="Archiv")
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

    def test_dateien_und_spalten_folgen_dem_kontrakt_aus_adr_0029(self) -> None:
        """Der veröffentlichte Kontrakt nennt genau die gelieferten Dateien und Spalten."""

        ada: Konto = forschende("ada")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Kontrakt")
        self.client.force_login(ada)

        export: HttpResponse = self.client.get(
            reverse("erhebungen:export", args=[erhebung.pk])
        )

        self.assertEqual(export_kopfzeilen(export), exportkontrakt_aus_adr_0029())


class ErhebungenGesperrteItemzuordnungTests(TestCase):
    """Finale Erhebungen zeigen ihre Itemzuordnung ohne Änderungswege."""

    def test_finale_erhebung_zeigt_items_je_andockpunkt_ohne_bibliothek_oder_aktionen(
        self,
    ) -> None:
        """Das eingefrorene Design bleibt in seiner Reihenfolge lesbar."""

        ada: Konto = forschende("ada")
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
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
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
        self.assertNotContains(detail, "zuordnungsliste__einfuegen")
        self.assertNotContains(detail, "zuordnung-iconknopf")
        for url in (
            reverse("erhebungen:item_entfernen", args=[erhebung.pk, erste_bindung.pk]),
            reverse(
                "erhebungen:item_verschieben", args=[erhebung.pk, zweite_bindung.pk]
            ),
            reverse("erhebungen:item_umhaengen", args=[erhebung.pk, erste_bindung.pk]),
            reverse("erhebungen:item_entfernen", args=[erhebung.pk, ende_bindung.pk]),
        ):
            self.assertNotContains(detail, url)

    def test_archivierte_erhebung_zeigt_leere_andockpunktbereiche_gesperrt(
        self,
    ) -> None:
        """Auch ohne Items bleibt die archivierte Zuordnung als leere Ansicht lesbar."""

        ada: Konto = forschende("ada")
        erhebung: Erhebung = finale_erhebung(ada)
        erhebung.archivieren()
        self.client.force_login(ada)

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[erhebung.pk])
        )

        self.assertContains(detail, "Nach jeder Vignettensitzung")
        self.assertContains(detail, "Am Ende")
        self.assertContains(detail, "Keine Fragebogen-Items aufgenommen.", count=2)
        self.assertNotContains(detail, "zuordnungsliste__einfuegen")

    def test_finale_erhebung_zeigt_vignetten_ohne_aktionen(self) -> None:
        """Auch die Vignettenliste bleibt nach dem Finalisieren lesbar, aber fest."""

        ada: Konto = forschende("ada")
        erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
        vignette: Vignette = finale_vignette(ada, fach="Mathematik")
        Erhebungsvignette.objects.create(
            erhebung=erhebung, vignette=vignette, position=1
        )
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        erhebung.finalisieren()
        self.client.force_login(ada)

        detail: HttpResponse = self.client.get(
            reverse("erhebungen:detail", args=[erhebung.pk])
        )

        self.assertContains(detail, "Feste Reihenfolge")
        self.assertNotContains(detail, "zuordnungsliste__einfuegen")
        self.assertNotContains(detail, "zuordnung-iconknopf")
        self.assertNotContains(detail, 'role="switch"')
        self.assertEqual(
            detail.context["aufgenommene_daten"],
            [
                {
                    "pk": vignette.pk,
                    "label": vignette.anzeigename,
                    "fach": vignette.fach,
                    "thema": vignette.thema,
                }
            ],
        )


class ErhebungstexteVorschauUndLeseansichtTests(TestCase):
    """Forschende sehen ihre Erhebungstexte so, wie Teilnehmer:innen sie sehen."""

    def setUp(self) -> None:
        # Richtet eine Forschende mit einem Entwurf voller Markdown-Texte ein.

        self.ada: Konto = forschende("ada")
        self.erhebung: Erhebung = Erhebung.objects.anlegen(self.ada, name="Brüche")
        self.erhebung.instruktionstext = "# Ablauf\n- erst\n- dann"
        self.erhebung.einwilligungstext = "**Zweck** [Datenschutz](https://example.org)"
        self.erhebung.abschlusstext = ""
        self.erhebung.save()
        ModellKonfiguration.objects.aktivieren(
            _forschungskonfiguration(), Verwendung.SCHUELERIN
        )
        self.client.force_login(self.ada)

    def _detail(self) -> HttpResponse:
        return self.client.get(reverse("erhebungen:detail", args=[self.erhebung.pk]))

    def test_entwurf_bietet_je_textfeld_hinweis_und_umschalter(self) -> None:
        """Alle drei Felder holen ihre Vorschau im Profil Informationstext."""

        detail: HttpResponse = self._detail()

        self.assertContains(detail, ">Vorschau</button>", count=3)
        self.assertContains(detail, f'hx-post="{reverse("texte:vorschau")}"', count=3)
        self.assertContains(detail, '"profil": "informationstext"', count=3)
        self.assertContains(detail, "[Linktext](https://…)", count=3)
        for feld in ("instruktionstext", "einwilligungstext", "abschlusstext"):
            self.assertContains(detail, f'name="{feld}"')
        self.assertContains(detail, "<h3>Ablauf</h3>", count=1)

    def test_vorschau_entspricht_der_teilnahmeseite(self) -> None:
        """Endpunkt und Teilnahmeseite liefern dasselbe Rendering."""

        vorschau: HttpResponse = self.client.post(
            reverse("texte:vorschau"),
            {
                "profil": "informationstext",
                "quelle": self.erhebung.einwilligungstext,
            },
        )
        self.erhebung.finalisieren()
        stichprobe: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=timezone.now() - timedelta(days=1),
            ende=timezone.now() + timedelta(days=1),
        )
        teilnahmeseite: HttpResponse = self.client.get(
            reverse("erhebungen:teilnehmen", args=[stichprobe.teilnahme_link]),
            follow=True,
        )

        self.assertContains(teilnahmeseite, vorschau.content.decode().strip())


@pytest.mark.django_db
@pytest.mark.parametrize("archiviert", [False, True], ids=["final", "archiviert"])
def test_finale_und_archivierte_erhebung_zeigen_die_texte_gerendert_und_nur_lesend(
    client: Client, archiviert: bool
) -> None:
    """Die Leseansicht rendert Markdown und nutzt für Leeres den Platzhalter."""

    ada: Konto = forschende("ada")
    erhebung: Erhebung = finale_erhebung(
        ada,
        instruktionstext="# Ablauf\n- erst\n- dann",
        einwilligungstext="**Zweck** [Datenschutz](https://example.org)",
        abschlusstext="",
    )
    if archiviert:
        erhebung.archivieren()
    client.force_login(ada)

    detail: HttpResponse = client.get(reverse("erhebungen:detail", args=[erhebung.pk]))

    assertContains(detail, "<h3>Ablauf</h3>")
    assertContains(detail, "<li>erst</li>")
    assertContains(detail, "<strong>Zweck</strong>")
    assertContains(detail, 'href="https://example.org"')
    assertContains(detail, '<div class="markdown-text">—</div>')
    assertNotContains(detail, "<textarea")
    assertNotContains(detail, ">Vorschau</button>")

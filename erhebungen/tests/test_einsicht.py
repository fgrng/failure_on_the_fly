"""HTTP-Tests der Übersicht in der Fremdeinsicht einer Erhebung (ADR-0049)."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import time_machine
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from config.tests.aufbau import finale_vignette, finaler_kern, konto_mit_rollen
from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Stichprobe,
    Vignettenziehung,
)
from erhebungen.tests.aufbau import finale_erhebung, forschende
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE, AUTORIN_GRUPPE
from simulation.models import ModellKonfiguration, Verwendung
from sitzungen.models import Sitzung
from vignetten.models import Vignette

_BERLIN: ZoneInfo = ZoneInfo("Europe/Berlin")


def _einsicht_url(erhebung: Erhebung) -> str:
    return reverse("erhebungen:einsicht", args=[erhebung.pk])


class EinsichtTestCase(TestCase):
    """Eine finale Erhebung von ada mit zwei Vignetten und einer Stichprobe."""

    def setUp(self) -> None:
        self.ada: Konto = forschende("ada")
        self.brueche: Vignette = finale_vignette(self.ada, name="Brüche addieren")
        self.zinsen: Vignette = finale_vignette(self.ada, name="Zinsen rechnen")
        self.erhebung: Erhebung = finale_erhebung(
            self.ada, vignetten=[self.brueche, self.zinsen]
        )
        self.stichprobe: Stichprobe = self._stichprobe(self.erhebung)

    def _stichprobe(self, erhebung: Erhebung) -> Stichprobe:
        return Stichprobe.objects.create(
            erhebung=erhebung,
            beginn=timezone.now() - timedelta(days=30),
            ende=timezone.now() + timedelta(days=30),
        )

    def _teilnahme(
        self,
        stichprobe: Stichprobe | None = None,
        *,
        beginn: datetime | None = None,
        einwilligung: bool | None = True,
        fluechtig: bool = False,
        ziehung: tuple[Vignette, ...] | None = None,
    ) -> Erhebungsbindung:
        # Eine Teilnahme, begonnen zum angegebenen Zeitpunkt; die Ziehung legt
        # die gespielte Reihenfolge fest, ohne Angabe die der Erhebung.
        with time_machine.travel(beginn or timezone.now(), tick=False):
            bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(
                stichprobe or self.stichprobe
            )
        bindung.teilnahme.sprachmodell_eingewilligt = einwilligung
        bindung.teilnahme.speicherung_eingewilligt = not fluechtig
        bindung.teilnahme.save()
        if einwilligung:
            for position, vignette in enumerate(
                ziehung or (self.brueche, self.zinsen), start=1
            ):
                Vignettenziehung.objects.create(
                    erhebungsbindung=bindung, vignette=vignette, position=position
                )
        return bindung

    def _sitzung(
        self,
        bindung: Erhebungsbindung,
        vignette: Vignette,
        status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN,
    ) -> Sitzung:
        return Sitzung.objects.create(
            teilnahme=bindung.teilnahme,
            vignette=vignette,
            simulationskern=finaler_kern(),
            modell_konfiguration=ModellKonfiguration.objects.belegte(
                Verwendung.SCHUELERIN
            ),
            status=status,
        )

    def _einsicht(self, konto: Konto | None = None) -> HttpResponse:
        self.client.force_login(konto or self.ada)
        return self.client.get(_einsicht_url(self.erhebung))

    def _zeile(self, antwort: HttpResponse, bindung: Erhebungsbindung) -> str:
        # Die Tabellenzeile, die mit der Kennung der Teilnahme beschriftet ist.
        treffer: list[str] = re.findall(
            r"<tr\b(?:(?!</tr>).)*</tr>", antwort.content.decode(), re.DOTALL
        )
        zeilen: list[str] = [
            zeile for zeile in treffer if bindung.teilnahme.kennung in zeile
        ]
        self.assertEqual(len(zeilen), 1, zeilen)
        return zeilen[0]


class EinsichtZugangTests(EinsichtTestCase):
    """Wer die Übersicht erreicht."""

    def setUp(self) -> None:
        super().setUp()
        self.bindung: Erhebungsbindung = self._teilnahme()

    def test_kreismitglied_sieht_die_teilnahme_unter_ihrer_kennung(self) -> None:
        """Die eigene Erhebung zeigt jede eingewilligte Teilnahme."""

        antwort: HttpResponse = self._einsicht()

        self.assertContains(antwort, self.bindung.teilnahme.kennung)

    def test_administration_sieht_jede_erhebung(self) -> None:
        """Die Administration sieht die Übersicht einer fremden Erhebung."""

        admin: Konto = konto_mit_rollen("root", is_superuser=True)

        antwort: HttpResponse = self._einsicht(admin)

        self.assertContains(antwort, self.bindung.teilnahme.kennung)

    def test_fremder_kreis_bekommt_404(self) -> None:
        """Eine fremde Erhebung bleibt unauffindbar."""

        self.assertEqual(self._einsicht(forschende("grace")).status_code, 404)

    def test_andere_rollen_werden_abgewiesen(self) -> None:
        """Ohne Forschungsrolle gibt es keine Einsicht."""

        for username, rollen in (
            ("hedy", (AUSBILDERIN_GRUPPE,)),
            ("lin", (AUTORIN_GRUPPE,)),
            ("mo", ()),
        ):
            with self.subTest(username=username):
                konto: Konto = konto_mit_rollen(username, *rollen)

                self.assertEqual(self._einsicht(konto).status_code, 403)

    def test_neues_kreismitglied_sieht_aeltere_teilnahmen(self) -> None:
        """Einsicht folgt der aktuellen Eigentümerschaft, auch rückwirkend."""

        neu: Konto = forschende("hedy")
        self.erhebung.eigentuemerinnen.add(neu)

        antwort: HttpResponse = self._einsicht(neu)

        self.assertContains(antwort, self.bindung.teilnahme.kennung)

    def test_ausgetretenes_kreismitglied_bekommt_404(self) -> None:
        """Wer den Kreis verlässt, sieht sofort nichts mehr."""

        self.erhebung.eigentuemerinnen.add(forschende("hedy"))
        self.erhebung.austreten(self.ada.pk)

        self.assertEqual(self._einsicht().status_code, 404)

    def test_bleibt_nach_dem_archivieren_der_erhebung_lesbar(self) -> None:
        """Eine archivierte Erhebung zeigt ihre Teilnahmen weiter."""

        self.stichprobe.ende = timezone.now() - timedelta(days=1)
        self.stichprobe.save(update_fields=["ende"])
        self.erhebung.archivieren()

        antwort: HttpResponse = self._einsicht()

        self.assertContains(antwort, self.bindung.teilnahme.kennung)

    def test_archivierte_stichprobe_bleibt_lesbar(self) -> None:
        """Eine archivierte Stichprobe steht weiter in der Übersicht."""

        # Archivieren lassen sich nur Stichproben ohne Daten.
        archivierte: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=datetime(2027, 3, 1, tzinfo=_BERLIN),
            ende=datetime(2027, 3, 31, tzinfo=_BERLIN),
        )
        archivierte.archivieren()

        self.assertContains(self._einsicht(), "Stichprobe 01.03.2027 – 31.03.2027")


class EinsichtLinkTests(EinsichtTestCase):
    """Der Link auf der Detailseite der Erhebung."""

    def _detail(self) -> HttpResponse:
        self.client.force_login(self.ada)
        return self.client.get(reverse("erhebungen:detail", args=[self.erhebung.pk]))

    def test_ohne_teilnahmen_fehlt_der_link(self) -> None:
        """Eine Stichprobe ohne Teilnahmen bietet keine leere Einsicht an."""

        self.assertNotContains(self._detail(), _einsicht_url(self.erhebung))

    def test_mit_teilnahme_erscheint_der_link(self) -> None:
        """Sobald eine Teilnahme besteht, führt der Link zur Einsicht."""

        self._teilnahme()

        self.assertContains(self._detail(), _einsicht_url(self.erhebung))


class EinsichtRasterTests(EinsichtTestCase):
    """Aufbau und Inhalt des Rasters."""

    def test_spalten_folgen_der_erhebungsreihenfolge(self) -> None:
        """Die Vignetten stehen in der Reihenfolge der Erhebung."""

        # Umgekehrt zur Anlagereihenfolge der Vignetten.
        self.erhebung = finale_erhebung(self.ada, vignetten=[self.zinsen, self.brueche])
        self._stichprobe(self.erhebung)

        inhalt: str = self._einsicht().content.decode()

        self.assertLess(inhalt.index("Zinsen rechnen"), inhalt.index("Brüche addieren"))

    def test_zeilen_sind_nach_beginn_sortiert(self) -> None:
        """Die älteste Teilnahme steht oben."""

        spaete: Erhebungsbindung = self._teilnahme(
            beginn=datetime(2026, 10, 5, 9, 0, tzinfo=_BERLIN)
        )
        fruehe: Erhebungsbindung = self._teilnahme(
            beginn=datetime(2026, 10, 1, 9, 0, tzinfo=_BERLIN)
        )

        inhalt: str = self._einsicht().content.decode()

        self.assertLess(
            inhalt.index(fruehe.teilnahme.kennung),
            inhalt.index(spaete.teilnahme.kennung),
        )

    def test_ist_nach_stichproben_gegliedert(self) -> None:
        """Jede Teilnahme steht unter ihrer Stichprobe."""

        zweite: Stichprobe = Stichprobe.objects.create(
            erhebung=self.erhebung,
            beginn=datetime(2027, 3, 1, tzinfo=_BERLIN),
            ende=datetime(2027, 3, 31, tzinfo=_BERLIN),
        )
        erste_bindung: Erhebungsbindung = self._teilnahme()
        zweite_bindung: Erhebungsbindung = self._teilnahme(zweite)

        inhalt: str = self._einsicht().content.decode()

        self.assertLess(
            inhalt.index(erste_bindung.teilnahme.kennung), inhalt.index("01.03.2027")
        )
        self.assertLess(
            inhalt.index("01.03.2027"), inhalt.index(zweite_bindung.teilnahme.kennung)
        )

    def test_bubble_zeigt_die_gespielte_position(self) -> None:
        """Die Position stammt aus der Ziehung, nicht aus der Spalte."""

        bindung: Erhebungsbindung = self._teilnahme(ziehung=(self.zinsen, self.brueche))
        self._sitzung(bindung, self.zinsen)
        self._sitzung(bindung, self.brueche, Sitzung.Status.LAUFEND)

        zeile: str = self._zeile(self._einsicht(), bindung)

        self.assertRegex(
            zeile,
            r'class="fremdeinsicht__sitzung"[^>]*aria-label="Position 1, '
            r'Abgeschlossen"[^>]*>1<',
        )

    def test_abgebrochene_und_gescheiterte_tragen_warnfarbe_und_status(
        self,
    ) -> None:
        """Auffällige Ausgänge fallen auf und nennen ihren Status."""

        bindung: Erhebungsbindung = self._teilnahme()
        self._sitzung(bindung, self.brueche, Sitzung.Status.ABGEBROCHEN)
        self._sitzung(bindung, self.zinsen, Sitzung.Status.GESCHEITERT)

        zeile: str = self._zeile(self._einsicht(), bindung)

        for position, status in ((1, "Abgebrochen"), (2, "Gescheitert")):
            self.assertRegex(
                zeile,
                r'class="fremdeinsicht__sitzung fremdeinsicht__sitzung--warnung"'
                rf' title="{status}" aria-label="Position {position}, {status}"'
                rf">{position}<",
            )

    def test_laufende_sitzung_ist_gedimmt(self) -> None:
        """Eine laufende Sitzung zeigt nur, dass sie läuft."""

        bindung: Erhebungsbindung = self._teilnahme()
        self._sitzung(bindung, self.brueche, Sitzung.Status.LAUFEND)

        zeile: str = self._zeile(self._einsicht(), bindung)

        self.assertIn(
            'class="fremdeinsicht__sitzung fremdeinsicht__sitzung--laufend"', zeile
        )

    def test_bubbles_sind_noch_nicht_verlinkt(self) -> None:
        """Die Sitzungsansicht kommt erst später; keine Bubble ist ein Link."""

        bindung: Erhebungsbindung = self._teilnahme()
        self._sitzung(bindung, self.brueche)

        self.assertNotIn("<a ", self._zeile(self._einsicht(), bindung))

    def test_fluechtige_zeile_traegt_den_hinweis(self) -> None:
        """Von flüchtigen Teilnahmen gibt es nur das Ablaufgerüst."""

        bindung: Erhebungsbindung = self._teilnahme(fluechtig=True)
        self._sitzung(bindung, self.brueche)

        self.assertIn(
            "flüchtig, nur Ablaufgerüst", self._zeile(self._einsicht(), bindung)
        )

    def test_fluechtige_bubbles_sind_in_jedem_status_umrandet(self) -> None:
        """Auch eine gescheiterte flüchtige Sitzung ist nur umrandet."""

        bindung: Erhebungsbindung = self._teilnahme(fluechtig=True)
        self._sitzung(bindung, self.brueche)
        self._sitzung(bindung, self.zinsen, Sitzung.Status.GESCHEITERT)

        zeile: str = self._zeile(self._einsicht(), bindung)

        self.assertEqual(zeile.count("fremdeinsicht__sitzung--fluechtig"), 2)

    def test_eingewilligte_teilnahme_ohne_sitzung(self) -> None:
        """Wer eingewilligt, aber noch nicht gespielt hat, steht in der Liste."""

        bindung: Erhebungsbindung = self._teilnahme()

        self.assertIn("noch keine Sitzung", self._zeile(self._einsicht(), bindung))

    def test_abgelehnte_und_unentschiedene_teilnahmen_fehlen(self) -> None:
        """Ohne Einwilligung a gibt es keine Ziehung und keine Zeile."""

        abgelehnt: Erhebungsbindung = self._teilnahme(einwilligung=False)
        offen: Erhebungsbindung = self._teilnahme(einwilligung=None)

        antwort: HttpResponse = self._einsicht()

        self.assertNotContains(antwort, abgelehnt.teilnahme.kennung)
        self.assertNotContains(antwort, offen.teilnahme.kennung)

    def test_token_steht_nirgends_im_html(self) -> None:
        """Über die Einsicht lässt sich keine Teilnahme fortsetzen."""

        bindung: Erhebungsbindung = self._teilnahme()
        self._sitzung(bindung, self.brueche)

        self.assertNotContains(self._einsicht(), bindung.token)

    def test_teilnahmen_anderer_erhebungen_fehlen(self) -> None:
        """Eine fremde Erhebung derselben Vignette steuert keine Zeile bei."""

        andere: Erhebung = finale_erhebung(self.ada, vignetten=[self.brueche])
        fremde: Erhebungsbindung = self._teilnahme(
            self._stichprobe(andere), ziehung=(self.brueche,)
        )
        self._sitzung(fremde, self.brueche)

        self.assertNotContains(self._einsicht(), fremde.teilnahme.kennung)

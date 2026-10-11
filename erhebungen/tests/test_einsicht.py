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
    Erhebungsitem,
    ItemAntwort,
    Itemblock,
    Stichprobe,
    Vignettenziehung,
)
from erhebungen.tests.aufbau import finale_erhebung, forschende
from fragebogen_items.models import FragebogenItem
from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE, AUTORIN_GRUPPE
from simulation.models import ModellKonfiguration, Verwendung
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
)
from vignetten.models import Vignette

_BERLIN: ZoneInfo = ZoneInfo("Europe/Berlin")


def _einsicht_url(erhebung: Erhebung) -> str:
    return reverse("erhebungen:einsicht", args=[erhebung.pk])


def _sitzung_url(erhebung: Erhebung, sitzung: Sitzung) -> str:
    return reverse("erhebungen:einsicht_sitzung", args=[erhebung.pk, sitzung.pk])


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
                rf"[^>]*>{position}<",
            )

    def test_laufende_sitzung_ist_gedimmt(self) -> None:
        """Eine laufende Sitzung zeigt nur, dass sie läuft."""

        bindung: Erhebungsbindung = self._teilnahme()
        self._sitzung(bindung, self.brueche, Sitzung.Status.LAUFEND)

        zeile: str = self._zeile(self._einsicht(), bindung)

        self.assertIn(
            'class="fremdeinsicht__sitzung fremdeinsicht__sitzung--laufend"', zeile
        )

    def test_bubbles_beendeter_sitzungen_sind_verlinkt(self) -> None:
        """Abgeschlossene, abgebrochene und gescheiterte Sitzungen öffnen sich."""

        bindung: Erhebungsbindung = self._teilnahme()
        abgeschlossen: Sitzung = self._sitzung(bindung, self.brueche)
        gescheitert: Sitzung = self._sitzung(
            bindung, self.zinsen, Sitzung.Status.GESCHEITERT
        )

        zeile: str = self._zeile(self._einsicht(), bindung)

        for sitzung in (abgeschlossen, gescheitert):
            self.assertIn(f'href="{_sitzung_url(self.erhebung, sitzung)}"', zeile)

    def test_laufende_und_fluechtige_bubbles_sind_nicht_verlinkt(self) -> None:
        """Wer nichts lesen kann, bekommt keinen Link."""

        laufend: Erhebungsbindung = self._teilnahme()
        self._sitzung(laufend, self.brueche, Sitzung.Status.LAUFEND)
        fluechtig: Erhebungsbindung = self._teilnahme(fluechtig=True)
        self._sitzung(fluechtig, self.brueche)

        antwort: HttpResponse = self._einsicht()

        self.assertNotIn("<a ", self._zeile(antwort, laufend))
        self.assertNotIn("<a ", self._zeile(antwort, fluechtig))

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


class EinsichtSitzungTests(EinsichtTestCase):
    """Die lesende Sitzungsansicht der Einsicht."""

    def setUp(self) -> None:
        super().setUp()
        self.bindung: Erhebungsbindung = self._teilnahme()

    def _gespielte_sitzung(
        self,
        status: Sitzung.Status = Sitzung.Status.ABGESCHLOSSEN,
        bindung: Erhebungsbindung | None = None,
    ) -> Sitzung:
        # Eine Sitzung mit einem Gesprächsschritt samt Denkspur und
        # Fehlversuch und einer abgegebenen Diagnose.
        sitzung: Sitzung = self._sitzung(bindung or self.bindung, self.brueche, status)
        schritt: Gespraechsschritt = Gespraechsschritt.objects.create(
            sitzung=sitzung,
            eingabe="Wie hast du gerechnet?",
            denkspur="Mia addiert Zähler und Nenner.",
            aeusserung="Ich habe oben und unten zusammengezählt.",
            reihenfolge=1,
        )
        Fehlversuch.objects.create(
            gespraechsschritt=schritt,
            grund="kein JSON",
            rohantwort="Verworfene Rohantwort des Modells.",
        )
        Diagnose.objects.create(sitzung=sitzung, text="Zähler und Nenner addiert.")
        return sitzung

    def _ansicht(self, sitzung: Sitzung, konto: Konto | None = None) -> HttpResponse:
        self.client.force_login(konto or self.ada)
        return self.client.get(_sitzung_url(self.erhebung, sitzung))

    def _seite(self, antwort: HttpResponse) -> str:
        # Der Seiteninhalt ohne die Navigation, deren Abmelden ein Formular ist.
        inhalt: str = antwort.content.decode()
        return inhalt[inhalt.index('<article class="sitzung-seite"') :]

    def test_kreis_liest_transkript_denkspur_und_diagnose(self) -> None:
        """Die abgeschlossene Sitzung zeigt, was die Teilnehmerin sah, und mehr."""

        antwort: HttpResponse = self._ansicht(self._gespielte_sitzung())

        self.assertContains(antwort, "Wie hast du gerechnet?")
        self.assertContains(antwort, "Ich habe oben und unten zusammengezählt.")
        self.assertContains(antwort, "Denkspur ansehen")
        self.assertContains(antwort, "Mia addiert Zähler und Nenner.")
        self.assertContains(antwort, "Zähler und Nenner addiert.")

    def test_administration_liest_jede_sitzung(self) -> None:
        """Die Administration öffnet die Sitzung einer fremden Erhebung."""

        admin: Konto = konto_mit_rollen("root", is_superuser=True)

        antwort: HttpResponse = self._ansicht(self._gespielte_sitzung(), admin)

        self.assertContains(antwort, "Mia addiert Zähler und Nenner.")

    def test_abgebrochene_sitzung_zeigt_keine_diagnose(self) -> None:
        """Nur abgeschlossene Sitzungen haben einen Debrief."""

        for status in (Sitzung.Status.ABGEBROCHEN, Sitzung.Status.GESCHEITERT):
            with self.subTest(status=status):
                antwort: HttpResponse = self._ansicht(
                    self._gespielte_sitzung(status, self._teilnahme())
                )

                self.assertContains(antwort, "Ich habe oben und unten zusammengezählt.")
                self.assertNotContains(antwort, "Zähler und Nenner addiert.")

    def test_kopf_nennt_kennung_stichprobe_vignette_und_status(self) -> None:
        """Wer liest, weiß, was er liest, und findet zurück zur Übersicht."""

        antwort: HttpResponse = self._ansicht(
            self._gespielte_sitzung(Sitzung.Status.GESCHEITERT)
        )

        self.assertContains(antwort, self.bindung.teilnahme.kennung)
        self.assertContains(
            antwort,
            f"Stichprobe {self.stichprobe.beginn:%d.%m.%Y} – "
            f"{self.stichprobe.ende:%d.%m.%Y}",
        )
        self.assertContains(antwort, "Brüche addieren")
        self.assertContains(antwort, "Gescheitert")
        self.assertContains(antwort, f'href="{_einsicht_url(self.erhebung)}"')

    def test_item_antworten_nach_der_sitzung_stehen_darunter(self) -> None:
        """Die Antworten auf den Block dieser Sitzung erscheinen lesend."""

        likert: FragebogenItem = FragebogenItem.objects.anlegen(
            self.ada,
            typ=FragebogenItem.Typ.LIKERT,
            wortlaut="Wie sicher fühlten Sie sich?",
        )
        freitext: FragebogenItem = FragebogenItem.objects.anlegen(
            self.ada, wortlaut="Was war schwierig?"
        )
        for item in (likert, freitext):
            item.finalisieren()
        self.erhebung = finale_erhebung(
            self.ada, vignetten=[self.brueche], items_nach_sitzung=[likert, freitext]
        )
        bindung: Erhebungsbindung = self._teilnahme(
            self._stichprobe(self.erhebung), ziehung=(self.brueche,)
        )
        sitzung: Sitzung = self._gespielte_sitzung(bindung=bindung)
        block: Itemblock = Itemblock.objects.create(
            erhebungsbindung=bindung,
            andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
            sitzung=sitzung,
        )
        for erhebungsitem, werte in zip(
            self.erhebung.itemzugehoerigkeiten.order_by("position"),
            ({"likert_stufe": 5}, {"freitext": "Das Kürzen."}),
        ):
            ItemAntwort.objects.create(
                itemblock=block,
                erhebungsbindung=bindung,
                erhebungsitem=erhebungsitem,
                sitzung=sitzung,
                **werte,
            )

        inhalt: str = self._ansicht(sitzung).content.decode()

        self.assertIn("Wie sicher fühlten Sie sich?", inhalt)
        self.assertIn("Stimme zu", inhalt)
        self.assertIn("Das Kürzen.", inhalt)
        self.assertLess(
            inhalt.index("Zähler und Nenner addiert."),
            inhalt.index("Wie sicher fühlten Sie sich?"),
        )

    def test_keine_fehlversuche_kein_token_keine_formulare(self) -> None:
        """Die Ansicht ist rein lesend und führt in keine Teilnahme zurück."""

        antwort: HttpResponse = self._ansicht(self._gespielte_sitzung())
        seite: str = self._seite(antwort)

        self.assertNotContains(antwort, "Verworfene Rohantwort des Modells.")
        self.assertNotContains(antwort, self.bindung.token)
        self.assertNotIn("<form", seite)
        self.assertNotIn("<textarea", seite)
        self.assertNotIn("<button", seite)

    def test_laufende_sitzung_bekommt_404(self) -> None:
        """Live-Mitlesen gibt es nicht."""

        sitzung: Sitzung = self._gespielte_sitzung(Sitzung.Status.LAUFEND)

        self.assertEqual(self._ansicht(sitzung).status_code, 404)

    def test_fluechtige_sitzung_bekommt_404(self) -> None:
        """Von flüchtigen Teilnahmen gibt es nur das Gerüst."""

        sitzung: Sitzung = self._gespielte_sitzung(
            bindung=self._teilnahme(fluechtig=True)
        )

        self.assertEqual(self._ansicht(sitzung).status_code, 404)

    def test_sitzung_einer_anderen_erhebung_bekommt_404(self) -> None:
        """Die Sitzung wird gegen die Erhebung aus der URL geprüft."""

        andere: Erhebung = finale_erhebung(self.ada, vignetten=[self.brueche])
        fremde: Sitzung = self._gespielte_sitzung(
            bindung=self._teilnahme(self._stichprobe(andere), ziehung=(self.brueche,))
        )

        self.assertEqual(self._ansicht(fremde).status_code, 404)

    def test_fremder_kreis_bekommt_404(self) -> None:
        """Außerhalb des Kreises bleibt die Sitzung unauffindbar."""

        sitzung: Sitzung = self._gespielte_sitzung()

        self.assertEqual(self._ansicht(sitzung, forschende("grace")).status_code, 404)

    def test_andere_rollen_werden_abgewiesen(self) -> None:
        """Ohne Forschungsrolle gibt es keine Sitzungsansicht."""

        sitzung: Sitzung = self._gespielte_sitzung()

        konto: Konto = konto_mit_rollen("hedy", AUSBILDERIN_GRUPPE)

        self.assertEqual(self._ansicht(sitzung, konto).status_code, 403)

    def test_trainingssitzung_bekommt_404(self) -> None:
        """Eine Sitzung ohne Erhebungsbindung ist hier unbekannt."""

        sitzung: Sitzung = Sitzung.objects.create(
            teilnahme=Teilnahme.objects.create(),
            vignette=self.brueche,
            simulationskern=finaler_kern(),
            modell_konfiguration=ModellKonfiguration.objects.belegte(
                Verwendung.SCHUELERIN
            ),
            status=Sitzung.Status.ABGESCHLOSSEN,
        )

        self.assertEqual(self._ansicht(sitzung).status_code, 404)

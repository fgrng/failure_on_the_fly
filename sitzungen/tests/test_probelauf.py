"""HTTP-Tests für den schreibfreien Probelauf."""

from datetime import UTC, datetime

import time_machine
from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finaler_kern,
    konto_mit_rollen,
    vignetten_entwurf,
)
from config.tests.formular import submit_knoepfe
from config.tests.sprachmodell import anfragen_aufzeichnen, modellaufrufe_dauern
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.durchlauf import Ausgang, gespraechsschritt_ausfuehren
from sitzungen.models import (
    Diagnose,
    Eingabemodus,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
)
from sitzungen.sink import ScratchSink, probelauf_laeuft
from vignetten.models import Vignette


# Zeitpunkt, zu dem das Gespräch angezeigt wird; ab hier zählen die Züge.
_GESPRAECHSBEGINN: datetime = datetime(2026, 9, 22, 10, 0, 10, tzinfo=UTC)

_ENDGUELTIGER_FEHLSCHLAG: list[dict[str, str]] = [
    {"fehler": "anbieterfehler", "rohantwort": "Rohtext vom Anbieter"},
    {"fehler": "anbieterfehler", "rohantwort": "Rohtext vom Anbieter"},
    {"fehler": "anbieterfehler", "rohantwort": "Rohtext vom Anbieter"},
]


class _ProbelaufAufbau(TestCase):
    """Gemeinsamer Aufbau der Probelauf-Tests, selbst ohne Tests."""

    def setUp(self) -> None:
        """Legt die sichtbaren und fremden Entwürfe für die HTTP-Tests an."""

        # Den Probelauf startet nur, wer den Vignetteneditor erreicht — und
        # dorthin führt er nach dem Debrief auch zurück.
        self.ada: Konto = konto_mit_rollen("ada", "Autor:in")
        grace: Konto = konto_mit_rollen("grace")
        self.kern: Simulationskern = Simulationskern.objects.anlegen(
            user_prompt_vorlage=(
                "$lernauftrag_simulationshinweise $arbeitsheft_simulationshinweise"
            ),
            rahmenhandlung_einleitung=(
                "$lehrperson_anrede $lehrperson_name begleitet Sie bei "
                "$fach in Klasse $klassenstufe."
            ),
            rahmenhandlung_gespraechseinleitung=(
                "$schuelerin_name zeigt Ihnen die Bearbeitung."
            ),
            rahmenhandlung_debrief=(
                "$lehrperson_anrede $lehrperson_name fragt nach Ihrer Diagnose."
            ),
        )
        self.kern.finalisieren()
        self.konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test", sprachmodell="fake", parameter={"skript": []}
        )
        ModellKonfiguration.objects.aktivieren(
            self.konfiguration, Verwendung.SCHUELERIN
        )
        self.entwurf: Vignette = vignetten_entwurf(self.ada)
        self.entwurf.historie.name = "Eigener Entwurf"
        self.entwurf.historie.save()
        self.entwurf.schuelerin_name = "Mia"
        self.entwurf.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.lehrperson_name = "Weber"
        self.entwurf.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.fach = "Mathematik"
        self.entwurf.thema = "Brüche"
        self.entwurf.klassenstufe = "5"
        self.entwurf.save()
        fremder_entwurf: Vignette = vignetten_entwurf(grace)
        fremder_entwurf.historie.name = "Fremder Entwurf"
        fremder_entwurf.historie.save()
        self.client.force_login(self.ada)


class ProbelaufStartTests(_ProbelaufAufbau):
    """Die HTTP-Naht startet einen Probelauf über einem festen Tripel."""

    def test_auswahl_zeigt_nur_eigene_entwuerfe_und_startet_rahmenhandlung(
        self,
    ) -> None:
        """Der Start zeigt nur eigene Entwürfe an und rendert die Rahmenhandlung."""

        auswahl: HttpResponse = self.client.get(reverse("sitzungen:probelauf_auswahl"))

        self.assertContains(auswahl, "Eigener Entwurf")
        self.assertNotContains(auswahl, "Fremder Entwurf")

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(
            response, "Frau Weber begleitet Sie bei Mathematik in Klasse 5."
        )
        self.assertContains(response, "Mia zeigt Ihnen die Bearbeitung.")
        self.assertContains(response, "Ihre nächste Frage")
        self.assertNotContains(response, "Diagnosegespräch beginnen")
        gespraech: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech")
        )
        self.assertContains(gespraech, "Ihre nächste Frage")

    def test_start_liest_die_schuelerin_nicht_lehrperson_oder_bewerter(
        self,
    ) -> None:
        """Ein Wechsel der Eval-Verwendungen ändert am Probelauf nichts."""

        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(
                bezeichnung="Schülerin",
                sprachmodell="fake",
                parameter={
                    "skript": [{"denkspur": "-", "aeusserung": "Antwort der Schülerin"}]
                },
            ),
            Verwendung.SCHUELERIN,
        )
        andere: ModellKonfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Andere",
            sprachmodell="fake",
            parameter={"skript": [{"denkspur": "-", "aeusserung": "Andere Antwort"}]},
        )
        ModellKonfiguration.objects.aktivieren(andere, Verwendung.LEHRPERSON)
        ModellKonfiguration.objects.aktivieren(andere, Verwendung.BEWERTER)

        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))
        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie?"}
        )

        self.assertContains(response, "Antwort der Schülerin")
        self.assertNotContains(response, "Andere Antwort")

    def test_frischer_entwurf_startet_ohne_akteure_zu_setzen(self) -> None:
        """Der Probelauf rendert mit den beim Anlegen gesetzten Akteuren."""
        entwurf: Vignette = vignetten_entwurf(self.ada)
        entwurf.fach = "Mathematik"
        entwurf.thema = "Brüche"
        entwurf.klassenstufe = "5"
        entwurf.save()

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[entwurf.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "begleitet Sie bei Mathematik in Klasse 5.")
        self.assertContains(response, "zeigt Ihnen die Bearbeitung.")

    def test_rahmenhandlung_erscheint_als_szenentext_mit_woertlichen_werten(
        self,
    ) -> None:
        """Einleitung, Gesprächseinleitung und Debrief werden gerendert."""

        kern: Simulationskern = self.kern.bearbeiten()
        kern.rahmenhandlung_einleitung = "# Hospitation\n\nThema: **$thema**"
        kern.rahmenhandlung_gespraechseinleitung = "*$schuelerin_name* zeigt."
        kern.rahmenhandlung_debrief = "- [Diagnose](https://example.org)"
        kern.save()
        kern.finalisieren()
        self.entwurf.gepinnter_kern = kern
        self.entwurf.thema = "_Brüche_"
        self.entwurf.save()

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )
        debrief: HttpResponse = self.client.post(reverse("sitzungen:probelauf_beenden"))

        self.assertContains(response, "<h3>Hospitation</h3>")
        self.assertContains(response, "<strong>_Brüche_</strong>")
        self.assertContains(response, "<em>Mia</em> zeigt.")
        self.assertContains(debrief, "<li>[Diagnose](https://example.org)</li>")

    def test_sitzung_waechst_per_htmx_unter_der_bleibenden_einleitung(self) -> None:
        """Die Sitzung wächst auf einer Seite, statt zwischen Seiten zu wechseln."""

        einleitung: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(einleitung, 'class="sitzung-seite"')
        self.assertContains(einleitung, 'id="sitzung-fortsetzung"')
        self.assertContains(einleitung, "rahmenhandlung-einstieg-w.webp")
        self.assertContains(einleitung, "gespraechsanlass-w.webp")
        self.assertContains(einleitung, 'id="eingabe"')
        self.assertNotContains(einleitung, "Diagnosegespräch beginnen")

        gespraech: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech"),
            headers={"HX-Request": "true"},
        )

        self.assertContains(gespraech, 'id="diagnosegespraech"')
        self.assertNotContains(gespraech, "<!DOCTYPE html>")

        debrief: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_beenden"),
            headers={"HX-Request": "true"},
        )

        self.assertContains(debrief, 'id="diagnosegespraech"')
        self.assertContains(debrief, 'id="sitzung-debrief"')
        self.assertContains(debrief, "rahmenhandlung-debrief-w.webp")
        self.assertNotContains(debrief, "<!DOCTYPE html>")

    def test_arbeitsheft_ordnet_text_und_bild_am_marker(self) -> None:
        """Das Gespräch zeigt den Arbeitshefttext um das Bild herum."""

        self.entwurf.arbeitsheft_text = (
            "Rechnung oben\n [BILD] \nRechnung unten\n[bild]"
        )
        self.entwurf.arbeitsheft_bild = "vignettenbilder/heft.gif"
        self.entwurf.arbeitsheft_bildbeschreibung = "Durchgestrichene Rechnung"
        self.entwurf.save()

        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))
        response: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech")
        )

        inhalt: str = response.content.decode()
        self.assertLess(inhalt.index("Rechnung oben"), inhalt.index("heft.gif"))
        self.assertLess(inhalt.index("heft.gif"), inhalt.index("Rechnung unten"))
        self.assertContains(response, 'alt="Durchgestrichene Rechnung"')
        self.assertNotContains(response, "[BILD]")

    def test_lernauftrag_ordnet_text_und_bild_am_marker(self) -> None:
        """Die Sitzungsseite zeigt den Lernauftrag um sein Bild herum."""

        self.entwurf.lernauftrag_text = "Oben\n[BILD]\nunten\n[bild]"
        self.entwurf.lernauftrag_bild = "vignettenbilder/auftrag.gif"
        self.entwurf.lernauftrag_bildbeschreibung = "Arbeitsblatt mit Zahlenreihe"
        self.entwurf.save()

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        inhalt: str = response.content.decode()
        self.assertLess(inhalt.index("Oben"), inhalt.index("auftrag.gif"))
        self.assertLess(inhalt.index("auftrag.gif"), inhalt.index("unten"))
        self.assertContains(response, 'alt="Arbeitsblatt mit Zahlenreihe"')
        self.assertNotContains(response, "[BILD]")

    def test_lernauftrag_rendert_die_teile_um_das_bild_je_als_szenentext(
        self,
    ) -> None:
        """Vor und nach dem Bild steht je ein eigener Szenentext, Alt-Text bleibt roh."""

        self.entwurf.lernauftrag_text = "**Oben**\n[bild]\n- unten"
        self.entwurf.lernauftrag_bild = "vignettenbilder/auftrag.gif"
        self.entwurf.lernauftrag_bildbeschreibung = "Reihe *1, 2, 3*"
        self.entwurf.save()

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(
            response,
            '<div class="markdown-text aufgabenkontext-inhalt">'
            "<p><strong>Oben</strong></p>\n</div>",
        )
        self.assertContains(
            response,
            '<div class="markdown-text aufgabenkontext-inhalt">'
            "<ul>\n<li>unten</li>\n</ul>\n</div>",
        )
        self.assertContains(response, 'alt="Reihe *1, 2, 3*"')

    def test_gespraech_kann_bereits_aus_der_einleitung_beendet_werden(self) -> None:
        """Auch ohne Gesprächsschritt ist der Debrief erreichbar."""

        einleitung: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(einleitung, "Gespräch beenden")
        debrief: HttpResponse = self.client.post(reverse("sitzungen:probelauf_beenden"))
        self.assertContains(debrief, "Frau Weber fragt nach Ihrer Diagnose.")

    def test_aktionszeile_im_probelauf_ohne_abbrechen(self) -> None:
        """Der Probelauf zeigt nur Erklärsatz und »Gespräch beenden →«."""

        einleitung: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertIn(("Gespräch beenden →", None), submit_knoepfe(einleitung))
        self.assertContains(
            einleitung, "Genug gefragt? Danach folgt der Debrief mit Ihrer Diagnose."
        )
        self.assertNotContains(einleitung, "Sitzung abbrechen")


class ProbelaufGespraechTests(_ProbelaufAufbau):
    """Die HTTP-Naht führt das Diagnosegespräch schreibfrei Zug um Zug."""

    def _erfolgreiche_antwort_konfigurieren(self) -> None:
        """Richtet den Fake für einen erfolgreichen Schritt ein."""

        self.konfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Mia addiert Zähler und Nenner.",
                        "aeusserung": "Ich addiere einfach alles.",
                    }
                ]
            },
        )
        ModellKonfiguration.objects.aktivieren(
            self.konfiguration, Verwendung.SCHUELERIN
        )

    def _budget_konfigurieren(
        self, budget_typ: Vignette.BudgetTyp, budget_wert: int
    ) -> None:
        """Setzt das Gesprächsbudget des Probelaufentwurfs."""

        self.entwurf.budget_typ = budget_typ
        self.entwurf.budget_wert = budget_wert
        self.entwurf.save()

    def _geglueckte_neben_fehlschlag_anlegen(self) -> ModellKonfiguration:
        # Belegt die Schülerin mit dem Fehlschlag und liefert eine geglückte
        # Konfiguration für den ersten Schritt. Der Fake beginnt sein Skript in
        # jedem Schritt neu, und der Probelauf pinnt seine Konfiguration.

        self.konfiguration = ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={"skript": _ENDGUELTIGER_FEHLSCHLAG},
        )
        ModellKonfiguration.objects.aktivieren(
            self.konfiguration, Verwendung.SCHUELERIN
        )
        return ModellKonfiguration.objects.create(
            bezeichnung="Geglückt",
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Mia addiert Zähler und Nenner.",
                        "aeusserung": "Ich addiere einfach alles.",
                    }
                ]
            },
        )

    def _endgueltigen_fehlschlag_ausloesen(
        self,
        eingabemodus: str = Eingabemodus.GETIPPT,
        geglueckt: ModellKonfiguration | None = None,
    ) -> HttpResponse:
        # Spielt einen geglückten ersten Schritt und lässt den zweiten scheitern.
        # Der erste Schritt läuft mit der geglückten Konfiguration über den
        # Durchlauf am Sink dieser Session.

        if geglueckt is None:
            geglueckt = self._geglueckte_neben_fehlschlag_anlegen()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))
        session: SessionBase = self.client.session
        gespraechsschritt_ausfuehren(
            ScratchSink(session),
            self.entwurf,
            self.kern,
            geglueckt,
            eingabe="Wie rechnest du?",
        )
        session.save()
        return self.client.post(
            reverse("sitzungen:probelauf_gespraech"),
            {"eingabe": "Und warum?", "eingabemodus": eingabemodus},
        )

    def test_simulationshinweise_erscheinen_nicht_auf_der_sitzungsseite(
        self,
    ) -> None:
        """Simulationshinweise erreichen keine Stelle der Sitzungsseite."""

        self._erfolgreiche_antwort_konfigurieren()
        self.entwurf.lernauftrag_text = "Löse die Aufgabe."
        self.entwurf.lernauftrag_simulationshinweise = (
            "Geheimer Hinweis zum Lernauftrag"
        )
        self.entwurf.arbeitsheft_text = "Meine Rechnung."
        self.entwurf.arbeitsheft_simulationshinweise = (
            "Geheimer Hinweis zum Arbeitsheft"
        )
        self.entwurf.save()

        # 1. Startseite des Probelaufs prüfen
        response_start: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )
        self.assertNotContains(response_start, "Geheimer Hinweis zum Lernauftrag")
        self.assertNotContains(response_start, "Geheimer Hinweis zum Arbeitsheft")

        # 2. Gesprächsseite des Probelaufs prüfen
        response_gespraech: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech")
        )
        self.assertNotContains(response_gespraech, "Geheimer Hinweis zum Lernauftrag")
        self.assertNotContains(response_gespraech, "Geheimer Hinweis zum Arbeitsheft")

    def test_spracheingabe_steht_schon_beim_ersten_schritt_bereit(self) -> None:
        """Auch das erste Eingabefeld trägt bereits den Aufnahme-Knopf."""

        einstieg: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(einstieg, "data-spracheingabe")
        self.assertContains(einstieg, "Frage aufnehmen")

    def test_spracheingabe_traegt_dieselbe_aufnahmegrenze_wie_der_endpunkt(
        self,
    ) -> None:
        """Der Browser zählt gegen die Grenze, die der Endpunkt danach hält."""

        with override_settings(TRANSKRIPTION_MAX_AUFNAHME_BYTES=1234):
            einstieg: HttpResponse = self.client.post(
                reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
            )

        self.assertContains(einstieg, 'data-maximale-bytes="1234"')

    def test_spracheingabe_steht_im_gespraech_und_im_debrief_bereit(self) -> None:
        """Der Probelauf bietet das Mikrofon ohne Einwilligungsschritt an."""

        self._erfolgreiche_antwort_konfigurieren()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        gespraech: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(gespraech, "data-spracheingabe")
        self.assertContains(gespraech, "Frage aufnehmen")

        debrief: HttpResponse = self.client.post(reverse("sitzungen:probelauf_beenden"))

        self.assertContains(debrief, "data-spracheingabe")
        self.assertContains(debrief, "Diagnose aufnehmen")

    def test_antwort_und_denkspur_werden_live_angezeigt(self) -> None:
        """Eingabe, Äußerung und Denkspur stehen in der Antwort (ADR-0005)."""

        self._erfolgreiche_antwort_konfigurieren()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        erste_antwort: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(erste_antwort, "Wie rechnest du?")
        self.assertContains(erste_antwort, "Ich addiere einfach alles.")
        self.assertContains(erste_antwort, "Mia addiert Zähler und Nenner.")

        zweite_antwort: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Und warum?"}
        )

        self.assertContains(zweite_antwort, "Wie rechnest du?")
        self.assertContains(zweite_antwort, "Und warum?")
        self.assertContains(zweite_antwort, "Ich addiere einfach alles.", count=2)

    def test_schrittbudget_fuehrt_nach_letztem_schritt_unsichtbar_in_den_debrief(
        self,
    ) -> None:
        """Der letzte erlaubte Gesprächsschritt endet erst nach seiner Antwort."""

        self._budget_konfigurieren(Vignette.BudgetTyp.SCHRITTE, 1)
        self._erfolgreiche_antwort_konfigurieren()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(response, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertContains(response, "Ich addiere einfach alles.")
        self.assertNotContains(response, "Budget")

        erneutes_oeffnen: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech")
        )

        self.assertContains(erneutes_oeffnen, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertNotContains(erneutes_oeffnen, "Ihre nächste Frage")

        with anfragen_aufzeichnen() as aufgezeichnet:
            erneuter_versuch: HttpResponse = self.client.post(
                reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Und warum?"}
            )

        self.assertContains(erneuter_versuch, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertEqual(aufgezeichnet, [])

        erneuter_aufruf: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech")
        )

        self.assertContains(erneuter_aufruf, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertNotContains(erneuter_aufruf, "Ihre nächste Frage")
        self.assertNotContains(erneuter_aufruf, "Und warum?")

    def test_zeitbudget_pausiert_waehrend_des_modellaufrufs(self) -> None:
        """Modellwartezeit erhöht den Zeitverbrauch des Probelaufs nicht."""

        self._budget_konfigurieren(Vignette.BudgetTyp.ZEIT, 5)
        self._erfolgreiche_antwort_konfigurieren()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        # 4 s Autorinnenzug, danach rechnet das Modell 100 s.
        with time_machine.travel(_GESPRAECHSBEGINN, tick=False) as uhr:
            self.client.get(reverse("sitzungen:probelauf_gespraech"))
            uhr.shift(4)
            with modellaufrufe_dauern(uhr, 100):
                response: HttpResponse = self.client.post(
                    reverse("sitzungen:probelauf_gespraech"),
                    {"eingabe": "Wie rechnest du?"},
                )

        self.assertContains(response, "Ich addiere einfach alles.")
        self.assertNotContains(response, "Budget")
        self.assertContains(response, "Ihre nächste Frage")

    def test_zeitbudget_pausiert_waehrend_endgueltiger_fehlversuche(self) -> None:
        """Fehlversuche des Modells kosten keine Zeit aus dem Autorinnenzug."""

        self._budget_konfigurieren(Vignette.BudgetTyp.ZEIT, 5)
        geglueckt: ModellKonfiguration = self._geglueckte_neben_fehlschlag_anlegen()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        # 4 s Autorinnenzug, danach kostet jeder Fehlversuch 100 s.
        with time_machine.travel(_GESPRAECHSBEGINN, tick=False) as uhr:
            self.client.get(reverse("sitzungen:probelauf_gespraech"))
            uhr.shift(4)
            with modellaufrufe_dauern(uhr, 100):
                response: HttpResponse = self.client.post(
                    reverse("sitzungen:probelauf_gespraech"),
                    {"eingabe": "Wie rechnest du?"},
                )

            session: SessionBase = self.client.session
            ausgang: Ausgang = gespraechsschritt_ausfuehren(
                ScratchSink(session),
                self.entwurf,
                self.kern,
                geglueckt,
                eingabe="Und warum?",
            )

        self.assertContains(response, "Die Antwort konnte nicht erzeugt werden.")
        self.assertNotContains(response, "Budget")
        self.assertEqual(ausgang, Ausgang.FORTGESETZT)

    def test_zeitbudget_fuehrt_nach_laufendem_schritt_in_den_debrief(self) -> None:
        """Ein abgelaufenes Zeitbudget schneidet die erzeugte Antwort nicht ab."""

        self._budget_konfigurieren(Vignette.BudgetTyp.ZEIT, 5)
        self._erfolgreiche_antwort_konfigurieren()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        with time_machine.travel(_GESPRAECHSBEGINN, tick=False) as uhr:
            self.client.get(reverse("sitzungen:probelauf_gespraech"))
            uhr.shift(5)
            response: HttpResponse = self.client.post(
                reverse("sitzungen:probelauf_gespraech"),
                {"eingabe": "Wie rechnest du?"},
            )

        self.assertContains(response, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertContains(response, "Ich addiere einfach alles.")

    def test_modellverlauf_traegt_beide_gespraechsseiten(self) -> None:
        """Beide Gesprächsseiten reisen als native Rollen zum Modell."""

        self._erfolgreiche_antwort_konfigurieren()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )
        with anfragen_aufzeichnen() as aufgezeichnet:
            self.client.post(
                reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Und warum so?"}
            )

        self.assertEqual(
            aufgezeichnet[-1][-3:],
            [
                {"role": "user", "content": "Wie rechnest du?"},
                {"role": "assistant", "content": "Ich addiere einfach alles."},
                {"role": "user", "content": "Und warum so?"},
            ],
        )

    def test_endgueltiger_fehlschlag_zeigt_fehlermeldung(self) -> None:
        """Ein endgültiger Fehlschlag wird an der Stelle des Schritts erklärt."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertContains(response, "Die Antwort konnte nicht erzeugt werden.")

    def test_endgueltiger_fehlschlag_zeigt_erneutes_senden(self) -> None:
        """Ein endgültiger Fehlschlag bietet das Wiederholen derselben Eingabe an."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertContains(response, "Erneut senden")

    def test_endgueltiger_fehlschlag_bewahrt_eingabe_fuer_wiederholung(self) -> None:
        """Ein endgültiger Fehlschlag bewahrt die Eingabe im Wiederholungsformular."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertContains(
            response,
            '<input type="hidden" name="eingabe" value="Und warum?">',
            html=True,
        )

    def test_endgueltiger_fehlschlag_bewahrt_den_eingabemodus_fuer_wiederholung(
        self,
    ) -> None:
        """Die Wiederholung schickt den Modus der ursprünglichen Eingabe mit (Spec: #122)."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen(
            Eingabemodus.TRANSKRIBIERT
        )

        self.assertContains(
            response,
            '<input type="hidden" name="eingabemodus" value="transkribiert">',
            html=True,
        )

    def test_endgueltiger_fehlschlag_zeigt_beenden_im_debrief(self) -> None:
        """Ein endgültiger Fehlschlag bietet das Beenden in den Debrief an."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertContains(response, "Gespräch beenden und Debrief anzeigen")

    def test_endgueltiger_fehlschlag_bewahrt_den_sichtbaren_verlauf(self) -> None:
        """Ein endgültiger Fehlschlag lässt vorherige Äußerungen sichtbar."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertContains(response, "Ich addiere einfach alles.")

    def test_endgueltiger_fehlschlag_verbirgt_fehlergrund(self) -> None:
        """Ein endgültiger Fehlschlag zeigt keine Fehlversuchsgründe an."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertNotContains(response, "Anbieterfehler")
        self.assertNotContains(response, "Rohtext vom Anbieter")

    def test_beenden_zeigt_debrief_nach_endgueltigem_fehlschlag(self) -> None:
        """Das Beenden führt nach einem endgültigen Fehlschlag in den Debrief."""

        self._endgueltigen_fehlschlag_ausloesen()

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_beenden")
        )

        self.assertContains(response, "Frau Weber fragt nach Ihrer Diagnose.")

    def test_beenden_zeigt_debrief_und_verwirft_diagnose_schreibfrei(self) -> None:
        """Der volle Probelauf endet im Debrief ohne eine Domänenspur (ADR-0014)."""

        def zeilen_zaehlen() -> list[int]:
            # Zählt die Zeilen jeder Domänentabelle, die ein Lauf beschreiben könnte.

            return [
                Vignette.objects.count(),
                Simulationskern.objects.count(),
                ModellKonfiguration.objects.count(),
                Teilnahme.objects.count(),
                Sitzung.objects.count(),
                Gespraechsschritt.objects.count(),
                Fehlversuch.objects.count(),
                Diagnose.objects.count(),
            ]

        geglueckt: ModellKonfiguration = self._geglueckte_neben_fehlschlag_anlegen()
        zeilen: list[int] = zeilen_zaehlen()
        self._endgueltigen_fehlschlag_ausloesen(geglueckt=geglueckt)

        debrief: HttpResponse = self.client.post(reverse("sitzungen:probelauf_beenden"))

        self.assertContains(debrief, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertContains(debrief, "Ihre Diagnose")
        ende: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_debrief"),
            {"diagnose": "Brüche werden addiert."},
        )

        self.assertRedirects(ende, reverse("vignetten:detail", args=[self.entwurf.pk]))
        self.assertFalse(probelauf_laeuft(self.client.session))
        self.assertEqual(zeilen_zaehlen(), zeilen)


class AdministratorinProbelaufTests(TestCase):
    """Die HTTP-Naht erlaubt Administrator:innen ein freies Probelauf-Tripel."""

    def setUp(self) -> None:
        """Legt ein administrativ frei kombinierbares Tripel an."""

        self.administratorin: Konto = konto_mit_rollen("admin", is_superuser=True)
        autorin: Konto = konto_mit_rollen("ada")
        self.kern_entwurf: Simulationskern = finaler_kern().bearbeiten()
        self.kern_entwurf.rahmenhandlung_einleitung = "$lehrperson_name begleitet Sie."
        self.kern_entwurf.rahmenhandlung_gespraechseinleitung = (
            "$schuelerin_name zeigt Ihnen das Arbeitsheft."
        )
        self.kern_entwurf.rahmenhandlung_debrief = (
            "$lehrperson_name beendet den Probelauf."
        )
        self.kern_entwurf.save()
        aktive_modell_konfiguration(Verwendung.SCHUELERIN)
        self.test_konfiguration: ModellKonfiguration = (
            ModellKonfiguration.objects.create(
                bezeichnung="Skript Bruchfehler",
                sprachmodell="fake",
                parameter={
                    "skript": [
                        {
                            "denkspur": "Sie zählt Zähler und Nenner.",
                            "aeusserung": "So.",
                        }
                    ]
                },
            )
        )
        self.vignette: Vignette = vignetten_entwurf(autorin)
        for feld, wert in {
            "fehlermuster_beschreibung": "Zähler und Nenner addieren",
            "lernauftrag_text": "Addiere Brüche.",
            "arbeitsheft_bildbeschreibung": "Eine Rechnung.",
            "arbeitsheft_text": "1/2 + 1/3 = 2/5",
            "schuelerin_name": "Mia",
            "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
            "lehrperson_name": "Weber",
            "lehrperson_geschlecht": Vignette.Geschlecht.WEIBLICH,
            "fach": "Mathematik",
            "thema": "Brüche",
            "klassenstufe": "5",
            "budget_typ": Vignette.BudgetTyp.SCHRITTE,
            "budget_wert": 3,
        }.items():
            setattr(self.vignette, feld, wert)
        self.vignette.save()
        self.vignette.finalisieren()
        self.gepinnter_kern_pk: int = self.vignette.gepinnter_kern_id
        self.client.force_login(self.administratorin)

    def test_administratorin_startet_freies_tripel_ohne_vignetten_pin_oder_aktive_konfiguration_zu_aendern(
        self,
    ) -> None:
        """Der freie Auswähler speichert das gewählte Tripel nur in der Session."""

        auswahl: HttpResponse = self.client.get(
            reverse("sitzungen:administratorin_probelauf_auswahl")
        )

        self.assertContains(
            auswahl,
            f'<option value="{self.kern_entwurf.pk}">'
            f"{self.kern_entwurf.pk} (Entwurf)</option>",
            html=True,
        )
        self.assertContains(
            auswahl,
            f'<option value="{self.test_konfiguration.pk}">'
            "Skript Bruchfehler (fake)</option>",
            html=True,
        )
        self.assertContains(
            auswahl,
            f'<option value="{self.vignette.pk}">'
            f"{self.vignette.pk}: Mathematik – Brüche</option>",
            html=True,
        )
        response: HttpResponse = self.client.post(
            reverse("sitzungen:administratorin_probelauf_starten"),
            {
                "kern_pk": self.kern_entwurf.pk,
                "modell_konfiguration_pk": self.test_konfiguration.pk,
                "vignette_pk": self.vignette.pk,
            },
        )

        self.assertContains(response, "Weber begleitet Sie.")
        self.assertContains(response, "Mia zeigt Ihnen das Arbeitsheft.")
        gespraech: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie?"}
        )
        self.assertContains(gespraech, "Sie zählt Zähler und Nenner.")
        debrief: HttpResponse = self.client.post(reverse("sitzungen:probelauf_beenden"))
        self.assertContains(debrief, "Weber beendet den Probelauf.")
        ende: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_debrief"), {"diagnose": "Bruchfehler"}
        )
        self.assertRedirects(
            ende, reverse("sitzungen:administratorin_probelauf_auswahl")
        )
        self.assertFalse(probelauf_laeuft(self.client.session))
        self.vignette.refresh_from_db()
        self.assertEqual(self.vignette.gepinnter_kern_id, self.gepinnter_kern_pk)
        self.assertNotEqual(
            ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN),
            self.test_konfiguration,
        )

    def test_nicht_administratorin_erreicht_freien_auswaehler_nicht(self) -> None:
        """Der administrative Einstieg ist ausschließlich der Group vorbehalten."""

        self.client.force_login(konto_mit_rollen("grace"))

        response: HttpResponse = self.client.get(
            reverse("sitzungen:administratorin_probelauf_auswahl")
        )

        self.assertEqual(response.status_code, 403)


class GeteiltesKontoTests(_ProbelaufAufbau):
    """Ein Konto trägt mehrere gleichzeitige Probeläufe in getrennten Browsern."""

    def test_zwei_anmeldungen_desselben_kontos_proben_unabhaengig(self) -> None:
        """Der Probelauf lebt in der Session, also je Browser statt je Konto."""

        ModellKonfiguration.objects.aktivieren(
            ModellKonfiguration.objects.create(
                bezeichnung="Test",
                sprachmodell="fake",
                parameter={
                    "skript": [
                        {"denkspur": "Mia rechnet ihre Regel.", "aeusserung": "So."}
                    ]
                },
            ),
            Verwendung.SCHUELERIN,
        )
        zweiter_entwurf: Vignette = vignetten_entwurf(self.ada)
        zweiter_entwurf.historie.name = "Zweiter Entwurf"
        zweiter_entwurf.historie.save()
        zweiter_entwurf.schuelerin_name = "Nora"
        zweiter_entwurf.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
        zweiter_entwurf.lehrperson_name = "Weber"
        zweiter_entwurf.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
        zweiter_entwurf.fach = "Mathematik"
        zweiter_entwurf.thema = "Dezimalzahlen"
        zweiter_entwurf.klassenstufe = "6"
        zweiter_entwurf.save()
        eins: Client = Client()
        zwei: Client = Client()
        eins.force_login(self.ada)
        zwei.force_login(self.ada)

        eins.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))
        zwei.post(reverse("sitzungen:probelauf_starten", args=[zweiter_entwurf.pk]))
        antwort_eins: HttpResponse = eins.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Frage aus Browser 1"}
        )
        antwort_zwei: HttpResponse = zwei.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Frage aus Browser 2"}
        )

        self.assertContains(antwort_eins, "Frage aus Browser 1")
        self.assertNotContains(antwort_eins, "Frage aus Browser 2")
        self.assertContains(antwort_zwei, "Frage aus Browser 2")
        self.assertNotContains(antwort_zwei, "Frage aus Browser 1")

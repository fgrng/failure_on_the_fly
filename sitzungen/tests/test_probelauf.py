"""HTTP-Tests für den schreibfreien Probelauf."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.sprachmodell import FakeSprachmodell
from sitzungen.models import Diagnose, Fehlversuch, Gespraechsschritt, Sitzung, Teilnahme
from vignetten.models import Vignette


_ENDGUELTIGER_FEHLSCHLAG: list[dict[str, str]] = [
    {"fehler": "anbieterfehler"},
    {"fehler": "anbieterfehler"},
    {"fehler": "anbieterfehler"},
]


class ProbelaufStartTests(TestCase):
    """Die HTTP-Naht startet einen Probelauf über einem festen Tripel."""

    def setUp(self) -> None:
        """Legt die sichtbaren und fremden Entwürfe für die HTTP-Tests an."""

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        self.kern: Simulationskern = Simulationskern.objects.anlegen(
            rahmenhandlung_einleitung=(
                "$lehrperson_anrede $lehrperson_name begleitet Sie bei "
                "$fach in Klasse $klassenstufe."
            ),
            rahmenhandlung_debrief=(
                "$lehrperson_anrede $lehrperson_name fragt nach Ihrer Diagnose."
            ),
        )
        self.kern.finalisieren()
        self.konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter={"skript": []}
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.entwurf: Vignette = Vignette.objects.anlegen(self.ada)
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
        fremder_entwurf: Vignette = Vignette.objects.anlegen(grace)
        fremder_entwurf.historie.name = "Fremder Entwurf"
        fremder_entwurf.historie.save()
        self.client.force_login(self.ada)

    def test_auswahl_zeigt_nur_eigene_entwuerfe_und_startet_rahmenhandlung(
        self,
    ) -> None:
        """Der Start pinnt das automatische Tripel in der Session und rendert einleitend."""

        auswahl: HttpResponse = self.client.get(reverse("sitzungen:probelauf_auswahl"))

        self.assertContains(auswahl, "Eigener Entwurf")
        self.assertNotContains(auswahl, "Fremder Entwurf")

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(response, "Frau Weber begleitet Sie bei Mathematik in Klasse 5.")
        self.assertContains(response, reverse("sitzungen:probelauf_gespraech"))
        gespraech: HttpResponse = self.client.get(reverse("sitzungen:probelauf_gespraech"))
        self.assertContains(gespraech, "Ihre Nachricht")
        session = self.client.session
        self.assertEqual(session["probelauf"], {
            "vignette_pk": self.entwurf.pk,
            "kern_pk": self.kern.pk,
            "modell_konfiguration_pk": self.konfiguration.pk,
            "gespraechsschritte": [],
        })

    def test_startzustand_ueberlebt_folge_request_ohne_domaenenschreiben(
        self,
    ) -> None:
        """Der Probelauf bleibt allein als Session-Zustand über mehrere Requests erhalten."""

        anzahl_vignetten: int = Vignette.objects.count()
        anzahl_kerne: int = Simulationskern.objects.count()
        anzahl_konfigurationen: int = ModellKonfiguration.objects.count()
        anzahl_teilnahmen: int = Teilnahme.objects.count()
        anzahl_sitzungen: int = Sitzung.objects.count()
        anzahl_gespraechsschritte: int = Gespraechsschritt.objects.count()
        anzahl_fehlversuche: int = Fehlversuch.objects.count()
        anzahl_diagnosen: int = Diagnose.objects.count()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        self.client.get(reverse("sitzungen:probelauf_auswahl"))

        self.assertEqual(self.client.session["probelauf"], {
            "vignette_pk": self.entwurf.pk,
            "kern_pk": self.kern.pk,
            "modell_konfiguration_pk": self.konfiguration.pk,
            "gespraechsschritte": [],
        })
        self.assertEqual(Vignette.objects.count(), anzahl_vignetten)
        self.assertEqual(Simulationskern.objects.count(), anzahl_kerne)
        self.assertEqual(ModellKonfiguration.objects.count(), anzahl_konfigurationen)
        self.assertEqual(Teilnahme.objects.count(), anzahl_teilnahmen)
        self.assertEqual(Sitzung.objects.count(), anzahl_sitzungen)
        self.assertEqual(Gespraechsschritt.objects.count(), anzahl_gespraechsschritte)
        self.assertEqual(Fehlversuch.objects.count(), anzahl_fehlversuche)
        self.assertEqual(Diagnose.objects.count(), anzahl_diagnosen)

    def test_gespraech_kann_bereits_aus_der_einleitung_beendet_werden(self) -> None:
        """Auch ohne Gesprächsschritt ist der Debrief erreichbar."""

        einleitung: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(einleitung, "Gespräch beenden")
        debrief: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_beenden")
        )
        self.assertContains(debrief, "Frau Weber fragt nach Ihrer Diagnose.")


class ProbelaufGespraechTests(ProbelaufStartTests):
    """Die HTTP-Naht führt das Diagnosegespräch schreibfrei Zug um Zug."""

    def _domaenenzeilen_zaehlen(self) -> tuple[int, int, int, int, int]:
        """Zählt die Probelauf-fremden Persistenzmodelle."""

        return (
            Teilnahme.objects.count(),
            Sitzung.objects.count(),
            Gespraechsschritt.objects.count(),
            Fehlversuch.objects.count(),
            Diagnose.objects.count(),
        )

    def _erfolgreiche_antwort_konfigurieren(self) -> None:
        """Richtet den Fake für einen erfolgreichen Schritt ein."""

        self.konfiguration = ModellKonfiguration.objects.create(
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
        ModellKonfiguration.objects.aktivieren(self.konfiguration)

    def _budget_konfigurieren(
        self, budget_typ: Vignette.BudgetTyp, budget_wert: int
    ) -> None:
        """Setzt das Gesprächsbudget des Probelaufentwurfs."""

        self.entwurf.budget_typ = budget_typ
        self.entwurf.budget_wert = budget_wert
        self.entwurf.save()

    def _endgueltigen_fehlschlag_ausloesen(self) -> HttpResponse:
        # Richtet einen gespeicherten Verlauf und den folgenden Fehlerfall ein.

        self.konfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter={"skript": _ENDGUELTIGER_FEHLSCHLAG}
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))
        session = self.client.session
        session["probelauf"]["gespraechsschritte"] = [
            {
                "reihenfolge": 1,
                "eingabe": "Wie rechnest du?",
                "denkspur": "Mia addiert Zähler und Nenner.",
                "aeusserung": "Ich addiere einfach alles.",
                "native_reasoning_spur": None,
                "fehlversuche": [],
            }
        ]
        session.save()
        return self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Und warum?"}
        )

    def test_antwort_und_denkspur_werden_live_angezeigt_und_in_session_behalten(
        self,
    ) -> None:
        """Nur Äußerungen erreichen den nächsten Modellaufruf."""

        self.konfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Mia addiert Zähler und Nenner.",
                        "aeusserung": "Ich rechne eins plus eins und zwei plus drei.",
                        "native_reasoning_spur": "native erste Spur",
                    },
                ]
            },
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        anzahl_vignetten: int = Vignette.objects.count()
        anzahl_kerne: int = Simulationskern.objects.count()
        anzahl_konfigurationen: int = ModellKonfiguration.objects.count()
        anzahl_teilnahmen: int = Teilnahme.objects.count()
        anzahl_sitzungen: int = Sitzung.objects.count()
        anzahl_gespraechsschritte: int = Gespraechsschritt.objects.count()
        anzahl_fehlversuche: int = Fehlversuch.objects.count()
        anzahl_diagnosen: int = Diagnose.objects.count()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        erste_antwort: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(erste_antwort, "Wie rechnest du?")
        self.assertContains(erste_antwort, "Ich rechne eins plus eins und zwei plus drei.")
        self.assertContains(erste_antwort, "Mia addiert Zähler und Nenner.")
        self.assertContains(erste_antwort, "native erste Spur")

        zweite_antwort: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Und warum?"}
        )

        self.assertContains(zweite_antwort, "Ich rechne eins plus eins und zwei plus drei.")
        self.assertEqual(self.client.session["probelauf"]["gespraechsschritte"], [
            {
                "reihenfolge": 1,
                "eingabe": "Wie rechnest du?",
                "denkspur": "Mia addiert Zähler und Nenner.",
                "aeusserung": "Ich rechne eins plus eins und zwei plus drei.",
                "native_reasoning_spur": "native erste Spur",
                "fehlversuche": [],
            },
            {
                "reihenfolge": 2,
                "eingabe": "Und warum?",
                "denkspur": "Mia addiert Zähler und Nenner.",
                "aeusserung": "Ich rechne eins plus eins und zwei plus drei.",
                "native_reasoning_spur": "native erste Spur",
                "fehlversuche": [],
            },
        ])
        zweiter_prompt: str = FakeSprachmodell.letzte_anfragen[-1][1]
        self.assertIn("Ich rechne eins plus eins und zwei plus drei.", zweiter_prompt)
        self.assertNotIn("Mia addiert Zähler und Nenner.", zweiter_prompt)
        self.assertEqual(Vignette.objects.count(), anzahl_vignetten)
        self.assertEqual(Simulationskern.objects.count(), anzahl_kerne)
        self.assertEqual(ModellKonfiguration.objects.count(), anzahl_konfigurationen)
        self.assertEqual(Teilnahme.objects.count(), anzahl_teilnahmen)
        self.assertEqual(Sitzung.objects.count(), anzahl_sitzungen)
        self.assertEqual(Gespraechsschritt.objects.count(), anzahl_gespraechsschritte)
        self.assertEqual(Fehlversuch.objects.count(), anzahl_fehlversuche)
        self.assertEqual(Diagnose.objects.count(), anzahl_diagnosen)

    def test_schrittbudget_fuehrt_nach_letztem_schritt_unsichtbar_in_den_debrief(
        self,
    ) -> None:
        """Der letzte erlaubte Gesprächsschritt endet erst nach seiner Antwort."""

        self._budget_konfigurieren(Vignette.BudgetTyp.SCHRITTE, 1)
        self._erfolgreiche_antwort_konfigurieren()
        domaenenzeilen: tuple[int, int, int, int, int] = self._domaenenzeilen_zaehlen()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertEqual(
            self.client.session["probelauf"]["status"],
            Sitzung.Status.ABGESCHLOSSEN,
        )
        self.assertContains(response, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertContains(response, "Ich addiere einfach alles.")
        self.assertNotContains(response, "Budget")
        self.assertEqual(
            self.client.session["probelauf"]["gespraechsschritte"][0]["aeusserung"],
            "Ich addiere einfach alles.",
        )
        self.assertEqual(self._domaenenzeilen_zaehlen(), domaenenzeilen)

        erneutes_oeffnen: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech")
        )

        self.assertContains(erneutes_oeffnen, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertNotContains(erneutes_oeffnen, "Ihre Nachricht")

        erneuter_versuch: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Und warum?"}
        )

        self.assertContains(erneuter_versuch, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertEqual(len(self.client.session["probelauf"]["gespraechsschritte"]), 1)

        erneuter_aufruf: HttpResponse = self.client.get(
            reverse("sitzungen:probelauf_gespraech")
        )

        self.assertContains(erneuter_aufruf, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertNotContains(erneuter_aufruf, "Ihre Nachricht")

    def test_zeitbudget_pausiert_waehrend_des_modellaufrufs(self) -> None:
        """Modellwartezeit erhöht den Zeitverbrauch des Probelaufs nicht."""

        self._budget_konfigurieren(Vignette.BudgetTyp.ZEIT, 5)
        self._erfolgreiche_antwort_konfigurieren()
        domaenenzeilen: tuple[int, int, int, int, int] = self._domaenenzeilen_zaehlen()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        with patch("sitzungen.sink.monotonic", side_effect=[10, 14, 114]):
            self.client.get(reverse("sitzungen:probelauf_gespraech"))
            response: HttpResponse = self.client.post(
                reverse("sitzungen:probelauf_gespraech"),
                {"eingabe": "Wie rechnest du?"},
            )

        self.assertContains(response, "Ich addiere einfach alles.")
        self.assertNotContains(response, "Budget")
        self.assertEqual(self.client.session["probelauf"]["verbrauchte_zeit"], 4)
        self.assertEqual(self._domaenenzeilen_zaehlen(), domaenenzeilen)

    def test_zeitbudget_pausiert_waehrend_endgueltiger_fehlversuche(self) -> None:
        """Fehlversuche des Modells kosten keine Zeit aus dem Autorinnenzug."""

        self._budget_konfigurieren(Vignette.BudgetTyp.ZEIT, 5)
        self.konfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter={"skript": _ENDGUELTIGER_FEHLSCHLAG}
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        domaenenzeilen: tuple[int, int, int, int, int] = self._domaenenzeilen_zaehlen()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        with patch("sitzungen.sink.monotonic", side_effect=[10, 14, 114]):
            self.client.get(reverse("sitzungen:probelauf_gespraech"))
            response: HttpResponse = self.client.post(
                reverse("sitzungen:probelauf_gespraech"),
                {"eingabe": "Wie rechnest du?"},
            )

        self.assertContains(response, "Die Antwort konnte nicht erzeugt werden.")
        self.assertNotContains(response, "Budget")
        self.assertEqual(self.client.session["probelauf"]["verbrauchte_zeit"], 4)
        self.assertEqual(self._domaenenzeilen_zaehlen(), domaenenzeilen)

    def test_zeitbudget_fuehrt_nach_laufendem_schritt_in_den_debrief(self) -> None:
        """Ein abgelaufenes Zeitbudget schneidet die erzeugte Antwort nicht ab."""

        self._budget_konfigurieren(Vignette.BudgetTyp.ZEIT, 5)
        self._erfolgreiche_antwort_konfigurieren()
        domaenenzeilen: tuple[int, int, int, int, int] = self._domaenenzeilen_zaehlen()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        with patch("sitzungen.sink.monotonic", side_effect=[10, 15]):
            self.client.get(reverse("sitzungen:probelauf_gespraech"))
            response: HttpResponse = self.client.post(
                reverse("sitzungen:probelauf_gespraech"),
                {"eingabe": "Wie rechnest du?"},
            )

        self.assertContains(response, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertEqual(
            self.client.session["probelauf"]["gespraechsschritte"][0]["aeusserung"],
            "Ich addiere einfach alles.",
        )
        self.assertEqual(self._domaenenzeilen_zaehlen(), domaenenzeilen)

    def test_native_reasoning_spur_fehlt_ohne_anbieterwert(self) -> None:
        """Die native Spur ist ein optionaler Zusatz zur immer sichtbaren Denkspur."""

        self.konfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Mia addiert Zähler und Nenner.",
                        "aeusserung": "Ich rechne eins plus eins und zwei plus drei.",
                    }
                ]
            },
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )

        self.assertContains(response, "Denkspur:")
        self.assertNotContains(response, "Native Reasoning-Spur:")

    def test_leere_aeusserung_bleibt_im_modellverlauf(self) -> None:
        """Auch eine leere sichtbare Äußerung ist Teil des Verlaufs."""

        self.konfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={"skript": [{"denkspur": "still", "aeusserung": ""}]},
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Erster Schritt"}
        )
        self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Zweiter Schritt"}
        )

        self.assertIn(
            "Verlauf:\n\n\nEingabe:\nZweiter Schritt",
            FakeSprachmodell.letzte_anfragen[-1][1],
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

    def test_endgueltiger_fehlschlag_zeigt_beenden_im_debrief(self) -> None:
        """Ein endgültiger Fehlschlag bietet das Beenden in den Debrief an."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertContains(response, "Gespräch beenden → Debrief")

    def test_endgueltiger_fehlschlag_bewahrt_den_sichtbaren_verlauf(self) -> None:
        """Ein endgültiger Fehlschlag lässt vorherige Äußerungen sichtbar."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertContains(response, "Ich addiere einfach alles.")

    def test_endgueltiger_fehlschlag_verbirgt_fehlergrund(self) -> None:
        """Ein endgültiger Fehlschlag zeigt keine Fehlversuchsgründe an."""

        response: HttpResponse = self._endgueltigen_fehlschlag_ausloesen()

        self.assertNotContains(response, "anbieterfehler")

    def test_beenden_zeigt_debrief_nach_endgueltigem_fehlschlag(self) -> None:
        """Das Beenden führt nach einem endgültigen Fehlschlag in den Debrief."""

        self._endgueltigen_fehlschlag_ausloesen()

        response: HttpResponse = self.client.post(reverse("sitzungen:probelauf_beenden"))

        self.assertContains(response, "Frau Weber fragt nach Ihrer Diagnose.")

    def test_beenden_zeigt_debrief_und_verwirft_diagnose_schreibfrei(self) -> None:
        """Der volle Probelauf endet im Debrief ohne eine Domänenspur."""

        self.konfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {
                        "denkspur": "Mia addiert Zähler und Nenner.",
                        "aeusserung": "Ich rechne eins plus eins und zwei plus drei.",
                    }
                ]
            },
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        anzahl_sitzungen: int = Sitzung.objects.count()
        anzahl_schritte: int = Gespraechsschritt.objects.count()
        anzahl_diagnosen: int = Diagnose.objects.count()

        einleitung: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )
        self.assertContains(einleitung, "Frau Weber begleitet Sie bei Mathematik in Klasse 5.")
        schritt: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie rechnest du?"}
        )
        self.assertContains(schritt, "Ich rechne eins plus eins und zwei plus drei.")
        self.assertContains(schritt, "Mia addiert Zähler und Nenner.")
        debrief: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_beenden")
        )

        self.assertContains(debrief, "Frau Weber fragt nach Ihrer Diagnose.")
        self.assertContains(debrief, "Ihre Diagnose")
        ende: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_debrief"), {"diagnose": "Brüche werden addiert."}
        )

        self.assertRedirects(ende, reverse("sitzungen:probelauf_auswahl"))
        self.assertNotIn("probelauf", self.client.session)
        self.assertEqual(Sitzung.objects.count(), anzahl_sitzungen)
        self.assertEqual(Gespraechsschritt.objects.count(), anzahl_schritte)
        self.assertEqual(Diagnose.objects.count(), anzahl_diagnosen)


class AdministratorinProbelaufTests(TestCase):
    """Die HTTP-Naht erlaubt Administrator:innen ein freies Probelauf-Tripel."""

    def setUp(self) -> None:
        """Legt ein administrativ frei kombinierbares Tripel an."""

        self.administratorin: Konto = get_user_model().objects.create_user(username="admin")
        self.administratorin.groups.add(Group.objects.get(name="Administrator:in"))
        autorin: Konto = get_user_model().objects.create_user(username="ada")
        finaler_kern: Simulationskern = Simulationskern.objects.anlegen()
        finaler_kern.finalisieren()
        self.kern_entwurf: Simulationskern = finaler_kern.bearbeiten()
        self.kern_entwurf.rahmenhandlung_einleitung = "$lehrperson_name begleitet Sie."
        self.kern_entwurf.rahmenhandlung_debrief = "$lehrperson_name beendet den Probelauf."
        self.kern_entwurf.save()
        aktive_konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake"
        )
        ModellKonfiguration.objects.aktivieren(aktive_konfiguration)
        self.test_konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake",
            parameter={
                "skript": [{"denkspur": "Sie zählt Zähler und Nenner.", "aeusserung": "So."}]
            },
        )
        self.vignette: Vignette = Vignette.objects.anlegen(autorin)
        for feld, wert in {
            "fehlermuster_beschreibung": "Zähler und Nenner addieren",
            "lernauftrag": "Addiere Brüche.",
            "arbeitsheft_beschreibung": "Eine Rechnung.",
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

        self.assertContains(auswahl, str(self.kern_entwurf.pk))
        self.assertContains(auswahl, str(self.test_konfiguration.pk))
        self.assertContains(auswahl, str(self.vignette.pk))
        response: HttpResponse = self.client.post(
            reverse("sitzungen:administratorin_probelauf_starten"),
            {
                "kern_pk": self.kern_entwurf.pk,
                "modell_konfiguration_pk": self.test_konfiguration.pk,
                "vignette_pk": self.vignette.pk,
            },
        )

        self.assertContains(response, "Weber begleitet Sie.")
        gespraech: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_gespraech"), {"eingabe": "Wie?"}
        )
        self.assertContains(gespraech, "Sie zählt Zähler und Nenner.")
        self.assertEqual(self.client.session["probelauf"]["kern_pk"], self.kern_entwurf.pk)
        debrief: HttpResponse = self.client.post(reverse("sitzungen:probelauf_beenden"))
        self.assertContains(debrief, "Weber beendet den Probelauf.")
        ende: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_debrief"), {"diagnose": "Bruchfehler"}
        )
        self.assertRedirects(
            ende, reverse("sitzungen:administratorin_probelauf_auswahl")
        )
        self.assertNotIn("probelauf", self.client.session)
        self.vignette.refresh_from_db()
        self.assertEqual(self.vignette.gepinnter_kern_id, self.gepinnter_kern_pk)
        self.assertNotEqual(ModellKonfiguration.objects.aktive(), self.test_konfiguration)

    def test_nicht_administratorin_erreicht_freien_auswaehler_nicht(self) -> None:
        """Der administrative Einstieg ist ausschließlich der Group vorbehalten."""

        self.client.force_login(get_user_model().objects.create_user(username="grace"))

        response: HttpResponse = self.client.get(
            reverse("sitzungen:administratorin_probelauf_auswahl")
        )

        self.assertEqual(response.status_code, 403)

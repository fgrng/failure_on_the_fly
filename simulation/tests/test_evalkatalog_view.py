"""HTTP-Tests für den Evalkatalog-Editor im System-Bereich."""

import re
from html.parser import HTMLParser

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen
from config.tests.formular import submit_knoepfe
from simulation.models import (
    Eval,
    Evalkatalog,
    Evalinput,
    Evalkriterium,
    Inputschritt,
    UebergreifendesKriterium,
)
from simulation.tests.evalkatalog_bau import vervollstaendigen, vollstaendiger_katalog


class EvalkatalogUebersichtTests(TestCase):
    """Die Systemseite bietet das Anlegen nur ohne Katalog an."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def test_ohne_katalog_bietet_die_seite_das_anlegen_an(self) -> None:
        """Eine Instanz startet ohne Katalog; die Seite sagt das und bietet an."""
        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertIn(("Evalkatalog anlegen", None), submit_knoepfe(response))

    def test_anlegen_oeffnet_den_editor_des_neuen_entwurfs(self) -> None:
        """Nach dem Anlegen steht die Administratorin im Editor des Entwurfs."""
        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_anlegen")
        )

        katalog: Evalkatalog = Evalkatalog.objects.get()
        self.assertRedirects(
            response, reverse("simulation:evalkatalog_editor", args=[katalog.pk])
        )

    def test_mit_entwurf_fuehrt_die_seite_zum_editor_statt_anzulegen(self) -> None:
        """Mit Entwurf gibt es kein zweites Anlegen, aber Bearbeiten und Verwerfen."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()

        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        knoepfe: list[str] = [text for text, _ in submit_knoepfe(response)]
        self.assertNotIn("Evalkatalog anlegen", knoepfe)
        self.assertIn("Entwurf verwerfen", knoepfe)
        self.assertContains(
            response, reverse("simulation:evalkatalog_editor", args=[katalog.pk])
        )

    def test_zweites_anlegen_wird_mit_meldung_abgelehnt(self) -> None:
        """Ein zweiter Entwurf entsteht auch per direktem POST nicht."""
        Evalkatalog.objects.anlegen()

        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_anlegen"), follow=True
        )

        self.assertContains(response, "Der Evalkatalog wurde bereits angelegt.")
        self.assertIn(("Entwurf verwerfen", None), submit_knoepfe(response))

    def test_verwerfen_loescht_den_entwurf(self) -> None:
        """Auch mit allen Teilen verworfen, ist die Linie leer und das Anlegen möglich."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        katalog.kriterium_anlegen("Rollentreue")
        eval_: Eval = katalog.eval_anlegen("Muster")
        eval_.kriterium_anlegen("A")
        eval_.input_anlegen()

        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_verwerfen", args=[katalog.pk]),
            follow=True,
        )

        self.assertIn(("Evalkatalog anlegen", None), submit_knoepfe(response))


class _Platzhaltersammler(HTMLParser):
    """Sammelt die Platzhalterknöpfe einer Seite je Zielfeld."""

    def __init__(self) -> None:
        super().__init__()
        self.knoepfe: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        werte: dict[str, str | None] = dict(attrs)
        name: str | None = werte.get("data-platzhalter")
        if tag == "button" and name:
            ziel: str = werte.get("data-ziel") or ""
            self.knoepfe.setdefault(ziel, []).append(name.removeprefix("$"))


def _platzhalter(response: HttpResponse) -> dict[str, list[str]]:
    """Die Namen der Platzhalterknöpfe je Zielfeld in Reihenfolge der Seite."""
    sammler: _Platzhaltersammler = _Platzhaltersammler()
    sammler.feed(response.content.decode())
    return sammler.knoepfe


class EvalkatalogEditorTests(TestCase):
    """Der Editor zeigt den Baum und den Knoten Durchlauf und Vorlagen."""

    def setUp(self) -> None:
        """Legt einen Entwurf an und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        self.url: str = reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def test_zeigt_den_baum_mit_dem_knoten_durchlauf_und_vorlagen(self) -> None:
        """Der Baum verlinkt den Knoten Durchlauf und Vorlagen als aktuellen."""
        response: HttpResponse = self.client.get(self.url)

        self.assertContains(
            response,
            f'<a href="{self.url}" aria-current="page">Durchlauf und Vorlagen</a>',
            html=True,
        )

    def test_zeigt_k_und_beide_vorlagen(self) -> None:
        """Das Formular trägt *k* mit Startwert 3 und beide Vorlagen."""
        response: HttpResponse = self.client.get(self.url)

        self.assertContains(response, 'name="k" value="3"')
        self.assertContains(response, 'name="lehrperson_vorlage"')
        self.assertContains(response, 'name="bewerter_vorlage"')

    def test_speichern_uebernimmt_die_werte(self) -> None:
        """Speichern schreibt *k* und beide Vorlagen in den Entwurf."""
        response: HttpResponse = self.client.post(
            self.url,
            {
                "k": "5",
                "lehrperson_vorlage": "Frage nach: $inputstrategie",
                "bewerter_vorlage": "Prüfe: $kriterium",
            },
        )

        self.assertRedirects(response, self.url)
        self.katalog.refresh_from_db()
        self.assertEqual(self.katalog.k, 5)
        self.assertEqual(self.katalog.lehrperson_vorlage, "Frage nach: $inputstrategie")
        self.assertEqual(self.katalog.bewerter_vorlage, "Prüfe: $kriterium")

    def test_platzhalterknoepfe_folgen_dem_vertrag_jeder_vorlage(self) -> None:
        """Je Vorlage steht ihr eigener Evalwert vorn, danach der Rest alphabetisch."""
        gemeinsam: list[str] = [
            "arbeitsheft",
            "arbeitsheft_simulationshinweise",
            "fach",
            "fehlermuster_beschreibung",
            "klassenstufe",
            "lernauftrag",
            "lernauftrag_simulationshinweise",
            "schuelerin_geschlecht",
            "schuelerin_name",
            "thema",
            "verlauf",
        ]

        knoepfe: dict[str, list[str]] = _platzhalter(self.client.get(self.url))

        self.assertEqual(
            knoepfe,
            {
                "id_lehrperson_vorlage": ["inputstrategie", *gemeinsam],
                "id_bewerter_vorlage": ["kriterium", *gemeinsam],
            },
        )

    def test_ungueltige_eingabe_bleibt_im_editor_ohne_zu_speichern(self) -> None:
        """Ohne gültiges *k* zeigt der Editor den Fehler und behält den alten Wert."""
        response: HttpResponse = self.client.post(
            self.url,
            {"k": "", "lehrperson_vorlage": "neu", "bewerter_vorlage": "neu"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get(self.url), 'name="k" value="3"')

    def test_speichern_schickt_das_editorformular(self) -> None:
        """Speichern schickt das Formular des Editors."""
        response: HttpResponse = self.client.get(self.url)

        self.assertIn(
            ("Änderungen speichern", "evalkatalog-formular"), submit_knoepfe(response)
        )

    def test_verworfener_entwurf_hat_keinen_editor(self) -> None:
        """Der Editor erreicht nur bestehende Entwürfe."""
        self.katalog.delete()

        response: HttpResponse = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)


class EvalkatalogKriterienTests(TestCase):
    """Der Knoten Übergreifende Kriterien pflegt die Rubriken aller Evals."""

    def setUp(self) -> None:
        """Legt einen Entwurf an und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        self.url: str = reverse(
            "simulation:evalkatalog_kriterien", args=[self.katalog.pk]
        )
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def _texte(self) -> list[str]:
        # Liefert die Texte der Kriterien des Entwurfs in gespeicherter Reihenfolge.
        return [k.text for k in self.katalog.uebergreifende_kriterien.all()]

    def test_baum_zeigt_den_knoten_mit_der_zahl_seiner_kriterien(self) -> None:
        """Der Baum nennt die Kriterien samt Zahl, auch im anderen Knoten."""
        self.katalog.kriterium_anlegen("A")
        self.katalog.kriterium_anlegen("B")

        response: HttpResponse = self.client.get(
            reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        )

        self.assertContains(response, f'href="{self.url}"')
        self.assertContains(response, "Übergreifende Kriterien (2)")

    def test_knoten_bietet_das_hinzufuegen_an(self) -> None:
        """Am Knoten hängt ein Knopf im Editorformular ein Kriterium an."""
        response: HttpResponse = self.client.get(self.url)

        self.assertIn(
            ("Kriterium hinzufügen", "evalkatalog-formular"),
            submit_knoepfe(response),
        )

    def test_hinzufuegen_haengt_ein_leeres_kriterium_an(self) -> None:
        """Ein neues Kriterium steht leer am Ende; die Texte bleiben erhalten."""
        kriterium = self.katalog.kriterium_anlegen("alt")

        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_kriterium_anlegen", args=[self.katalog.pk]),
            {f"kriterium-{kriterium.pk}": "Rollentreue"},
        )

        self.assertRedirects(response, self.url)
        self.assertEqual(self._texte(), ["Rollentreue", ""])

    def test_speichern_uebernimmt_die_texte(self) -> None:
        """Speichern schreibt jedes Kriterium; fremde Schlüssel bleiben folgenlos."""
        erstes = self.katalog.kriterium_anlegen("A")
        zweites = self.katalog.kriterium_anlegen("B")

        response: HttpResponse = self.client.post(
            self.url,
            {
                f"kriterium-{erstes.pk}": "Rollentreue",
                f"kriterium-{zweites.pk}": "Kein Verraten der Regel",
                "kriterium-999": "fremd",
            },
        )

        self.assertRedirects(response, self.url)
        self.assertEqual(self._texte(), ["Rollentreue", "Kein Verraten der Regel"])

    def test_loeschen_entfernt_das_kriterium(self) -> None:
        """Nach dem Löschen bleibt die übrige Liste in ihrer Reihenfolge."""
        self.katalog.kriterium_anlegen("A")
        zweites = self.katalog.kriterium_anlegen("B")
        self.katalog.kriterium_anlegen("C")

        self.client.post(
            reverse(
                "simulation:evalkatalog_kriterium_loeschen",
                args=[self.katalog.pk, zweites.pk],
            )
        )

        self.assertEqual(self._texte(), ["A", "C"])

    def test_hoch_und_runter_ordnen_um(self) -> None:
        """Die Reihenfolge bleibt nach dem Umordnen gespeichert."""
        erstes = self.katalog.kriterium_anlegen("A")
        self.katalog.kriterium_anlegen("B")
        drittes = self.katalog.kriterium_anlegen("C")

        for kriterium, richtung in ((drittes, "hoch"), (erstes, "runter")):
            self.client.post(
                reverse(
                    "simulation:evalkatalog_kriterium_verschieben",
                    args=[self.katalog.pk, kriterium.pk, richtung],
                )
            )

        self.assertEqual(self._texte(), ["C", "A", "B"])

    def test_hoch_an_der_ersten_zeile_aendert_nichts(self) -> None:
        """Am Rand der Liste bleibt die Reihenfolge, wie sie ist."""
        erstes = self.katalog.kriterium_anlegen("A")
        self.katalog.kriterium_anlegen("B")

        response: HttpResponse = self.client.post(
            reverse(
                "simulation:evalkatalog_kriterium_verschieben",
                args=[self.katalog.pk, erstes.pk, "hoch"],
            )
        )

        self.assertRedirects(response, self.url)
        self.assertEqual(self._texte(), ["A", "B"])

    def test_unbekannte_richtung_ist_nicht_erreichbar(self) -> None:
        """Nur hoch und runter verschieben ein Kriterium."""
        kriterium = self.katalog.kriterium_anlegen("A")

        response: HttpResponse = self.client.post(
            reverse(
                "simulation:evalkatalog_kriterium_verschieben",
                args=[self.katalog.pk, kriterium.pk, "seitwaerts"],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_hoch_an_der_ersten_runter_an_der_letzten_zeile_deaktiviert(self) -> None:
        """Am Rand der Liste ist der jeweilige Knopf gesperrt."""
        erstes = self.katalog.kriterium_anlegen("A")
        letztes = self.katalog.kriterium_anlegen("B")
        inhalt: str = self.client.get(self.url).content.decode()

        def knopf(kriterium: UebergreifendesKriterium, richtung: str) -> str:
            # Liefert das öffnende Tag des Verschiebeknopfs der Zeile.
            ziel: str = reverse(
                "simulation:evalkatalog_kriterium_verschieben",
                args=[self.katalog.pk, kriterium.pk, richtung],
            )
            return re.search(rf'<button[^>]*formaction="{ziel}"[^>]*>', inhalt)[0]

        self.assertIn("disabled", knopf(erstes, "hoch"))
        self.assertNotIn("disabled", knopf(erstes, "runter"))
        self.assertNotIn("disabled", knopf(letztes, "hoch"))
        self.assertIn("disabled", knopf(letztes, "runter"))

    def test_kriterium_eines_anderen_katalogs_ist_nicht_erreichbar(self) -> None:
        """Die Route verlangt, dass das Kriterium zum genannten Entwurf gehört."""
        self.katalog.kriterium_anlegen("A")
        vervollstaendigen(self.katalog).finalisieren()
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        fremd = self.katalog.uebergreifende_kriterien.get()

        for url in (
            reverse(
                "simulation:evalkatalog_kriterium_loeschen",
                args=[entwurf.pk, fremd.pk],
            ),
            reverse(
                "simulation:evalkatalog_kriterium_verschieben",
                args=[entwurf.pk, fremd.pk, "runter"],
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)


class EvalkatalogEvalTests(TestCase):
    """Evals stehen als eigene Knoten im Baum und tragen ihre Evalkriterien."""

    def setUp(self) -> None:
        """Legt einen Entwurf an und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def _knoten(self, eval_: Eval) -> str:
        # Die Adresse des Eval-Knotens im Editor.
        return reverse("simulation:evalkatalog_eval", args=[self.katalog.pk, eval_.pk])

    def _namen(self) -> list[str]:
        # Die Namen der Evals des Entwurfs in gespeicherter Reihenfolge.
        return [e.name for e in self.katalog.evals.all()]

    def test_hinzufuegen_legt_ein_eval_an_und_oeffnet_seinen_knoten(self) -> None:
        """Das neue Eval steht am Ende; der Knoten zeigt es zur Benennung."""
        self.katalog.eval_anlegen("Muster")

        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_eval_anlegen", args=[self.katalog.pk])
        )

        neues: Eval = self.katalog.evals.last()
        self.assertRedirects(response, self._knoten(neues))
        self.assertEqual(self._namen(), ["Muster", "Neues Eval"])
        self.assertContains(
            self.client.get(self._knoten(neues)), f'name="eval-{neues.pk}"'
        )

    def test_hinzufuegen_uebernimmt_die_getippten_eingaben(self) -> None:
        """Wer aus einem Knoten heraus ein Eval anlegt, verliert nichts."""
        kriterium: UebergreifendesKriterium = self.katalog.kriterium_anlegen("alt")

        self.client.post(
            reverse("simulation:evalkatalog_eval_anlegen", args=[self.katalog.pk]),
            {
                f"kriterium-{kriterium.pk}": "Rollentreue",
                "k": "7",
                "lehrperson_vorlage": "L",
                "bewerter_vorlage": "B",
            },
        )

        kriterium.refresh_from_db()
        self.katalog.refresh_from_db()
        self.assertEqual(kriterium.text, "Rollentreue")
        self.assertEqual(self.katalog.k, 7)

    def test_ungueltiger_durchlauf_wird_bei_jeder_geste_gemeldet(self) -> None:
        """Ein ungültiges *k* bleibt ungespeichert und wird genannt; gültige Vorlagen gelten."""
        for url in (
            reverse("simulation:evalkatalog_eval_anlegen", args=[self.katalog.pk]),
            reverse("simulation:evalkatalog_kriterien", args=[self.katalog.pk]),
        ):
            with self.subTest(url=url):
                response: HttpResponse = self.client.post(
                    url,
                    {"k": "-1", "lehrperson_vorlage": "L", "bewerter_vorlage": "B"},
                    follow=True,
                )

                self.assertContains(
                    response, "K: Dieser Wert muss größer oder gleich 0 sein."
                )
                self.assertNotContains(response, "Übergreifende Kriterien gespeichert.")
                self.katalog.refresh_from_db()
                self.assertEqual(self.katalog.k, 3)
                self.assertEqual(self.katalog.lehrperson_vorlage, "L")
                self.assertEqual(self.katalog.bewerter_vorlage, "B")

    def test_baum_zeigt_jedes_eval_in_seiner_reihenfolge(self) -> None:
        """Jedes Eval ist ein Knoten im Baum; der Baum folgt der Reihenfolge."""
        erstes: Eval = self.katalog.eval_anlegen("Muster")
        zweites: Eval = self.katalog.eval_anlegen("Rolle")
        zweites.verschieben(-1)

        inhalt: str = self.client.get(
            reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        ).content.decode()

        baum: str = inhalt[inhalt.index('class="evalkatalog-baum"') :]
        self.assertLess(
            baum.index(f'href="{self._knoten(zweites)}"'),
            baum.index(f'href="{self._knoten(erstes)}"'),
        )
        self.assertIn(
            ("Eval hinzufügen", "evalkatalog-formular"),
            submit_knoepfe(self.client.get(self._knoten(erstes))),
        )

    def test_speichern_benennt_das_eval_um_und_uebernimmt_die_kriterien(self) -> None:
        """Am Eval-Knoten speichert das Formular Name und Evalkriterien."""
        eval_: Eval = self.katalog.eval_anlegen("Neues Eval")
        kriterium: Evalkriterium = eval_.kriterium_anlegen("")

        response: HttpResponse = self.client.post(
            self._knoten(eval_),
            {
                f"eval-{eval_.pk}": "Muster bleibt stabil",
                f"evalkriterium-{kriterium.pk}": "Nennt die falsche Regel",
            },
        )

        self.assertRedirects(response, self._knoten(eval_))
        eval_.refresh_from_db()
        kriterium.refresh_from_db()
        self.assertEqual(eval_.name, "Muster bleibt stabil")
        self.assertEqual(kriterium.text, "Nennt die falsche Regel")

    def test_loeschen_fuehrt_zum_editor(self) -> None:
        """Nach dem Löschen steht die Administratorin wieder am Katalog."""
        eval_: Eval = self.katalog.eval_anlegen("Muster")
        eval_.kriterium_anlegen("A")
        self.katalog.eval_anlegen("Rolle")

        response: HttpResponse = self.client.post(
            reverse(
                "simulation:evalkatalog_eval_loeschen",
                args=[self.katalog.pk, eval_.pk],
            )
        )

        self.assertRedirects(
            response, reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        )
        self.assertEqual(self._namen(), ["Rolle"])

    def test_hoch_und_runter_ordnen_die_evals_um(self) -> None:
        """Am Eval-Knoten rückt das Eval eine Stelle; am Rand ist der Knopf gesperrt."""
        erstes: Eval = self.katalog.eval_anlegen("A")
        self.katalog.eval_anlegen("B")

        def knopf(richtung: str) -> str:
            # Das öffnende Tag des Verschiebeknopfs am Knoten des ersten Evals.
            ziel: str = reverse(
                "simulation:evalkatalog_eval_verschieben",
                args=[self.katalog.pk, erstes.pk, richtung],
            )
            inhalt: str = self.client.get(self._knoten(erstes)).content.decode()
            return re.search(rf'<button[^>]*formaction="{ziel}"[^>]*>', inhalt)[0]

        self.assertIn("disabled", knopf("hoch"))
        self.assertNotIn("disabled", knopf("runter"))

        response: HttpResponse = self.client.post(
            reverse(
                "simulation:evalkatalog_eval_verschieben",
                args=[self.katalog.pk, erstes.pk, "runter"],
            )
        )

        self.assertRedirects(response, self._knoten(erstes))
        self.assertEqual(self._namen(), ["B", "A"])
        self.assertIn("disabled", knopf("runter"))

    def test_evalkriterien_lassen_sich_anlegen_loeschen_und_umordnen(self) -> None:
        """Die Gesten am Eval-Knoten wirken nur auf dessen Kriterien."""
        eval_: Eval = self.katalog.eval_anlegen("Muster")
        anderes: Eval = self.katalog.eval_anlegen("Rolle")
        anderes.kriterium_anlegen("X")
        erstes: Evalkriterium = eval_.kriterium_anlegen("A")

        def route(name: str, *args: object) -> str:
            # Eine Kriterienroute am Eval-Knoten.
            return reverse(
                f"simulation:evalkatalog_evalkriterium_{name}",
                args=[self.katalog.pk, eval_.pk, *args],
            )

        response: HttpResponse = self.client.post(
            route("anlegen"), {f"evalkriterium-{erstes.pk}": "A1"}
        )
        self.assertRedirects(response, self._knoten(eval_))
        zweites: Evalkriterium = eval_.kriterien.last()
        self.client.post(route("anlegen"))
        self.client.post(route("verschieben", zweites.pk, "hoch"))
        self.client.post(route("loeschen", eval_.kriterien.last().pk))

        self.assertEqual([k.text for k in eval_.kriterien.all()], ["", "A1"])
        self.assertEqual([k.text for k in anderes.kriterien.all()], ["X"])

    def test_knoten_zeigt_die_evalkriterien_mit_gesten(self) -> None:
        """Jede Zeile trägt Hoch, Runter und Löschen; darunter das Hinzufügen."""
        eval_: Eval = self.katalog.eval_anlegen("Muster")
        kriterium: Evalkriterium = eval_.kriterium_anlegen("Nennt die falsche Regel")

        response: HttpResponse = self.client.get(self._knoten(eval_))

        self.assertContains(response, "Nennt die falsche Regel")
        knoepfe: list[tuple[str, str | None]] = submit_knoepfe(response)
        self.assertIn(("Evalkriterium hinzufügen", "evalkatalog-formular"), knoepfe)
        self.assertContains(
            response,
            reverse(
                "simulation:evalkatalog_evalkriterium_loeschen",
                args=[self.katalog.pk, eval_.pk, kriterium.pk],
            ),
        )

    def test_eval_und_kriterium_eines_anderen_katalogs_sind_nicht_erreichbar(
        self,
    ) -> None:
        """Eval und Kriterium müssen zum genannten Entwurf und Eval gehören."""
        eval_: Eval = self.katalog.eval_anlegen("Muster")
        kriterium: Evalkriterium = eval_.kriterium_anlegen("A")
        vervollstaendigen(self.katalog).finalisieren()
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        eigenes: Eval = entwurf.evals.get()

        for url in (
            reverse("simulation:evalkatalog_eval", args=[entwurf.pk, eval_.pk]),
            reverse(
                "simulation:evalkatalog_eval_loeschen", args=[entwurf.pk, eval_.pk]
            ),
            reverse(
                "simulation:evalkatalog_eval_verschieben",
                args=[entwurf.pk, eval_.pk, "runter"],
            ),
            reverse(
                "simulation:evalkatalog_evalkriterium_anlegen",
                args=[entwurf.pk, eval_.pk],
            ),
            reverse(
                "simulation:evalkatalog_evalkriterium_loeschen",
                args=[entwurf.pk, eigenes.pk, kriterium.pk],
            ),
            reverse(
                "simulation:evalkatalog_evalkriterium_verschieben",
                args=[entwurf.pk, eigenes.pk, kriterium.pk, "runter"],
            ),
            reverse(
                "simulation:evalkatalog_eval_verschieben",
                args=[entwurf.pk, eigenes.pk, "seitwaerts"],
            ),
            reverse(
                "simulation:evalkatalog_evalkriterium_verschieben",
                args=[entwurf.pk, eigenes.pk, eigenes.kriterien.get().pk, "seitwaerts"],
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)

    def test_kriterium_eines_anderen_evals_ist_nicht_erreichbar(self) -> None:
        """Die Kriteriengesten eines Evals greifen nicht auf seine Geschwister durch."""
        eval_: Eval = self.katalog.eval_anlegen("Muster")
        anderes: Eval = self.katalog.eval_anlegen("Rolle")
        fremdes: Evalkriterium = anderes.kriterium_anlegen("X")
        anderes.kriterium_anlegen("Y")

        for url in (
            reverse(
                "simulation:evalkatalog_evalkriterium_loeschen",
                args=[self.katalog.pk, eval_.pk, fremdes.pk],
            ),
            reverse(
                "simulation:evalkatalog_evalkriterium_verschieben",
                args=[self.katalog.pk, eval_.pk, fremdes.pk, "runter"],
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual([k.text for k in anderes.kriterien.all()], ["X", "Y"])

    def test_zu_langer_name_wird_nicht_gespeichert(self) -> None:
        """Ein Name über 200 Zeichen verletzt das Feld und bleibt ungespeichert."""
        eval_: Eval = self.katalog.eval_anlegen("Muster")

        self.client.post(self._knoten(eval_), {f"eval-{eval_.pk}": "x" * 201})

        eval_.refresh_from_db()
        self.assertEqual(eval_.name, "Muster")


class EvalkatalogEvalinputTests(TestCase):
    """Evalinputs hängen am Eval und werden als Drehbuch bearbeitet."""

    def setUp(self) -> None:
        """Legt einen Entwurf mit einem Eval an und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        self.eval_: Eval = self.katalog.eval_anlegen("Muster")
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def _route(self, name: str, *args: object) -> str:
        # Eine Route unterhalb des Evals.
        return reverse(
            f"simulation:evalkatalog_{name}",
            args=[self.katalog.pk, self.eval_.pk, *args],
        )

    def _schritte(self, evalinput: Evalinput) -> list[tuple[str, str]]:
        # Art und Text der Inputschritte in gespeicherter Reihenfolge.
        return [(s.art, s.text) for s in evalinput.schritte.all()]

    def test_hinzufuegen_legt_einen_weiteren_evalinput_an_und_oeffnet_ihn(self) -> None:
        """Am Eval-Knoten entsteht ein Evalinput nach dem anderen; sein Knoten öffnet sich."""
        self.assertIn(
            ("Evalinput hinzufügen", "evalkatalog-formular"),
            submit_knoepfe(self.client.get(self._route("eval"))),
        )

        self.client.post(self._route("evalinput_anlegen"))
        response: HttpResponse = self.client.post(self._route("evalinput_anlegen"))

        zweiter: Evalinput = self.eval_.inputs.last()
        self.assertRedirects(response, self._route("evalinput", zweiter.pk))
        self.assertEqual(self.eval_.inputs.count(), 2)

    def test_loeschen_entfernt_den_evalinput_und_fuehrt_zum_eval(self) -> None:
        """Nach dem Papierkorb am Evalinput steht die Administratorin am Eval."""
        evalinput: Evalinput = self.eval_.input_anlegen()

        response: HttpResponse = self.client.post(
            self._route("evalinput_loeschen", evalinput.pk)
        )

        self.assertRedirects(response, self._route("eval"))
        self.assertFalse(self.eval_.inputs.exists())

    def test_eval_knoten_listet_seine_evalinputs_mit_kuerzeln(self) -> None:
        """Am Eval führt je Evalinput ein Link samt F/G-Kürzel zu seinem Drehbuch."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        evalinput.schritt_anlegen(Inputschritt.Art.GELENKT)

        inhalt: str = self.client.get(self._route("eval")).content.decode()

        liste: str = inhalt[inhalt.index('class="evalkatalog-inputliste"') :]
        link: int = liste.index(f'href="{self._route("evalinput", evalinput.pk)}"')
        self.assertIn("FFFG", liste[link:])

    def test_speichern_uebernimmt_texte_und_arten(self) -> None:
        """Segmentknopf und Text jedes Schritts bleiben gespeichert."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        erster, zweiter, _ = evalinput.schritte.all()

        response: HttpResponse = self.client.post(
            self._route("evalinput", evalinput.pk),
            {
                f"inputschritt-{erster.pk}": "Wie rechnest du 3/4 + 1/2?",
                f"inputschritt-art-{erster.pk}": "fest",
                f"inputschritt-{zweiter.pk}": "Nennt sie die Lösung, äußere Zweifel.",
                f"inputschritt-art-{zweiter.pk}": "gelenkt",
            },
        )

        self.assertRedirects(response, self._route("evalinput", evalinput.pk))
        self.assertEqual(
            self._schritte(evalinput),
            [
                ("fest", "Wie rechnest du 3/4 + 1/2?"),
                ("gelenkt", "Nennt sie die Lösung, äußere Zweifel."),
                ("fest", ""),
            ],
        )

    def test_unbekannte_art_bleibt_ungespeichert(self) -> None:
        """Nur fest und gelenkt sind Arten eines Inputschritts."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        schritt: Inputschritt = evalinput.schritte.first()

        self.client.post(
            self._route("evalinput", evalinput.pk),
            {f"inputschritt-art-{schritt.pk}": "frei"},
        )

        schritt.refresh_from_db()
        self.assertEqual(schritt.art, Inputschritt.Art.FEST)

    def test_schritte_lassen_sich_anlegen_loeschen_und_umordnen(self) -> None:
        """Die Gesten am Drehbuch wirken nur auf die Schritte dieses Evalinputs."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        anderer: Evalinput = self.eval_.input_anlegen()
        erster: Inputschritt = evalinput.schritte.first()

        response: HttpResponse = self.client.post(
            self._route("inputschritt_anlegen", evalinput.pk),
            {f"inputschritt-{erster.pk}": "A"},
        )
        self.assertRedirects(response, self._route("evalinput", evalinput.pk))
        vierter: Inputschritt = evalinput.schritte.last()
        self.client.post(
            self._route("inputschritt_verschieben", evalinput.pk, vierter.pk, "hoch"),
            {f"inputschritt-{vierter.pk}": "D"},
        )
        self.client.post(self._route("inputschritt_loeschen", evalinput.pk, erster.pk))

        self.assertEqual([s.text for s in evalinput.schritte.all()], ["", "D", ""])
        self.assertEqual(anderer.schritte.count(), 3)

    def test_drehbuch_zeigt_schritte_antworten_und_gelenkte_blasen(self) -> None:
        """Zwischen den Schritten antwortet die Schüler:in; gelenkte sind markiert."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        schritte: list[Inputschritt] = list(evalinput.schritte.all())
        schritte[1].art = Inputschritt.Art.GELENKT
        schritte[1].text = "Äußere Zweifel."
        schritte[1].save()

        response: HttpResponse = self.client.get(self._route("evalinput", evalinput.pk))

        self.assertContains(response, "Schüler:in antwortet", count=3, html=True)
        self.assertContains(response, "sagt wörtlich")
        self.assertContains(response, "formuliert nach Strategie")
        self.assertContains(
            response,
            f'name="inputschritt-art-{schritte[1].pk}" value="gelenkt" checked',
        )
        self.assertIn(
            ("Inputschritt hinzufügen", "evalkatalog-formular"),
            submit_knoepfe(response),
        )

    def test_hoch_am_ersten_runter_am_letzten_schritt_deaktiviert(self) -> None:
        """Am Rand des Drehbuchs ist der jeweilige Verschiebeknopf gesperrt."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        erster, _, letzter = evalinput.schritte.all()
        inhalt: str = self.client.get(
            self._route("evalinput", evalinput.pk)
        ).content.decode()

        def knopf(schritt: Inputschritt, richtung: str) -> str:
            # Das öffnende Tag eines Verschiebeknopfs.
            ziel: str = self._route(
                "inputschritt_verschieben", evalinput.pk, schritt.pk, richtung
            )
            return re.search(rf'<button[^>]*formaction="{ziel}"[^>]*>', inhalt)[0]

        self.assertIn("disabled", knopf(erster, "hoch"))
        self.assertNotIn("disabled", knopf(erster, "runter"))
        self.assertIn("disabled", knopf(letzter, "runter"))

    def test_knoten_zeigt_die_evalkriterien_seines_evals(self) -> None:
        """Neben dem Drehbuch stehen die Kriterien, nach denen geurteilt wird."""
        self.eval_.kriterium_anlegen("Nennt die falsche Regel")
        self.katalog.eval_anlegen("Rolle").kriterium_anlegen("Bleibt in der Rolle")
        evalinput: Evalinput = self.eval_.input_anlegen()

        response: HttpResponse = self.client.get(self._route("evalinput", evalinput.pk))

        self.assertContains(response, "Nennt die falsche Regel")
        self.assertNotContains(response, "Bleibt in der Rolle")

    def test_baum_zeigt_die_evalinputs_je_eval_mit_kuerzeln(self) -> None:
        """Jeder Evalinput hängt unter seinem Eval, mit F/G je Schritt."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        evalinput.schritt_anlegen(Inputschritt.Art.GELENKT)
        anderes: Eval = self.katalog.eval_anlegen("Rolle")

        inhalt: str = self.client.get(
            reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        ).content.decode()

        baum: str = inhalt[inhalt.index('class="evalkatalog-baum"') :]
        link: int = baum.index(f'href="{self._route("evalinput", evalinput.pk)}"')
        self.assertLess(baum.index(f'href="{self._route("eval")}"'), link)
        self.assertLess(
            link,
            baum.index(
                reverse(
                    "simulation:evalkatalog_eval", args=[self.katalog.pk, anderes.pk]
                )
            ),
        )
        self.assertIn("FFFG", baum[link:])

    def test_fremde_evalinputs_und_schritte_sind_nicht_erreichbar(self) -> None:
        """Evalinput und Schritt müssen zum genannten Eval und Evalinput gehören."""
        evalinput: Evalinput = self.eval_.input_anlegen()
        fremder: Evalinput = self.katalog.eval_anlegen("Rolle").input_anlegen()
        fremder_schritt: Inputschritt = fremder.schritte.first()

        for url in (
            self._route("evalinput", fremder.pk),
            self._route("evalinput_loeschen", fremder.pk),
            self._route("inputschritt_anlegen", fremder.pk),
            self._route("inputschritt_loeschen", evalinput.pk, fremder_schritt.pk),
            self._route(
                "inputschritt_verschieben", evalinput.pk, fremder_schritt.pk, "runter"
            ),
            self._route(
                "inputschritt_verschieben",
                evalinput.pk,
                evalinput.schritte.first().pk,
                "seitwaerts",
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(fremder.schritte.count(), 3)


def _evalrouten(
    katalog: Evalkatalog, eval_: Eval, kriterium: Evalkriterium
) -> list[str]:
    """Alle Routen der Evals, Evalkriterien und Evalinputs eines Katalogs.

    Das Eval trägt einen Evalinput, dessen Routen dazugehören.
    """
    evalinput: Evalinput = eval_.inputs.get()
    schritt: Inputschritt = evalinput.schritte.first()
    return [
        reverse("simulation:evalkatalog_eval_anlegen", args=[katalog.pk]),
        reverse("simulation:evalkatalog_eval", args=[katalog.pk, eval_.pk]),
        reverse("simulation:evalkatalog_eval_loeschen", args=[katalog.pk, eval_.pk]),
        reverse(
            "simulation:evalkatalog_eval_verschieben",
            args=[katalog.pk, eval_.pk, "hoch"],
        ),
        reverse(
            "simulation:evalkatalog_evalkriterium_anlegen",
            args=[katalog.pk, eval_.pk],
        ),
        reverse(
            "simulation:evalkatalog_evalkriterium_loeschen",
            args=[katalog.pk, eval_.pk, kriterium.pk],
        ),
        reverse(
            "simulation:evalkatalog_evalkriterium_verschieben",
            args=[katalog.pk, eval_.pk, kriterium.pk, "hoch"],
        ),
        reverse(
            "simulation:evalkatalog_evalinput_anlegen", args=[katalog.pk, eval_.pk]
        ),
        reverse(
            "simulation:evalkatalog_evalinput",
            args=[katalog.pk, eval_.pk, evalinput.pk],
        ),
        reverse(
            "simulation:evalkatalog_evalinput_loeschen",
            args=[katalog.pk, eval_.pk, evalinput.pk],
        ),
        reverse(
            "simulation:evalkatalog_inputschritt_anlegen",
            args=[katalog.pk, eval_.pk, evalinput.pk],
        ),
        reverse(
            "simulation:evalkatalog_inputschritt_loeschen",
            args=[katalog.pk, eval_.pk, evalinput.pk, schritt.pk],
        ),
        reverse(
            "simulation:evalkatalog_inputschritt_verschieben",
            args=[katalog.pk, eval_.pk, evalinput.pk, schritt.pk, "runter"],
        ),
    ]


class EvalkatalogFinaleFassungTests(TestCase):
    """Eine finale Fassung ist kein Entwurf: kein Editor, kein Verwerfen."""

    def setUp(self) -> None:
        """Finalisiert eine Fassung und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        vervollstaendigen(self.katalog).finalisieren()
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def test_finale_fassung_nimmt_keine_eingaben_an(self) -> None:
        """Lesen ja, Speichern nein: Der Editor schreibt nur in Entwürfe."""
        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_editor", args=[self.katalog.pk]),
            {"k": "7", "lehrperson_vorlage": "x", "bewerter_vorlage": "y"},
        )

        self.assertEqual(response.status_code, 404)
        self.katalog.refresh_from_db()
        self.assertEqual(self.katalog.k, 3)

    def test_kriterienrouten_erreichen_nur_entwuerfe(self) -> None:
        """An einer finalen Fassung ändert keine Kriterienroute etwas."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        kriterium = entwurf.kriterium_anlegen("A")
        vervollstaendigen(entwurf).finalisieren()

        for url in (
            reverse("simulation:evalkatalog_kriterien", args=[entwurf.pk]),
            reverse("simulation:evalkatalog_kriterium_anlegen", args=[entwurf.pk]),
            reverse(
                "simulation:evalkatalog_kriterium_loeschen",
                args=[entwurf.pk, kriterium.pk],
            ),
            reverse(
                "simulation:evalkatalog_kriterium_verschieben",
                args=[entwurf.pk, kriterium.pk, "hoch"],
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(
            [k.text for k in entwurf.uebergreifende_kriterien.all()], ["A"]
        )

    def test_evalrouten_erreichen_nur_entwuerfe(self) -> None:
        """An einer finalen Fassung ändert keine Route eines Evals etwas."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        eval_: Eval = entwurf.eval_anlegen("Muster")
        kriterium: Evalkriterium = eval_.kriterium_anlegen("A")
        eval_.input_anlegen()
        vervollstaendigen(entwurf).finalisieren()

        for url in _evalrouten(entwurf, eval_, kriterium):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(
            [
                (e.name, [k.text for k in e.kriterien.all()])
                for e in entwurf.evals.all()
            ],
            # Das erste Eval stammt aus der vervollständigten Vorgängerin.
            [("Ergänzt", ["Ergänzt"]), ("Muster", ["A"])],
        )

    def test_evalrouten_erreichen_keine_ueberholte_fassung(self) -> None:
        """Auch eine überholte Fassung bleibt für die Routen der Evals gesperrt."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        eval_: Eval = entwurf.eval_anlegen("Muster")
        kriterium: Evalkriterium = eval_.kriterium_anlegen("A")
        eval_.input_anlegen()
        vervollstaendigen(entwurf).finalisieren()
        entwurf.bearbeiten().finalisieren()

        for url in _evalrouten(entwurf, eval_, kriterium):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)

    def test_finale_fassung_laesst_sich_nicht_verwerfen(self) -> None:
        """Verwerfen erreicht nur Entwürfe; die finale Fassung bleibt bestehen."""
        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_verwerfen", args=[self.katalog.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            ("Finale Fassung lesen", _editor(self.katalog)),
            _links(self.client.get(reverse("simulation:evalkatalog"))),
        )


class _Feldsammler(HTMLParser):
    """Sammelt die Eingabefelder einer Seite mit ihrer Sperre."""

    def __init__(self) -> None:
        super().__init__()
        self.felder: list[tuple[str | None, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        werte: dict[str, str | None] = dict(attrs)
        if tag in ("input", "textarea", "select") and werte.get("type") != "hidden":
            self.felder.append((werte.get("name"), "disabled" in werte))


def _felder(response: HttpResponse) -> list[tuple[str | None, bool]]:
    """Name und Sperre jedes sichtbaren Eingabefelds der Seite."""
    sammler: _Feldsammler = _Feldsammler()
    sammler.feed(response.content.decode())
    return sammler.felder


class _Linksammler(HTMLParser):
    """Sammelt die Links einer Seite mit ihrem Text."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str | None]] = []
        self._link: tuple[str | None, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._link = (dict(attrs).get("href"), [])

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link is not None:
            href, text = self._link
            self.links.append(("".join(text).strip(), href))
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._link is not None:
            self._link[1].append(data)


def _links(response: HttpResponse) -> list[tuple[str, str | None]]:
    """Text und Ziel jedes Links der Seite."""
    sammler: _Linksammler = _Linksammler()
    sammler.feed(response.content.decode())
    return sammler.links


def _editor(katalog: Evalkatalog) -> str:
    """Die Adresse des Editors bzw. der Lese-Ansicht einer Fassung."""
    return reverse("simulation:evalkatalog_editor", args=[katalog.pk])


def _editorknoepfe(response: HttpResponse) -> list[str]:
    """Die Beschriftungen der Submit-Knöpfe im Editor-Formular."""
    return [
        text
        for text, formular in submit_knoepfe(response)
        if formular == "evalkatalog-formular"
    ]


class EvalkatalogLeseansichtTests(TestCase):
    """Finale und überholte Fassungen öffnen sich gesperrt im Editor."""

    def setUp(self) -> None:
        """Finalisiert eine Fassung mit Kriterium und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        self.katalog.kriterium_anlegen("Rollentreu")
        self.eval_: Eval = self.katalog.eval_anlegen("Muster")
        self.eval_.input_anlegen().schritt_anlegen(Inputschritt.Art.GELENKT, "Zweifle")
        vervollstaendigen(self.katalog).finalisieren()
        self.evalinput: Evalinput = self.eval_.inputs.get()
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def _knoten(self, katalog: Evalkatalog) -> list[str]:
        # Die Adressen aller vier Knotenarten der Fassung.
        eval_: Eval = katalog.evals.get()
        return [
            reverse("simulation:evalkatalog_editor", args=[katalog.pk]),
            reverse("simulation:evalkatalog_kriterien", args=[katalog.pk]),
            reverse("simulation:evalkatalog_eval", args=[katalog.pk, eval_.pk]),
            reverse(
                "simulation:evalkatalog_evalinput",
                args=[katalog.pk, eval_.pk, eval_.inputs.get().pk],
            ),
        ]

    def test_jeder_knoten_zeigt_seine_werte_mit_gesperrten_feldern(self) -> None:
        """Alle Felder sind da, aber gesperrt; kein Knopf ändert etwas."""
        for url, inhalt in zip(
            self._knoten(self.katalog),
            ("Sprich mit $schuelerin_name", "Rollentreu", "Muster", "Zweifle"),
        ):
            with self.subTest(url=url):
                response: HttpResponse = self.client.get(url)

                self.assertContains(response, inhalt)
                felder: list[tuple[str | None, bool]] = _felder(response)
                self.assertTrue(felder)
                self.assertTrue(all(gesperrt for _, gesperrt in felder), felder)
                self.assertNotContains(response, "formaction=")
                self.assertNotContains(response, "data-platzhalter=")
                self.assertNotContains(response, "data-ungespeichert-warnen")
                self.assertEqual(_editorknoepfe(response), [])
                self.assertIn(
                    "Neue Fassung", [text for text, _ in submit_knoepfe(response)]
                )

    def test_finale_fassung_traegt_ein_hinweisband(self) -> None:
        """Das Band nennt den Zustand und seit wann die Fassung gilt."""
        response: HttpResponse = self.client.get(self._knoten(self.katalog)[0])

        self.assertContains(response, "Diese Fassung ist final")
        self.assertContains(response, "Finale Fassung lesen")

    def test_ueberholte_fassung_traegt_ein_hinweisband_ohne_neue_fassung(
        self,
    ) -> None:
        """Eine überholte Fassung lässt sich nur lesen; neu abgeleitet wird aus der finalen."""
        self.katalog.bearbeiten().finalisieren()

        for url in self._knoten(self.katalog):
            with self.subTest(url=url):
                response: HttpResponse = self.client.get(url)

                self.assertContains(response, "Diese Fassung ist überholt")
                self.assertContains(response, "Überholte Fassung lesen")
                self.assertEqual(_editorknoepfe(response), [])
                self.assertNotIn(
                    "Neue Fassung", [text for text, _ in submit_knoepfe(response)]
                )
                self.assertTrue(all(gesperrt for _, gesperrt in _felder(response)))

    def test_ueberholte_fassung_heisst_im_zustand_ueberholt(self) -> None:
        """Der Zustand im Kopf nennt die Fassung überholt, nicht archiviert."""
        self.katalog.bearbeiten().finalisieren()

        response: HttpResponse = self.client.get(self._knoten(self.katalog)[0])

        self.assertContains(response, '<span class="badge">Überholt</span>', html=True)

    def test_entwurf_bleibt_bearbeitbar(self) -> None:
        """Im Entwurf sind die Felder offen und ohne Hinweisband."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()

        for url in self._knoten(entwurf):
            with self.subTest(url=url):
                response: HttpResponse = self.client.get(url)

                self.assertNotContains(response, "Diese Fassung ist")
                self.assertFalse(any(gesperrt for _, gesperrt in _felder(response)))
                self.assertContains(response, "formaction=")

    def test_baum_der_lese_ansicht_fuehrt_zu_den_knoten_der_fassung(self) -> None:
        """Der Baum verlinkt die Knoten derselben Fassung."""
        response: HttpResponse = self.client.get(self._knoten(self.katalog)[0])

        for url in self._knoten(self.katalog)[1:]:
            self.assertContains(response, f'href="{url}"')

    def test_uebersicht_verlinkt_die_finale_fassung(self) -> None:
        """Die Systemseite führt zur Lese-Ansicht der finalen Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertContains(
            response,
            f'href="{reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])}"',
        )

    def test_uebersicht_listet_die_ueberholten_fassungen_neueste_zuerst(
        self,
    ) -> None:
        """Jede überholte Fassung steht mit Link zur Lese-Ansicht in der Liste."""
        zweite: Evalkatalog = self.katalog.bearbeiten()
        zweite.finalisieren()
        zweite.bearbeiten().finalisieren()

        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertContains(response, "Überholte Fassungen")
        inhalt: str = response.content.decode()
        links: list[str] = [
            reverse("simulation:evalkatalog_editor", args=[fassung.pk])
            for fassung in (zweite, self.katalog)
        ]
        positionen: list[int] = [inhalt.index(f'href="{link}"') for link in links]
        self.assertEqual(positionen, sorted(positionen))

    def test_ohne_ueberholte_fassung_fehlt_die_liste(self) -> None:
        """Solange nichts überholt ist, zeigt die Seite keine leere Liste."""
        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertNotContains(response, "Überholte Fassungen")


class EvalkatalogNeueFassungTests(TestCase):
    """Aus der finalen Fassung leitet die Administrator:in einen Entwurf ab."""

    def setUp(self) -> None:
        """Finalisiert eine Fassung und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = vollstaendiger_katalog()
        self.katalog.kriterium_anlegen("Rollentreu")
        # Abweichend vom Startwert 3, damit die Kopie von *k* sichtbar wird.
        self.katalog.k = 5
        self.katalog.finalisieren()
        self.url: str = reverse(
            "simulation:evalkatalog_neue_fassung", args=[self.katalog.pk]
        )
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def test_neue_fassung_oeffnet_den_editor_einer_tiefenkopie(self) -> None:
        """Der Editor des neuen Entwurfs zeigt *k* und Vorlagen der Vorgängerin."""
        response: HttpResponse = self.client.post(self.url, follow=True)

        entwurf: Evalkatalog = Evalkatalog.objects.get(
            zustand=Evalkatalog.Zustand.ENTWURF
        )
        self.assertRedirects(response, _editor(entwurf))
        self.assertContains(response, 'name="k" value="5"')
        self.assertContains(
            response, "Sprich mit $schuelerin_name nach $inputstrategie."
        )
        self.assertEqual(entwurf.vorgaengerin, self.katalog)

    def test_bei_bestehendem_entwurf_wird_keine_neue_fassung_abgeleitet(
        self,
    ) -> None:
        """Ein zweiter Entwurf wird mit Meldung abgelehnt."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()

        response: HttpResponse = self.client.post(self.url, follow=True)

        self.assertRedirects(response, reverse("simulation:evalkatalog"))
        self.assertContains(response, "Ein Evalkatalog-Entwurf existiert bereits.")
        self.assertEqual(
            list(Evalkatalog.objects.filter(zustand=Evalkatalog.Zustand.ENTWURF)),
            [entwurf],
        )

    def test_bei_bestehendem_entwurf_bieten_die_seiten_keine_neue_fassung_an(
        self,
    ) -> None:
        """Übersicht und Lese-Ansicht führen dann zum Entwurf statt abzuleiten."""
        self.katalog.bearbeiten()

        for url in (
            reverse("simulation:evalkatalog"),
            reverse("simulation:evalkatalog_editor", args=[self.katalog.pk]),
        ):
            with self.subTest(url=url):
                response: HttpResponse = self.client.get(url)

                self.assertNotIn(
                    "Neue Fassung", [text for text, _ in submit_knoepfe(response)]
                )

    def test_uebersicht_bietet_die_neue_fassung_an(self) -> None:
        """Ohne Entwurf steht „Neue Fassung“ bei der finalen Fassung."""
        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertIn("Neue Fassung", [text for text, _ in submit_knoepfe(response)])
        self.assertContains(response, f'action="{self.url}"')

    def test_neue_fassung_entsteht_nur_aus_der_finalen(self) -> None:
        """Entwürfe und überholte Fassungen erreicht die Route nicht."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        self.assertEqual(
            self.client.post(
                reverse("simulation:evalkatalog_neue_fassung", args=[entwurf.pk])
            ).status_code,
            404,
        )
        entwurf.finalisieren()

        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertEqual(Evalkatalog.objects.count(), 2)


class EvalkatalogFinalisierenTests(TestCase):
    """Der Editor finalisiert einen vollständigen Entwurf oder nennt die Lücken."""

    def setUp(self) -> None:
        """Legt einen vollständigen Entwurf an und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = vollstaendiger_katalog()
        self.url: str = reverse(
            "simulation:evalkatalog_finalisieren", args=[self.katalog.pk]
        )
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))

    def test_editor_bietet_das_finalisieren_im_formular_an(self) -> None:
        """Der Knopf steht in der Aktionszeile und schickt das ganze Formular."""
        response: HttpResponse = self.client.get(
            reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        )

        self.assertIn(
            ("Finalisieren", "evalkatalog-formular"), submit_knoepfe(response)
        )
        self.assertContains(response, f'formaction="{self.url}"')

    def test_vollstaendiger_entwurf_wird_final_und_ueberholt_die_vorgaengerin(
        self,
    ) -> None:
        """Nach dem Finalisieren gibt es genau eine finale Fassung."""
        vervollstaendigen(self.katalog).finalisieren()
        entwurf: Evalkatalog = self.katalog.bearbeiten()

        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_finalisieren", args=[entwurf.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("simulation:evalkatalog"))
        self.assertContains(response, "Der Evalkatalog ist final.")
        links: list[tuple[str, str | None]] = _links(response)
        self.assertIn(("Finale Fassung lesen", _editor(entwurf)), links)
        self.assertContains(response, "Überholte Fassungen")
        self.assertIn(_editor(self.katalog), [href for _, href in links])

    def test_unvollstaendiger_entwurf_bleibt_mit_meldungen_im_editor(self) -> None:
        """Jede Lücke erscheint als Meldung im Editor; der Entwurf bleibt Entwurf."""
        eval_: Eval = self.katalog.evals.get()
        eval_.kriterium_anlegen("")
        eval_.inputs.get().delete()

        response: HttpResponse = self.client.post(self.url, follow=True)

        self.assertRedirects(
            response, reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        )
        self.assertContains(response, "Eval „Ergänzt“ hat keinen Evalinput.")
        self.assertContains(response, "Evalkriterium 2 von Eval „Ergänzt“ ist leer.")
        self.katalog.refresh_from_db()
        self.assertEqual(self.katalog.zustand, Evalkatalog.Zustand.ENTWURF)

    def test_finalisieren_uebernimmt_zuerst_die_getippten_eingaben(self) -> None:
        """Was im Formular steht, gilt: auch ein frisch getippter Schritttext."""
        schritt: Inputschritt = Inputschritt.objects.get(
            evalinput__eval__katalog=self.katalog, position=1
        )
        schritt.text = ""
        schritt.save()

        self.client.post(self.url, {f"inputschritt-{schritt.pk}": "Erkläre es mir."})

        self.katalog.refresh_from_db()
        self.assertEqual(self.katalog.zustand, Evalkatalog.Zustand.FINAL)
        schritt.refresh_from_db()
        self.assertEqual(schritt.text, "Erkläre es mir.")

    def test_unerlaubter_platzhalter_wird_abgelehnt(self) -> None:
        """Die Meldung nennt den Platzhalter außerhalb des Vertrags."""
        response: HttpResponse = self.client.post(
            self.url,
            {
                "k": "3",
                "lehrperson_vorlage": "Prüfe $kriterium.",
                "bewerter_vorlage": "Prüfe $kriterium.",
            },
            follow=True,
        )

        self.assertContains(
            response,
            "Die Lehrperson-Vorlage enthält Platzhalter außerhalb ihres Vertrags: "
            "$kriterium.",
        )
        self.katalog.refresh_from_db()
        self.assertEqual(self.katalog.zustand, Evalkatalog.Zustand.ENTWURF)
        # Die getippte Vorlage bleibt gespeichert, damit sie sich korrigieren lässt.
        self.assertEqual(self.katalog.lehrperson_vorlage, "Prüfe $kriterium.")

    def test_ungueltiges_k_wird_abgelehnt_statt_uebergangen(self) -> None:
        """Ein getipptes *k* unter 1 lässt den Entwurf nie final werden."""
        response: HttpResponse = self.client.post(
            self.url,
            {
                "k": "-1",
                "lehrperson_vorlage": self.katalog.lehrperson_vorlage,
                "bewerter_vorlage": self.katalog.bewerter_vorlage,
            },
            follow=True,
        )

        self.assertRedirects(
            response, reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        )
        self.assertIsNone(Evalkatalog.objects.finale_fassung())

    def test_finale_fassung_wird_nicht_erneut_finalisiert(self) -> None:
        """Die Route erreicht nur Entwürfe."""
        self.katalog.finalisieren()

        self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_uebersicht_ohne_finale_fassung_nennt_keine(self) -> None:
        """Solange nichts finalisiert ist, gibt es nur den Entwurf zu verwerfen."""
        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertEqual(
            submit_knoepfe(response),
            [("Abmelden", None), ("Entwurf verwerfen", None)],
        )
        self.assertNotIn("Finale Fassung lesen", [text for text, _ in _links(response)])

    def test_uebersicht_nennt_die_finale_fassung(self) -> None:
        """Die Systemseite zeigt, seit wann der Katalog final ist."""
        self.katalog.finalisieren()

        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertContains(response, "Finale Fassung")
        self.assertNotIn(
            "Evalkatalog anlegen", [text for text, _ in submit_knoepfe(response)]
        )


class EvalkatalogZugriffTests(TestCase):
    """Nur Administrator:innen erreichen die Routen des Evalkatalogs."""

    def test_autorinnen_erhalten_auf_keiner_route_zugriff(self) -> None:
        """Auch die Entwicklungsrolle bekommt 403, lesend wie schreibend."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        kriterium = katalog.kriterium_anlegen("A")
        eval_: Eval = katalog.eval_anlegen("Muster")
        evalkriterium: Evalkriterium = eval_.kriterium_anlegen("B")
        eval_.input_anlegen()
        self.client.force_login(konto_mit_rollen("bea", "Autor:in"))

        for url in (
            reverse("simulation:evalkatalog"),
            reverse("simulation:evalkatalog_anlegen"),
            reverse("simulation:evalkatalog_editor", args=[katalog.pk]),
            reverse("simulation:evalkatalog_verwerfen", args=[katalog.pk]),
            reverse("simulation:evalkatalog_finalisieren", args=[katalog.pk]),
            reverse("simulation:evalkatalog_neue_fassung", args=[katalog.pk]),
            reverse("simulation:evalkatalog_kriterien", args=[katalog.pk]),
            reverse("simulation:evalkatalog_kriterium_anlegen", args=[katalog.pk]),
            reverse(
                "simulation:evalkatalog_kriterium_loeschen",
                args=[katalog.pk, kriterium.pk],
            ),
            reverse(
                "simulation:evalkatalog_kriterium_verschieben",
                args=[katalog.pk, kriterium.pk, "hoch"],
            ),
            *_evalrouten(katalog, eval_, evalkriterium),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Evalkatalog.objects.exists())
        self.assertTrue(katalog.uebergreifende_kriterien.filter(text="A").exists())
        self.assertEqual(
            [
                (e.name, [k.text for k in e.kriterien.all()])
                for e in katalog.evals.all()
            ],
            [("Muster", ["B"])],
        )

    def test_aenderungsrouten_nehmen_nur_post_an(self) -> None:
        """Ein GET ändert weder die Linie noch die Kriterien."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        kriterium = katalog.kriterium_anlegen("A")
        eval_: Eval = katalog.eval_anlegen("Muster")
        evalkriterium: Evalkriterium = eval_.kriterium_anlegen("B")
        evalinput: Evalinput = eval_.input_anlegen()
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))
        # Die Knoten von Eval und Evalinput zeigen sich auch per GET.
        knoten: set[str] = {
            reverse("simulation:evalkatalog_eval", args=[katalog.pk, eval_.pk]),
            reverse(
                "simulation:evalkatalog_evalinput",
                args=[katalog.pk, eval_.pk, evalinput.pk],
            ),
        }

        for url in (
            reverse("simulation:evalkatalog_anlegen"),
            reverse("simulation:evalkatalog_verwerfen", args=[katalog.pk]),
            reverse("simulation:evalkatalog_finalisieren", args=[katalog.pk]),
            reverse("simulation:evalkatalog_neue_fassung", args=[katalog.pk]),
            reverse("simulation:evalkatalog_kriterium_anlegen", args=[katalog.pk]),
            reverse(
                "simulation:evalkatalog_kriterium_loeschen",
                args=[katalog.pk, kriterium.pk],
            ),
            reverse(
                "simulation:evalkatalog_kriterium_verschieben",
                args=[katalog.pk, kriterium.pk, "runter"],
            ),
            *(
                url
                for url in _evalrouten(katalog, eval_, evalkriterium)
                if url not in knoten
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

    def test_sidebar_markiert_den_evalkatalog_auf_jedem_knoten(self) -> None:
        """Auch auf den Knoten Kriterien, Eval und Evalinput gilt der Link als aktuell."""
        self.client.force_login(konto_mit_rollen("ada", is_superuser=True))
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        eval_: Eval = katalog.eval_anlegen("Muster")
        evalinput: Evalinput = eval_.input_anlegen()
        link: str = (
            f'<a href="{reverse("simulation:evalkatalog")}" aria-current="page">'
            "Evalkatalog</a>"
        )

        for url in (
            reverse("simulation:evalkatalog_kriterien", args=[katalog.pk]),
            reverse("simulation:evalkatalog_eval", args=[katalog.pk, eval_.pk]),
            reverse(
                "simulation:evalkatalog_evalinput",
                args=[katalog.pk, eval_.pk, evalinput.pk],
            ),
        ):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), link, html=True)

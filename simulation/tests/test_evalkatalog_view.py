"""HTTP-Tests für den Evalkatalog-Editor im System-Bereich."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.formular import submit_knoepfe
from konten.models import Konto
from simulation.models import (
    VERTRAG_PROMPT,
    Eval,
    Evalkatalog,
    Evalinput,
    Evalkriterium,
    Inputschritt,
    UebergreifendesKriterium,
)


def _administratorin(username: str) -> Konto:
    """Legt ein Konto mit Zugriff auf den Evalkatalog an."""
    return get_user_model().objects.create_user(username=username, is_superuser=True)


class EvalkatalogUebersichtTests(TestCase):
    """Die Systemseite bietet das Anlegen nur ohne Katalog an."""

    def setUp(self) -> None:
        """Meldet eine Administratorin an."""
        self.client.force_login(_administratorin("ada"))

    def test_ohne_katalog_bietet_die_seite_das_anlegen_an(self) -> None:
        """Eine Instanz startet ohne Katalog; die Seite sagt das und bietet an."""
        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertIn(("Evalkatalog anlegen", None), submit_knoepfe(response))

    def test_verwerfen_nimmt_die_kriterien_des_entwurfs_mit(self) -> None:
        """Ein Entwurf mit übergreifenden Kriterien lässt sich verwerfen."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        katalog.kriterium_anlegen("Rollentreue")

        self.client.post(reverse("simulation:evalkatalog_verwerfen", args=[katalog.pk]))

        self.assertFalse(UebergreifendesKriterium.objects.exists())

    def test_verwerfen_nimmt_die_evals_samt_evalkriterien_mit(self) -> None:
        """Ein Entwurf mit Evals und Evalkriterien lässt sich verwerfen."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        katalog.eval_anlegen("Muster").kriterium_anlegen("A")

        self.client.post(reverse("simulation:evalkatalog_verwerfen", args=[katalog.pk]))

        self.assertFalse(Evalkriterium.objects.exists())

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

        self.assertEqual(Evalkatalog.objects.count(), 1)
        self.assertContains(response, "Der Evalkatalog wurde bereits angelegt.")

    def test_verwerfen_loescht_den_entwurf(self) -> None:
        """Nach dem Verwerfen ist die Linie leer und das Anlegen wieder möglich."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()

        response: HttpResponse = self.client.post(
            reverse("simulation:evalkatalog_verwerfen", args=[katalog.pk]),
            follow=True,
        )

        self.assertFalse(Evalkatalog.objects.exists())
        self.assertIn(("Evalkatalog anlegen", None), submit_knoepfe(response))


class EvalkatalogEditorTests(TestCase):
    """Der Editor zeigt den Baum und den Knoten Durchlauf und Vorlagen."""

    def setUp(self) -> None:
        """Legt einen Entwurf an und meldet eine Administratorin an."""
        self.katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        self.url: str = reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        self.client.force_login(_administratorin("ada"))

    def test_zeigt_den_baum_mit_dem_knoten_durchlauf_und_vorlagen(self) -> None:
        """Links steht der Baum mit dem Knoten Durchlauf und Vorlagen."""
        response: HttpResponse = self.client.get(self.url)

        self.assertContains(response, 'class="evalkatalog-baum"')
        self.assertContains(response, "Durchlauf und Vorlagen")

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

    def test_platzhalterknoepfe_heben_die_vorlageneigenen_hervor(self) -> None:
        """Je Vorlage steht ihr Vertrag als Knöpfe; der eigene Wert ist markiert."""
        response: HttpResponse = self.client.get(self.url)

        self.assertContains(
            response,
            'data-platzhalter="$inputstrategie" data-ziel="id_lehrperson_vorlage"'
            ' class="evalkatalog-platzhalter evalkatalog-platzhalter--eigen"',
        )
        self.assertContains(
            response,
            'data-platzhalter="$kriterium" data-ziel="id_bewerter_vorlage"'
            ' class="evalkatalog-platzhalter evalkatalog-platzhalter--eigen"',
        )
        self.assertNotContains(
            response, 'data-platzhalter="$kriterium" data-ziel="id_lehrperson_vorlage"'
        )
        self.assertNotContains(
            response,
            'data-platzhalter="$inputstrategie" data-ziel="id_bewerter_vorlage"',
        )
        for ziel in ("id_lehrperson_vorlage", "id_bewerter_vorlage"):
            self.assertContains(
                response,
                f'data-platzhalter="$verlauf" data-ziel="{ziel}"'
                ' class="evalkatalog-platzhalter"',
            )
            for name in VERTRAG_PROMPT:
                self.assertContains(
                    response, f'data-platzhalter="${name}" data-ziel="{ziel}"'
                )
        self.assertContains(response, "js/platzhalter.js")

    def test_der_vorlageneigene_platzhalter_steht_vorn(self) -> None:
        """Vor den übrigen, alphabetisch geordneten Knöpfen steht der eigene."""
        inhalt: str = self.client.get(self.url).content.decode()

        for ziel, eigener in (
            ("id_lehrperson_vorlage", "inputstrategie"),
            ("id_bewerter_vorlage", "kriterium"),
        ):
            with self.subTest(ziel=ziel):
                namen: list[str] = re.findall(
                    rf'data-platzhalter="\$(\w+)" data-ziel="{ziel}"', inhalt
                )
                self.assertEqual(namen, [eigener, *sorted(namen[1:])])

    def test_ungueltige_eingabe_bleibt_im_editor_ohne_zu_speichern(self) -> None:
        """Ohne gültiges *k* zeigt der Editor den Fehler und behält den alten Wert."""
        response: HttpResponse = self.client.post(
            self.url,
            {"k": "", "lehrperson_vorlage": "neu", "bewerter_vorlage": "neu"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get(self.url), 'name="k" value="3"')

    def test_aktionszeile_steht_am_formularende_und_klebt(self) -> None:
        """Abbrechen und Speichern stehen im Markup zuletzt; die CSS hebt sie an."""
        response: HttpResponse = self.client.get(self.url)
        inhalt: str = response.content.decode()

        self.assertContains(response, "css/vignette-form.css")
        formularende: int = inhalt.index(
            "</form>", inhalt.index('id="evalkatalog-formular"')
        )
        aktionen: int = inhalt.index('class="vignette-form-actions"')
        self.assertLess(aktionen, formularende)
        self.assertNotIn("<section", inhalt[aktionen:formularende])
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
        self.client.force_login(_administratorin("ada"))

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

    def test_knoten_zeigt_den_hinweis_zur_kern_neutralitaet(self) -> None:
        """Die Pflegeregel aus ADR-0046 steht am Knoten."""
        response: HttpResponse = self.client.get(self.url)

        self.assertContains(response, "kern-neutral")
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
        self.katalog.finalisieren()
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
        self.client.force_login(_administratorin("ada"))

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

    def test_loeschen_nimmt_die_evalkriterien_mit(self) -> None:
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
        self.assertFalse(Evalkriterium.objects.exists())

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
        self.katalog.finalisieren()
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
        self.client.force_login(_administratorin("ada"))

    def _route(self, name: str, *args: object) -> str:
        # Eine Route unterhalb des Evals.
        return reverse(
            f"simulation:evalkatalog_{name}",
            args=[self.katalog.pk, self.eval_.pk, *args],
        )

    def _schritte(self, evalinput: Evalinput) -> list[tuple[str, str]]:
        # Art und Text der Inputschritte in gespeicherter Reihenfolge.
        return [(s.art, s.text) for s in evalinput.schritte.all()]

    def test_hinzufuegen_legt_einen_evalinput_mit_drei_schritten_an(self) -> None:
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
        self.assertEqual(self._schritte(zweiter), [(Inputschritt.Art.FEST, "")] * 3)

    def test_loeschen_entfernt_den_evalinput_und_fuehrt_zum_eval(self) -> None:
        """Der Papierkorb am Evalinput nimmt seine Schritte mit."""
        evalinput: Evalinput = self.eval_.input_anlegen()

        response: HttpResponse = self.client.post(
            self._route("evalinput_loeschen", evalinput.pk)
        )

        self.assertRedirects(response, self._route("eval"))
        self.assertFalse(Inputschritt.objects.exists())

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

        inhalt: str = response.content.decode()
        self.assertEqual(
            inhalt.count('<p class="drehbuch__antwort">Schüler:in antwortet</p>'), 3
        )
        self.assertEqual(inhalt.count("drehbuch__blase--gelenkt"), 1)
        self.assertContains(response, "sagt wörtlich")
        self.assertContains(response, "formuliert nach Strategie")
        self.assertRegex(
            inhalt,
            rf'name="inputschritt-art-{schritte[1].pk}" value="gelenkt" checked',
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
        self.katalog.finalisieren()
        self.client.force_login(_administratorin("ada"))

    def test_finale_fassung_hat_keinen_editor(self) -> None:
        """Der Editor erreicht nur Entwürfe."""
        response: HttpResponse = self.client.get(
            reverse("simulation:evalkatalog_editor", args=[self.katalog.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_kriterienrouten_erreichen_nur_entwuerfe(self) -> None:
        """An einer finalen Fassung ändert keine Kriterienroute etwas."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        kriterium = entwurf.kriterium_anlegen("A")
        entwurf.finalisieren()

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
        entwurf.finalisieren()

        for url in _evalrouten(entwurf, eval_, kriterium):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(
            [
                (e.name, [k.text for k in e.kriterien.all()])
                for e in entwurf.evals.all()
            ],
            [("Muster", ["A"])],
        )

    def test_evalrouten_erreichen_keine_ueberholte_fassung(self) -> None:
        """Auch eine überholte Fassung bleibt für die Routen der Evals gesperrt."""
        entwurf: Evalkatalog = self.katalog.bearbeiten()
        eval_: Eval = entwurf.eval_anlegen("Muster")
        kriterium: Evalkriterium = eval_.kriterium_anlegen("A")
        eval_.input_anlegen()
        entwurf.finalisieren()
        entwurf.bearbeiten().finalisieren()

        for url in _evalrouten(entwurf, eval_, kriterium):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)

    def test_finale_fassung_laesst_sich_nicht_verwerfen(self) -> None:
        """Verwerfen erreicht nur Entwürfe; die finale Fassung bleibt bestehen."""
        self.client.post(
            reverse("simulation:evalkatalog_verwerfen", args=[self.katalog.pk])
        )

        self.assertTrue(Evalkatalog.objects.filter(pk=self.katalog.pk).exists())


class EvalkatalogZugriffTests(TestCase):
    """Nur Administrator:innen erreichen die Routen des Evalkatalogs."""

    def test_autorinnen_erhalten_auf_keiner_route_zugriff(self) -> None:
        """Auch die Entwicklungsrolle bekommt 403, lesend wie schreibend."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        kriterium = katalog.kriterium_anlegen("A")
        eval_: Eval = katalog.eval_anlegen("Muster")
        evalkriterium: Evalkriterium = eval_.kriterium_anlegen("B")
        eval_.input_anlegen()
        autorin: Konto = get_user_model().objects.create_user(username="bea")
        autorin.groups.add(Group.objects.get(name="Autor:in"))
        self.client.force_login(autorin)

        for url in (
            reverse("simulation:evalkatalog"),
            reverse("simulation:evalkatalog_anlegen"),
            reverse("simulation:evalkatalog_editor", args=[katalog.pk]),
            reverse("simulation:evalkatalog_verwerfen", args=[katalog.pk]),
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
        self.client.force_login(_administratorin("ada"))
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

    def test_sidebar_fuehrt_administratorinnen_zum_evalkatalog(self) -> None:
        """Der System-Bereich der Sidebar verlinkt den Evalkatalog."""
        self.client.force_login(_administratorin("ada"))

        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertContains(response, f'href="{reverse("simulation:evalkatalog")}"')

"""HTTP-Tests für den Evalkatalog-Editor im System-Bereich."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.formular import submit_knoepfe
from konten.models import Konto
from simulation.models import VERTRAG_PROMPT, Evalkatalog, UebergreifendesKriterium


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

    def test_hoch_an_der_ersten_runter_an_der_letzten_zeile_deaktiviert(self) -> None:
        """Am Rand der Liste ist der jeweilige Knopf gesperrt."""
        erstes = self.katalog.kriterium_anlegen("A")
        letztes = self.katalog.kriterium_anlegen("B")
        inhalt: str = self.client.get(self.url).content.decode()

        def knopf(kriterium: UebergreifendesKriterium, richtung: str) -> str:
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

        response: HttpResponse = self.client.post(
            reverse(
                "simulation:evalkatalog_kriterium_loeschen",
                args=[entwurf.pk, fremd.pk],
            )
        )

        self.assertEqual(response.status_code, 404)


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
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Evalkatalog.objects.exists())
        self.assertTrue(katalog.uebergreifende_kriterien.filter(text="A").exists())

    def test_aenderungsrouten_nehmen_nur_post_an(self) -> None:
        """Ein GET ändert weder die Linie noch die Kriterien."""
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
        kriterium = katalog.kriterium_anlegen("A")
        self.client.force_login(_administratorin("ada"))

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
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

    def test_sidebar_fuehrt_administratorinnen_zum_evalkatalog(self) -> None:
        """Der System-Bereich der Sidebar verlinkt den Evalkatalog."""
        self.client.force_login(_administratorin("ada"))

        response: HttpResponse = self.client.get(reverse("simulation:evalkatalog"))

        self.assertContains(response, f'href="{reverse("simulation:evalkatalog")}"')

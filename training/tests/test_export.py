"""HTTP-Tests des Trainingsexports (ADR-0049)."""

from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.urls import reverse
from django.utils.text import slugify

from konten.models import Konto
from konten.navigation import AUSBILDERIN_GRUPPE
from sitzungen.models import Fehlversuch, Gespraechsschritt, Sitzung
from training.models import Abschrift, Training
from training.tests.test_freigabe import _abschrift
from training.tests.test_fremdeinsicht import (
    FremdeinsichtTestCase,
    _gespielte_sitzung,
    _konto,
)


class TrainingsexportTestCase(FremdeinsichtTestCase):
    """Lädt den Trainingsexport herunter und liest das Archiv aus."""

    def setUp(self) -> None:
        super().setUp()
        self.teilnehmerin.email = "grace@example.org"
        self.teilnehmerin.save(update_fields=["email"])

    def _export(self, konto: Konto | None = None) -> HttpResponse:
        # Lädt den Export des Trainings aus Sicht des Kontos.
        self.client.force_login(konto or self.ausbilderin)
        return self.client.get(
            reverse("training:trainingsexport", args=[self.training.pk])
        )

    def _freigeben(self, abschrift: Abschrift, *trainings: Training) -> None:
        # Speichert die Freigaben der Abschrift aus Sicht ihres Kontos.
        self.client.force_login(abschrift.konto)
        self.client.post(
            reverse("training:abschrift_freigaben", args=[abschrift.pk]),
            {"training": [training.pk for training in trainings]},
        )

    def _archiv(self) -> dict[str, str]:
        # Die Dateien des heruntergeladenen Archivs mit ihrem Text.
        response: HttpResponse = self._export()
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(response.content)) as zip_datei:
            return {
                name: zip_datei.read(name).decode() for name in zip_datei.namelist()
            }

    def _ordner(self, archiv: dict[str, str]) -> set[str]:
        # Die Kennzeichen der obersten Ordner.
        return {name.split("/")[0] for name in archiv}


class ZugriffTests(TrainingsexportTestCase):
    """Wer den Export ziehen darf."""

    def test_kreis_laedt_ein_zip_herunter(self) -> None:
        """Die Antwort ist ein ZIP als Download."""
        response: HttpResponse = self._export()

        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment;", response["Content-Disposition"])

    def test_administration_laedt_den_export(self) -> None:
        """Die Administration zieht den Export jedes Trainings."""
        administratorin: Konto = _konto("root", is_superuser=True)

        self.assertEqual(self._export(administratorin).status_code, 200)

    def test_ko_eigentuemerin_laedt_den_export(self) -> None:
        """Jedes Kreismitglied zieht den Export."""
        ko: Konto = _konto("katherine", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(ko)

        self.assertEqual(self._export(ko).status_code, 200)

    def test_fremde_ausbilderin_bekommt_404(self) -> None:
        """Ein fremder Kreis erfährt nichts über das Training."""
        fremde: Konto = _konto("hedy", AUSBILDERIN_GRUPPE)

        self.assertEqual(self._export(fremde).status_code, 404)

    def test_neues_kreismitglied_laedt_auch_aeltere_sitzungen(self) -> None:
        """Der Export folgt der aktuellen Mitgliedschaft, auch rückwirkend."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        neues_mitglied: Konto = _konto("katherine", AUSBILDERIN_GRUPPE)
        self.training.eigentuemerinnen.add(neues_mitglied)

        response: HttpResponse = self._export(neues_mitglied)

        with ZipFile(BytesIO(response.content)) as zip_datei:
            self.assertEqual(len(zip_datei.namelist()), 1)

    def test_ausgetretenes_kreismitglied_bekommt_404(self) -> None:
        """Wer den Kreis verlässt, zieht sofort keinen Export mehr."""
        self.training.eigentuemerinnen.add(_konto("katherine", AUSBILDERIN_GRUPPE))
        self.training.austreten(self.ausbilderin.pk)

        self.assertEqual(self._export(self.ausbilderin).status_code, 404)

    def test_autorin_der_vignette_bekommt_404(self) -> None:
        """Autorschaft der Vignette begründet keinen Export, auch mit Rolle."""
        self.autorin.groups.add(Group.objects.get(name=AUSBILDERIN_GRUPPE))

        self.assertEqual(self._export(self.autorin).status_code, 404)

    def test_teilnehmerin_bekommt_403(self) -> None:
        """Eine Beigetretene ohne Rolle zieht keinen Export."""
        self.assertEqual(self._export(self.teilnehmerin).status_code, 403)

    def test_dateiname_nennt_training_und_zeitpunkt(self) -> None:
        """Der Download heißt nach Training und UTC-Zeitstempel."""
        response: HttpResponse = self._export()

        self.assertRegex(
            response["Content-Disposition"],
            rf'^attachment; filename="training-{self.training.pk}-'
            rf'{slugify(self.training.name)}-\d{{8}}T\d{{6}}Z\.zip"$',
        )

    def test_kuratierseite_bietet_den_export_an(self) -> None:
        """Der Knopf steht in der Werkzeugleiste der Fremdeinsicht."""
        self.client.force_login(self.ausbilderin)

        response: HttpResponse = self.client.get(
            reverse("training:kuratieren", args=[self.training.pk])
        )

        self.assertContains(
            response, reverse("training:trainingsexport", args=[self.training.pk])
        )
        self.assertContains(response, "Trainingsexport (ZIP)")
        self.assertContains(response, "pseudonym, nicht anonym")


class InhaltTests(TrainingsexportTestCase):
    """Was im Archiv steht."""

    def test_je_abgeschlossener_sitzung_eine_markdown_datei(self) -> None:
        """Zwei Sitzungen derselben Person liegen in einem Ordner."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)

        archiv: dict[str, str] = self._archiv()

        self.assertEqual(len(archiv), 2)
        self.assertEqual(len(self._ordner(archiv)), 1)
        self.assertTrue(all(name.endswith(".md") for name in archiv))

    def test_je_person_ein_eigener_ordner(self) -> None:
        """Bearbeitungen verschiedener Personen liegen getrennt."""
        zweite: Konto = _konto("margaret")
        self.training.beitreten(zweite)
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        _gespielte_sitzung(self.training, zweite, self.vignette)

        archiv: dict[str, str] = self._archiv()

        self.assertEqual(len(self._ordner(archiv)), 2)

    def test_dateien_sind_gezaehlt_und_nach_der_vignette_benannt(self) -> None:
        """Mehrere Durchläufe derselben Vignette tragen eine laufende Nummer."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)

        archiv: dict[str, str] = self._archiv()

        self.assertEqual(
            sorted(name.split("/", 1)[1] for name in archiv),
            ["01-brüche-addieren.md", "02-brüche-addieren.md"],
        )

    def test_ordner_heissen_nach_kennzeichen(self) -> None:
        """Der Ordner trägt ein Kennzeichen, keinen Namen."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)

        (ordner,) = self._ordner(self._archiv())

        self.assertRegex(ordner, r"^teilnehmer-[0-9a-f]+$")

    def test_datei_enthaelt_vignette_ausgang_transkript_und_diagnose(self) -> None:
        """Dasselbe wie in der Fremdeinsicht, als Markdown."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)

        (text,) = self._archiv().values()

        self.assertIn("# Brüche addieren", text)
        self.assertIn("Abgeschlossen", text)
        self.assertIn("Wie hast du gerechnet?", text)
        self.assertIn("Ich habe oben und unten zusammengezählt.", text)
        self.assertIn("Zähler und Nenner addiert.", text)

    def test_sitzung_ohne_zeitstempel_kommt_ohne_datum_hinaus(self) -> None:
        """Eine Bestandssitzung ohne Entstehungszeitpunkt nennt kein Datum."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        sitzung.erstellt_am = None
        sitzung.save(update_fields=["erstellt_am"])

        (text,) = self._archiv().values()

        self.assertNotIn("Datum:", text)

    def test_schritt_ohne_aeusserung_ist_als_solcher_markiert(self) -> None:
        """Ein endgültig gescheiterter Schritt bleibt im Transkript sichtbar."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        Gespraechsschritt.objects.answerless_anlegen(
            sitzung=sitzung,
            eingabe="Und jetzt?",
            reihenfolge=2,
            fehlversuche=[Fehlversuch(grund="Timeout", rohantwort="")],
        )

        (text,) = self._archiv().values()

        self.assertIn("**Äußerung:** (keine Antwort)", text)

    def test_sitzung_ohne_diagnose_ist_als_solche_markiert(self) -> None:
        """Fehlt die Diagnose, sagt der Abschnitt das ausdrücklich."""
        _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        ).diagnose.delete()

        (text,) = self._archiv().values()

        self.assertIn("## Diagnose\n\n(keine Diagnose)", text)

    def test_transkript_wechselt_eingabe_und_aeusserung(self) -> None:
        """Die Schritte stehen in ihrer Reihenfolge, Eingabe vor Äußerung."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        Gespraechsschritt.objects.create(
            sitzung=sitzung,
            eingabe="Und jetzt?",
            denkspur="Zweite Denkspur.",
            aeusserung="Jetzt kürze ich.",
            reihenfolge=2,
        )

        (text,) = self._archiv().values()

        reihenfolge: list[int] = [
            text.index(stelle)
            for stelle in (
                "Wie hast du gerechnet?",
                "Ich habe oben und unten zusammengezählt.",
                "Und jetzt?",
                "Jetzt kürze ich.",
            )
        ]
        self.assertEqual(reihenfolge, sorted(reihenfolge))

    def test_nicht_abgeschlossene_sitzungen_fehlen(self) -> None:
        """Laufend, abgebrochen und gescheitert gehen nicht hinaus."""
        for status in (
            Sitzung.Status.LAUFEND,
            Sitzung.Status.ABGEBROCHEN,
            Sitzung.Status.GESCHEITERT,
        ):
            _gespielte_sitzung(
                self.training,
                self.teilnehmerin,
                self.vignette,
                status,
                aeusserung=f"Antwort {status}",
            )

        self.assertEqual(self._archiv(), {})

    def test_sitzung_in_einem_fremden_training_fehlt(self) -> None:
        """Einsicht folgt dem Anlass, nicht der Vignette."""
        fremdes: Training = Training.objects.anlegen(
            _konto("hedy", AUSBILDERIN_GRUPPE), name="Fremd"
        )
        fremdes.vignetten.add(self.vignette)
        fremdes.veroeffentlichen()
        _gespielte_sitzung(fremdes, self.teilnehmerin, self.vignette)

        self.assertEqual(self._archiv(), {})

    def test_kein_kontoname_und_keine_mailadresse(self) -> None:
        """Weder Name, Benutzername noch Mailadresse stehen im Archiv."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        abschrift: Abschrift = _abschrift(self.teilnehmerin, self.vignette)
        self._freigeben(abschrift, self.training)

        archiv: dict[str, str] = self._archiv()

        alles: str = "\n".join([*archiv, *archiv.values()])
        for kontodatum in ("grace", "Grace", "Hopper", "example.org"):
            self.assertNotIn(kontodatum, alles)

    def test_keine_denkspur_und_keine_fehlversuche(self) -> None:
        """Denkspur und verworfene Modellantworten bleiben im System."""
        sitzung: Sitzung = _gespielte_sitzung(
            self.training, self.teilnehmerin, self.vignette
        )
        Fehlversuch.objects.create(
            gespraechsschritt=sitzung.gespraechsschritte.get(),
            grund="Ungültiges JSON",
            rohantwort="Verworfene Rohantwort.",
        )

        (text,) = self._archiv().values()

        self.assertNotIn("Geheime Denkspur", text)
        self.assertNotIn("Verworfene Rohantwort.", text)
        self.assertNotIn("Ungültiges JSON", text)

    def test_zwei_exporte_ziehen_verschiedene_kennzeichen(self) -> None:
        """Kennzeichen verfolgen niemanden über die Zeit."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)

        erstes: set[str] = self._ordner(self._archiv())
        zweites: set[str] = self._ordner(self._archiv())

        self.assertNotEqual(erstes, zweites)


class AbschriftTests(TrainingsexportTestCase):
    """Freigegebene Abschriften im Export."""

    def test_freigegebene_abschrift_liegt_als_unterordner_bei_der_person(
        self,
    ) -> None:
        """Sie liegt im Ordner der Person, benannt nach der Erhebung."""
        _gespielte_sitzung(self.training, self.teilnehmerin, self.vignette)
        abschrift: Abschrift = _abschrift(self.teilnehmerin, self.vignette)
        self._freigeben(abschrift, self.training)

        archiv: dict[str, str] = self._archiv()

        (ordner,) = self._ordner(archiv)
        abschriftdateien: list[str] = [name for name in archiv if name.count("/") == 2]
        self.assertEqual(len(archiv), 2)
        self.assertEqual(len(abschriftdateien), 1)
        self.assertTrue(
            abschriftdateien[0].startswith(f"{ordner}/studie-bruchrechnung/")
        )
        self.assertIn("Nur den Zähler gekürzt.", archiv[abschriftdateien[0]])

    def test_abschrift_geht_ohne_denkspur_hinaus(self) -> None:
        """Auch die kopierte Denkspur aus der Erhebung bleibt im System."""
        self._freigeben(_abschrift(self.teilnehmerin, self.vignette), self.training)

        (text,) = self._archiv().values()

        self.assertNotIn("Geheime Denkspur", text)

    def test_erhebungsname_bricht_nicht_aus_dem_ordner_aus(self) -> None:
        """Schrägstriche und Punkte im Namen werden kein Pfad."""
        abschrift: Abschrift = _abschrift(self.teilnehmerin, self.vignette)
        abschrift.erhebungsname = "../../Studie/Bruch"
        abschrift.save(update_fields=["erhebungsname"])
        self._freigeben(abschrift, self.training)

        (name,) = self._archiv()

        self.assertEqual(name.split("/")[1:], ["studiebruch", "01-brüche-addieren.md"])

    def test_private_abschrift_fehlt(self) -> None:
        """Ohne Freigabe geht die Abschrift nicht hinaus."""
        _abschrift(self.teilnehmerin, self.vignette)

        self.assertEqual(self._archiv(), {})

    def test_widerrufene_abschrift_fehlt(self) -> None:
        """Nach dem Widerruf geht die Abschrift nicht mehr hinaus."""
        abschrift: Abschrift = _abschrift(self.teilnehmerin, self.vignette)
        self._freigeben(abschrift, self.training)
        self._freigeben(abschrift)

        self.assertEqual(self._archiv(), {})

    def test_nicht_abgeschlossene_sitzung_der_abschrift_fehlt(self) -> None:
        """Auch in Abschriften gehen nur abgeschlossene Sitzungen hinaus."""
        abschrift: Abschrift = _abschrift(
            self.teilnehmerin, self.vignette, Sitzung.Status.ABGEBROCHEN
        )
        self._freigeben(abschrift, self.training)

        self.assertEqual(self._archiv(), {})

    def test_zwei_abschriften_derselben_erhebung_bleiben_getrennt(self) -> None:
        """Gleiche Erhebungsnamen überschreiben einander nicht."""
        for _ in range(2):
            self._freigeben(_abschrift(self.teilnehmerin, self.vignette), self.training)

        archiv: dict[str, str] = self._archiv()

        self.assertEqual(len(archiv), 2)
        self.assertEqual(len({name.rsplit("/", 1)[0] for name in archiv}), 2)

    def test_abschrift_ohne_einsehbare_sitzung_belegt_keinen_ordnernamen(
        self,
    ) -> None:
        """Eine leer ausgehende Abschrift schiebt die nächste nicht auf „-2“."""
        self._freigeben(
            _abschrift(self.teilnehmerin, self.vignette, Sitzung.Status.ABGEBROCHEN),
            self.training,
        )
        self._freigeben(_abschrift(self.teilnehmerin, self.vignette), self.training)

        (name,) = self._archiv()

        self.assertEqual(name.split("/")[1], "studie-bruchrechnung")

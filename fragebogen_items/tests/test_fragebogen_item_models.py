"""ORM-Tests für Fragebogen-Items und ihre Historien."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from konten.models import Konto
from fragebogen_items.models import (
    LikertSkalenpol,
    FragebogenItem,
    FragebogenItemHistorie,
)


class FragebogenItemAnlegenTests(TestCase):
    """Die Anlege-Naht erzeugt die erste Fassung samt Historie."""

    def test_anlegen_erstellt_entwurf_mit_historie_und_eigentuemerin(self) -> None:
        """Die erste Fassung gehört sofort zur Historie der anlegenden Person."""
        konto = get_user_model().objects.create_user(username="ada")

        item = FragebogenItem.objects.anlegen(konto)

        self.assertEqual(item.zustand, FragebogenItem.Zustand.ENTWURF)
        self.assertIsNotNone(item.historie_id)
        self.assertEqual(list(item.historie.eigentuemerinnen.all()), [konto])

    def test_anlegen_laesst_keine_lebenszykluswerte_zu(self) -> None:
        """Die Anlege-Naht erzeugt stets einen Entwurf, keine finale Fassung."""
        konto = get_user_model().objects.create_user(username="ada")

        with self.assertRaises(TypeError):
            FragebogenItem.objects.anlegen(
                konto,
                zustand=FragebogenItem.Zustand.FINAL,
            )


class FragebogenItemHistorieTests(TestCase):
    """Die Historie ist absichtlich kleiner als eine Vignettenhistorie."""

    def test_historie_kennt_keine_archivierung_als_ganzes(self) -> None:
        """Weder Feld noch Naht bauen die verworfene Bulk-Archivierung nach."""
        feldnamen = {feld.name for feld in FragebogenItemHistorie._meta.fields}

        self.assertNotIn("archiviert", feldnamen)
        self.assertFalse(hasattr(FragebogenItemHistorie, "historie_archivieren"))

    def test_sichtbar_fuer_liefert_nur_den_eigentuemer_kreis(self) -> None:
        """Ko-Eigentümerinnen sehen dieselbe Item-Linie, Fremde nicht."""
        ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        linus: Konto = get_user_model().objects.create_user(username="linus")
        geteilte_historie = FragebogenItemHistorie.objects.create()
        geteilte_historie.eigentuemerinnen.add(ada, grace)
        fremde_historie = FragebogenItemHistorie.objects.create()
        fremde_historie.eigentuemerinnen.add(linus)

        self.assertEqual(
            list(FragebogenItemHistorie.objects.sichtbar_fuer(grace)),
            [geteilte_historie],
        )

    def test_sichtbar_fuer_liefert_alle_historien_fuer_administration(self) -> None:
        """Die Administration sieht auch fremde Item-Historien."""
        administratorin: Konto = get_user_model().objects.create_user(username="admin")
        administratorin.is_superuser = True
        administratorin.save()
        fremde_historie: FragebogenItemHistorie = (
            FragebogenItemHistorie.objects.create()
        )
        fremde_historie.eigentuemerinnen.add(
            get_user_model().objects.create_user(username="linus")
        )

        self.assertEqual(
            list(FragebogenItemHistorie.objects.sichtbar_fuer(administratorin)),
            [fremde_historie],
        )


class FragebogenItemQuerySetTests(TestCase):
    """Die Fassungsabfragen übernehmen die Sichtbarkeit ihrer Historie."""

    def setUp(self) -> None:
        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        self.grace: Konto = get_user_model().objects.create_user(username="grace")
        self.dijkstra: Konto = get_user_model().objects.create_user(username="dijkstra")
        self.administratorin: Konto = get_user_model().objects.create_user(
            username="admin"
        )
        self.administratorin.is_superuser = True
        self.administratorin.save()

        self.eigenes: FragebogenItem = FragebogenItem.objects.anlegen(
            self.ada, wortlaut="Eigenes Item"
        )
        self.geteiltes: FragebogenItem = FragebogenItem.objects.anlegen(
            self.ada, wortlaut="Geteiltes Item"
        )
        self.geteiltes.historie.eigentuemerinnen.add(self.grace)
        self.fremdes: FragebogenItem = FragebogenItem.objects.anlegen(
            get_user_model().objects.create_user(username="linus"),
            wortlaut="Fremdes Item",
        )
        for item in (self.eigenes, self.geteiltes, self.fremdes):
            item.finalisieren()

    def test_sichtbar_fuer_liefert_fassungen_der_eigentuemerin(self) -> None:
        """Die Eigentümerin sieht ihre eigenen und geteilten Fassungen."""
        self.assertEqual(
            list(FragebogenItem.objects.sichtbar_fuer(self.ada)),
            [self.eigenes, self.geteiltes],
        )

    def test_sichtbar_fuer_liefert_fassungen_der_koeigentuemerin(self) -> None:
        """Die Ko-Eigentümerin sieht die geteilte Fassung."""
        self.assertEqual(
            list(FragebogenItem.objects.sichtbar_fuer(self.grace)), [self.geteiltes]
        )

    def test_sichtbar_fuer_liefert_dritten_keine_fassungen(self) -> None:
        """Ein Konto außerhalb aller Eigentümer-Kreise sieht keine Fassung."""
        self.assertEqual(list(FragebogenItem.objects.sichtbar_fuer(self.dijkstra)), [])

    def test_sichtbar_fuer_liefert_der_administration_alle_fassungen(self) -> None:
        """Die Administration sieht auch Fassungen fremder Eigentümer-Kreise."""
        self.assertEqual(
            list(FragebogenItem.objects.sichtbar_fuer(self.administratorin)),
            [self.eigenes, self.geteiltes, self.fremdes],
        )

    def test_sichtbar_fuer_ist_nach_zustandsfilter_verkettbar(self) -> None:
        """Sichtbarkeit lässt sich nach einem Zustandsfilter anwenden."""
        self.assertEqual(
            list(
                FragebogenItem.objects.filter(
                    zustand=FragebogenItem.Zustand.FINAL
                ).sichtbar_fuer(self.ada)
            ),
            [self.eigenes, self.geteiltes],
        )

    def test_sichtbar_fuer_ist_vor_zustandsfilter_verkettbar(self) -> None:
        """Ein Zustandsfilter lässt sich nach der Sichtbarkeit anwenden."""
        self.assertEqual(
            list(
                FragebogenItem.objects.sichtbar_fuer(self.ada).filter(
                    zustand=FragebogenItem.Zustand.FINAL
                )
            ),
            [self.eigenes, self.geteiltes],
        )

    def test_sichtbar_fuer_ist_nach_einbindbar_verkettbar(self) -> None:
        """Sichtbarkeit bleibt nach der Abfrage einbindbarer Fassungen verfügbar."""
        self.assertEqual(
            list(FragebogenItem.objects.einbindbar().sichtbar_fuer(self.ada)),
            [self.eigenes, self.geteiltes],
        )

    def test_sichtbar_fuer_ist_vor_einbindbar_verkettbar(self) -> None:
        """Die Abfrage einbindbarer Fassungen bleibt nach Sichtbarkeit verfügbar."""
        self.assertEqual(
            list(FragebogenItem.objects.sichtbar_fuer(self.ada).einbindbar()),
            [self.eigenes, self.geteiltes],
        )


class FragebogenItemConstraintTests(TestCase):
    """Die Datenbank schützt die gemeinsame Lebenszyklus-Form."""

    def _direkt_speichern(self, **werte: object) -> FragebogenItem:
        """Erzeugt eine Fassung ohne full_clean(), um DB-Constraints zu prüfen."""
        item = FragebogenItem(**werte)
        item._wird_angelegt = True
        item.save()
        return item

    def test_constraints_gelten_bei_direktem_save(self) -> None:
        """Entwürfe und nicht-archivierte Schwestern sind je einmalig."""
        historie = FragebogenItemHistorie.objects.create()
        entwurf = self._direkt_speichern(historie=historie, wortlaut="Wie geht es?")

        with self.assertRaises(IntegrityError), transaction.atomic():
            self._direkt_speichern(historie=historie)

        entwurf.finalisieren()
        self._direkt_speichern(historie=historie, vorgaengerin=entwurf)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._direkt_speichern(
                historie=historie,
                vorgaengerin=entwurf,
                zustand=FragebogenItem.Zustand.FINAL,
                finalisiert_am=entwurf.finalisiert_am,
            )

    def test_check_constraint_gilt_bei_direktem_save(self) -> None:
        """Ein Finalisierungszeitpunkt und der Zustand bleiben DB-konsistent."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._direkt_speichern(
                historie=FragebogenItemHistorie.objects.create(),
                zustand=FragebogenItem.Zustand.FINAL,
            )

    def test_archivierte_schwester_gibt_vorgaengerin_fuer_neue_fassung_frei(
        self,
    ) -> None:
        """Archivierung nimmt eine Fassung aus dem partiellen Schwester-Index."""
        konto = get_user_model().objects.create_user(username="ada")
        vorgaengerin = FragebogenItem.objects.anlegen(konto, wortlaut="Erste Fassung")
        vorgaengerin.finalisieren()
        archivierte_schwester = self._direkt_speichern(
            historie=vorgaengerin.historie,
            vorgaengerin=vorgaengerin,
            zustand=FragebogenItem.Zustand.FINAL,
            finalisiert_am=vorgaengerin.finalisiert_am,
        )

        archivierte_schwester.archivieren()
        neue_schwester = self._direkt_speichern(
            historie=vorgaengerin.historie,
            vorgaengerin=vorgaengerin,
            zustand=FragebogenItem.Zustand.FINAL,
            finalisiert_am=vorgaengerin.finalisiert_am,
        )

        self.assertEqual(neue_schwester.vorgaengerin, vorgaengerin)


class FragebogenItemLebenszyklusTests(TestCase):
    """Die öffentliche Modell-API bewahrt den Lebenszyklus einer Fassung."""

    def test_reversionieren_erhaelt_finale_vorgaengerin_und_erweitert_die_kette(
        self,
    ) -> None:
        """Die neue finale Fassung ergänzt die Historie, statt die alte zu ändern."""
        konto = get_user_model().objects.create_user(username="ada")
        alte_fassung = FragebogenItem.objects.anlegen(
            konto,
            typ=FragebogenItem.Typ.FREITEXT,
            wortlaut="Was fiel Ihnen auf?",
        )
        alte_fassung.finalisieren()
        alter_finalisierungszeitpunkt = alte_fassung.finalisiert_am

        neue_fassung = alte_fassung.bearbeiten()
        neue_fassung.typ = FragebogenItem.Typ.LIKERT
        neue_fassung.wortlaut = "Ich fühlte mich sicher."
        neue_fassung.save()
        neue_fassung.finalisieren()

        alte_fassung.refresh_from_db()
        self.assertEqual(alte_fassung.zustand, FragebogenItem.Zustand.FINAL)
        self.assertEqual(alte_fassung.wortlaut, "Was fiel Ihnen auf?")
        self.assertEqual(alte_fassung.finalisiert_am, alter_finalisierungszeitpunkt)
        self.assertEqual(neue_fassung.vorgaengerin, alte_fassung)
        self.assertEqual(
            FragebogenItem.objects.filter(historie=alte_fassung.historie).count(), 2
        )

    def test_finalisieren_bearbeiten_und_archivieren(self) -> None:
        """Finale Fassungen bleiben unveränderlich und versionieren sich linear."""
        konto = get_user_model().objects.create_user(username="ada")
        item = FragebogenItem.objects.anlegen(
            konto,
            typ=FragebogenItem.Typ.FREITEXT,
            wortlaut="Wie geht es dir?",
        )

        item.finalisieren()
        finalisiert_am = item.finalisiert_am
        item.wortlaut = "Geändert"
        item.typ = FragebogenItem.Typ.LIKERT
        with self.assertRaises(ValidationError):
            item.save()
        item.refresh_from_db()
        self.assertEqual(item.wortlaut, "Wie geht es dir?")
        self.assertEqual(item.typ, FragebogenItem.Typ.FREITEXT)

        entwurf = item.bearbeiten()
        self.assertEqual(entwurf.vorgaengerin, item)
        self.assertEqual(entwurf.zustand, FragebogenItem.Zustand.ENTWURF)

        item.archivieren()
        item.entarchivieren()
        item.refresh_from_db()
        self.assertEqual(item.zustand, FragebogenItem.Zustand.FINAL)
        self.assertEqual(item.finalisiert_am, finalisiert_am)

    def test_nur_entwuerfe_duerfen_physisch_geloescht_werden(self) -> None:
        """Das Löschen ist keine zusätzliche Lifecycle-Kante für Finale."""
        konto = get_user_model().objects.create_user(username="ada")
        entwurf = FragebogenItem.objects.anlegen(konto)
        entwurf.delete()

        finale = FragebogenItem.objects.anlegen(konto, wortlaut="Wie geht es dir?")
        finale.finalisieren()
        with self.assertRaises(ValidationError):
            finale.delete()

    def test_loeschen_der_letzten_fassung_raeumt_die_historie_ab(self) -> None:
        """Eine fassungslose Historie blockiert sonst unsichtbar das Kontolöschen."""
        konto = get_user_model().objects.create_user(username="ada")
        entwurf = FragebogenItem.objects.anlegen(konto)
        historie_pk = entwurf.historie_id

        entwurf.delete()

        self.assertFalse(FragebogenItemHistorie.objects.filter(pk=historie_pk).exists())

    def test_loeschen_einer_fassung_neben_anderen_erhaelt_die_historie(self) -> None:
        """Solange eine Fassung bleibt, trägt die Historie weiter ihren Bestand."""
        konto = get_user_model().objects.create_user(username="ada")
        finale = FragebogenItem.objects.anlegen(konto, wortlaut="Was fiel auf?")
        finale.finalisieren()
        entwurf = finale.bearbeiten()

        entwurf.delete()

        self.assertTrue(
            FragebogenItemHistorie.objects.filter(pk=finale.historie_id).exists()
        )

    def test_massenloeschung_raeumt_leer_gewordene_historien_ab(self) -> None:
        """Auch der QuerySet-Weg hinterlässt keine fassungslose Historie."""
        konto = get_user_model().objects.create_user(username="ada")
        historien = [
            FragebogenItem.objects.anlegen(konto).historie_id for _ in range(2)
        ]

        FragebogenItem.objects.filter(zustand=FragebogenItem.Zustand.ENTWURF).delete()

        self.assertFalse(
            FragebogenItemHistorie.objects.filter(pk__in=historien).exists()
        )


class FragebogenItemSchreibnahtTests(TestCase):
    """Massenschreibwege umgehen die Modell-Naht nicht."""

    def test_create_ist_blockiert(self) -> None:
        """Items entstehen ausschließlich über die Anlege-Naht."""
        historie = FragebogenItemHistorie.objects.create()

        with self.assertRaises(RuntimeError):
            FragebogenItem.objects.create(historie=historie)

    def test_bulk_create_ist_blockiert(self) -> None:
        """Masseneinfügen umgeht die Anlege-Naht nicht."""
        historie = FragebogenItemHistorie.objects.create()

        with self.assertRaises(RuntimeError):
            FragebogenItem.objects.bulk_create([FragebogenItem(historie=historie)])

    def test_bulk_update_ist_blockiert(self) -> None:
        """Massenupdates umgehen die Lebenszyklus-Methoden nicht."""
        with self.assertRaises(RuntimeError):
            FragebogenItem.objects.bulk_update([], ["wortlaut"])


def test_likert_skalenpole_sind_aufsteigend_deklariert() -> None:
    """Die sechs global festgelegten Pole steigen mit der Zustimmung."""
    assert list(LikertSkalenpol.values) == [
        "Stimme gar nicht zu",
        "Stimme nicht zu",
        "Stimme eher nicht zu",
        "Stimme eher zu",
        "Stimme zu",
        "Stimme voll zu",
    ]


def test_likert_skalenpol_wird_aus_seiner_stufe_abgeleitet() -> None:
    """Jede Likert-Stufe verweist auf ihren globalen Skalenpol."""
    for stufe, pol in enumerate(LikertSkalenpol, start=1):
        assert LikertSkalenpol.fuer_stufe(stufe) == pol


def test_likert_stufe_wird_aus_ihrem_skalenpol_abgeleitet() -> None:
    """Jeder globale Likert-Skalenpol verweist auf seine Stufe."""
    for stufe, pol in enumerate(LikertSkalenpol, start=1):
        assert LikertSkalenpol.stufe_fuer(pol) == stufe


def test_likert_skalenpole_sind_nicht_pro_item_konfigurierbar() -> None:
    """Die sechs methodisch festgelegten Pole leben nicht an der Fassung."""
    assert "skalenpole" not in {feld.name for feld in FragebogenItem._meta.fields}

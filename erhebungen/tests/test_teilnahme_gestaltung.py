"""Gestaltungstests der Teilnahmeseiten einer Erhebung.

Geprüft wird ausschließlich die Darstellung: Seitengerüst, Bereichsfarbe und die
Formular- und Knopfklassen des Designsystems (ADR-0023, ADR-0024). Die Seiten
werden dafür ohne Datenbank gerendert — ihre Inhalte und ihr Verhalten prüfen
die HTTP-Tests in `test_teilnahme.py`.
"""

import re
from types import SimpleNamespace
from uuid import uuid4

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

_ERHEBUNG: SimpleNamespace = SimpleNamespace(
    einwilligungstext="Ich willige in die Teilnahme ein.",
    instruktionstext="Fragen Sie gezielt nach dem Rechenweg.",
    abschlusstext="Vielen Dank für Ihre Zeit.",
)
_STICHPROBE: SimpleNamespace = SimpleNamespace(teilnahme_link=uuid4())


class _Feld:
    """Stellvertreter für ein gebundenes Feld des Itemblock-Formulars."""

    label: str = "Wie war die Sitzung?"

    def __str__(self) -> str:
        """Gibt das Steuerelement so zurück, wie Django es ausliefert."""

        return mark_safe('<textarea name="item_1"></textarea>')


_FORMULAR: tuple[_Feld, ...] = (_Feld(),)
# Das Token steht in der URL der Folgeseite ("token") und im Kontextprozessor
# der Seitenleiste ("teilnahme_token"); beide Wege zeigen auf dieselbe Teilnahme.
_TOKEN: str = "ABCD-1234"
_KONTEXT: dict[str, object] = {
    "erhebung": _ERHEBUNG,
    "stichprobe": _STICHPROBE,
    "formular": _FORMULAR,
    "token": _TOKEN,
    "teilnahme_token": _TOKEN,
}
_SEITEN: tuple[str, ...] = (
    "erhebungen/einwilligung.html",
    "erhebungen/instruktion.html",
    "erhebungen/itemblock.html",
    "erhebungen/abschluss.html",
    "erhebungen/abbruchseite.html",
)
_FORMULARSEITEN: tuple[str, ...] = (
    "erhebungen/einwilligung.html",
    "erhebungen/instruktion.html",
    "erhebungen/itemblock.html",
)
_TEILVORLAGE: str = "erhebungen/includes/itemblock_form.html"
_BESCHRIFTUNGSVERWEIS: re.Pattern[str] = re.compile(r'aria-labelledby="([^"]+)"')
_KNOPF: re.Pattern[str] = re.compile(r"<button[^>]*>")


def _gerendert(vorlage: str) -> str:
    # Rendert eine Teilnahmeseite mit stellvertretenden Anzeigedaten.

    return render_to_string(vorlage, _KONTEXT)


class TeilnahmeseitenGestaltungTests(SimpleTestCase):
    """Die Teilnahmeseiten tragen das Gerüst und die Farbe der Teilnehmer:in."""

    def test_jede_teilnahmeseite_nutzt_seitengeruest_und_seitenkopf(self) -> None:
        """Rahmen, Kopf und Abschnittsstruktur stammen aus dem Seiten-Gerüst."""

        for vorlage in _SEITEN:
            with self.subTest(vorlage=vorlage):
                seite: str = _gerendert(vorlage)

                self.assertIn('class="page area--participant"', seite)
                self.assertIn('class="page-head"', seite)
                self.assertIn('class="page-section"', seite)
                self.assertIn('class="page-section__head"', seite)

    def test_jede_teilnahmeseite_traegt_die_gruene_bereichsfarbe(self) -> None:
        """Die Teilnehmer:in-Sicht bleibt grün, auch in der Erhebungs-App."""

        for vorlage in _SEITEN:
            with self.subTest(vorlage=vorlage):
                seite: str = _gerendert(vorlage)

                self.assertIn("area--participant", seite)
                self.assertNotIn("area--research", seite)
                self.assertNotIn("card--research", seite)

    def test_jede_teilnahmeseite_verknuepft_abschnitt_und_ueberschrift(self) -> None:
        """Jeder Abschnitt zeigt über `aria-labelledby` auf seine Überschrift."""

        for vorlage in _SEITEN:
            with self.subTest(vorlage=vorlage):
                seite: str = _gerendert(vorlage)
                verweise: list[str] = _BESCHRIFTUNGSVERWEIS.findall(seite)

                self.assertTrue(verweise, "Die Seite beschriftet keinen Abschnitt.")
                for verweis in verweise:
                    self.assertIn(f'id="{verweis}"', seite)

    def test_formularseiten_verwenden_die_vorhandenen_knopfklassen(self) -> None:
        """Knöpfe tragen die gemeinsame Knopfklasse statt nackter Vorgaben."""

        for vorlage in _FORMULARSEITEN:
            with self.subTest(vorlage=vorlage):
                knoepfe: list[str] = _KNOPF.findall(_gerendert(vorlage))

                self.assertTrue(knoepfe, "Die Seite zeigt keinen Knopf.")
                for knopf in knoepfe:
                    self.assertIn('class="button"', knopf)

    def test_keine_teilnahmeseite_fuehrt_eigene_farbwerte_ein(self) -> None:
        """Farben kommen aus den semantischen Tokens, nicht aus der Vorlage."""

        for vorlage in (*_SEITEN, _TEILVORLAGE):
            with self.subTest(vorlage=vorlage):
                seite: str = _gerendert(vorlage)

                self.assertNotIn("--phsg-", seite)
                self.assertNotIn("color:", seite)
                self.assertNotIn("background:", seite)

    def test_itemblock_teilvorlage_traegt_ihre_klassen_selbst(self) -> None:
        """Der htmx-Tausch mit `outerHTML` darf keine Gestaltung verlieren."""

        teilvorlage: str = _gerendert(_TEILVORLAGE)

        self.assertIn('class="form"', teilvorlage)
        self.assertIn("page-fieldset", teilvorlage)
        self.assertIn('class="button"', teilvorlage)

    def test_itemblock_behaelt_beschriftete_feldgruppen(self) -> None:
        """Jedes Item bleibt eine Feldgruppe mit eigener Beschriftung."""

        teilvorlage: str = _gerendert(_TEILVORLAGE)

        self.assertIn("<fieldset", teilvorlage)
        self.assertIn("<legend", teilvorlage)
        self.assertIn(_Feld.label, teilvorlage)

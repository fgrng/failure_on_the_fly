"""Tests für die geteilte Lese-Hülle um das Markdown-Feld."""

from django.template.loader import render_to_string
from django.test import SimpleTestCase


def _lesefeld(wert: str, profil: str = "szenentext") -> str:
    return render_to_string(
        "texte/includes/markdown_lesefeld.html",
        {
            "feld_id": "id_text",
            "feld_name": "text",
            "label": "Lernauftrag",
            "wert": wert,
            "profil": profil,
        },
    )


class MarkdownLesefeldTests(SimpleTestCase):
    """Die Hülle lässt sich mit jedem Profil ohne Kopie einbinden."""

    def test_rendert_den_text_im_uebergebenen_profil(self) -> None:
        """Ein Szenentext bleibt ohne Link, das Feld behält die Quelle."""

        html: str = _lesefeld("**fett** [Info](https://example.org)")

        self.assertIn("<strong>fett</strong> [Info](https://example.org)", html)
        self.assertIn('<textarea id="id_text" name="text"', html)
        self.assertIn('"profil": "szenentext"', html)
        self.assertIn(">Bearbeiten</button>", html)
        self.assertNotIn("Noch kein Text", html)

    def test_leerer_text_laedt_zum_schreiben_ein(self) -> None:
        """Ohne Quelle gibt es nichts zu lesen, nur »Text schreiben«."""

        html: str = _lesefeld("")

        self.assertIn("Noch kein Text", html)
        self.assertIn(">Text schreiben</button>", html)
        self.assertNotIn("Ganz anzeigen", html)

    def test_traegt_das_label_nur_einmal(self) -> None:
        """Das Markdown-Feld in der Hülle verzichtet auf ein eigenes Label."""

        self.assertEqual(_lesefeld("x").count('<label for="id_text">'), 1)

    def test_speichern_sendet_das_umgebende_formular(self) -> None:
        """Speichern ist ein Submit-Knopf, Abbrechen nicht."""

        html: str = _lesefeld("x")

        self.assertIn('<button type="submit" class="button">Speichern</button>', html)
        self.assertIn("feld.value = feld.defaultValue", html)

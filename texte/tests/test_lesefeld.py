"""Tests für die geteilte Lese-Hülle um das Markdown-Feld."""

from django import forms
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


class _Formular(forms.Form):
    """Ein Markdown-Text und ein Klartext, beide optional."""

    lernauftrag = forms.CharField(
        label="Lernauftrag", required=False, widget=forms.Textarea
    )
    hinweise = forms.CharField(
        label="Hinweise",
        required=False,
        widget=forms.Textarea,
        help_text="Nur für die Simulation.",
    )


def _formularfeld(feld: forms.BoundField, profil: str = "") -> str:
    return render_to_string(
        "texte/includes/lesefeld_formularfeld.html",
        {"field": feld, "profil": profil},
    )


class LesefeldFormularfeldTests(SimpleTestCase):
    """Die Hülle nimmt auch Django-Formularfelder, mit oder ohne Markdown."""

    def test_markdown_feld_liest_wert_und_label_aus_dem_formularfeld(self) -> None:
        """Label, ID und Wert kommen aus dem Feld, die Vorschau aus dem Profil."""

        feld: forms.BoundField = _Formular(initial={"lernauftrag": "**27**"})[
            "lernauftrag"
        ]

        html: str = _formularfeld(feld, "szenentext")

        self.assertIn('<label for="id_lernauftrag">Lernauftrag</label>', html)
        self.assertIn("<strong>27</strong>", html)
        self.assertIn('name="lernauftrag"', html)
        self.assertIn(">Vorschau</button>", html)
        self.assertIn(">Bearbeiten</button>", html)

    def test_klartext_steht_ohne_markdown_und_ohne_vorschau(self) -> None:
        """Ohne Profil bleibt der Text wörtlich, Absätze bleiben erhalten."""

        feld: forms.BoundField = _Formular(
            initial={"hinweise": "Zählt **einzeln**\nund laut"}
        )["hinweise"]

        html: str = _formularfeld(feld)

        self.assertIn("<p>Zählt **einzeln**<br>und laut</p>", html)
        self.assertNotIn(">Vorschau</button>", html)
        self.assertIn('<textarea name="hinweise"', html)
        self.assertIn("Nur für die Simulation.", html)
        self.assertIn('<button type="submit" class="button">Speichern</button>', html)

    def test_leerer_klartext_laedt_zum_schreiben_ein(self) -> None:
        """Auch ohne Markdown zeigt ein leerer Text »Text schreiben«."""

        html: str = _formularfeld(_Formular()["hinweise"])

        self.assertIn("Noch kein Text", html)
        self.assertIn(">Text schreiben</button>", html)

    def test_feld_mit_fehler_startet_offen(self) -> None:
        """Ein Fehler steht sichtbar am geöffneten Feld."""

        formular: _Formular = _Formular(data={"hinweise": "x"})
        formular.is_valid()
        formular.add_error("hinweise", "Enthält ungültige Platzhalter.")

        offen: str = _formularfeld(formular["hinweise"])
        zu: str = _formularfeld(formular["lernauftrag"])

        self.assertIn("bearbeiten: true", offen)
        self.assertIn("Enthält ungültige Platzhalter.", offen)
        self.assertIn("bearbeiten: false", zu)

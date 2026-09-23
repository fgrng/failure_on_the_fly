"""Tests der beiden Markdown-Profile über ihre HTML-Ausgabe."""

from django.test import SimpleTestCase

from texte.markdown import informationstext, szenentext

_PROFILE = (informationstext, szenentext)


class GemeinsamerUmfangTests(SimpleTestCase):
    """Beide Profile teilen Absätze, Hervorhebung, Überschriften und Listen."""

    def test_fett_und_kursiv(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("**fett** und *kursiv*")

                self.assertIn("<strong>fett</strong>", html)
                self.assertIn("<em>kursiv</em>", html)

    def test_einfacher_zeilenumbruch_wird_br_und_leerzeile_trennt_absaetze(
        self,
    ) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("eins\nzwei\n\ndrei")

                self.assertIn("<p>eins<br>\nzwei</p>", html)
                self.assertIn("<p>drei</p>", html)

    def test_ueberschriften_werden_um_zwei_ebenen_verschoben(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("# Eins\n\n## Zwei\n\n### Drei")

                self.assertIn("<h3>Eins</h3>", html)
                self.assertIn("<h4>Zwei</h4>", html)
                self.assertIn("<h5>Drei</h5>", html)
                self.assertNotIn("<h1", html)
                self.assertNotIn("<h2", html)

    def test_tiefere_ueberschriften_bleiben_woertlich(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("#### Vier")

                self.assertIn("<p>#### Vier</p>", html)
                self.assertNotIn("<h6", html)

    def test_listen_und_zitatblock(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("- a\n- b\n\n1. c\n2. d\n\n> Zitat")

                self.assertIn("<ul>\n<li>a</li>\n<li>b</li>\n</ul>", html)
                self.assertIn("<ol>\n<li>c</li>\n<li>d</li>\n</ol>", html)
                self.assertIn("<blockquote>\n<p>Zitat</p>\n</blockquote>", html)

    def test_rohes_html_erscheint_woertlich(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil('<script>alert(1)</script>\n\nText <b onclick="x">')

                self.assertNotIn("<script", html)
                self.assertNotIn("<b ", html)
                self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
                self.assertIn("&lt;b onclick=&quot;x&quot;&gt;", html)

    def test_bilder_erscheinen_woertlich(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("![Tafel](https://example.org/bild.png)")

                self.assertNotIn("<img", html)
                self.assertNotIn("<a ", html)
                self.assertIn("![Tafel](https://example.org/bild.png)", html)

    def test_tabellen_erscheinen_woertlich(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("| a | b |\n|---|---|\n| 1 | 2 |")

                self.assertNotIn("<table", html)
                self.assertIn("| a | b |", html)

    def test_codebloecke_erscheinen_woertlich(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("```\n3 + 4\n```\n\n    eingerückt\n\n`inline`")

                self.assertNotIn("<pre", html)
                self.assertNotIn("<code", html)
                self.assertIn("```", html)
                self.assertIn("eingerückt", html)
                self.assertIn("`inline`", html)

    def test_nackte_urls_werden_nicht_verlinkt(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("Siehe https://example.org und www.example.org")

                self.assertNotIn("<a", html)
                self.assertIn("https://example.org", html)

    def test_backslash_escapes_bleiben_woertlich(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("3 \\* 4 = 12\n\\- 5\n\\# keine Überschrift")

                self.assertIn("3 * 4 = 12", html)
                self.assertIn("- 5", html)
                self.assertIn("# keine Überschrift", html)
                self.assertNotIn("<em>", html)
                self.assertNotIn("<ul>", html)
                self.assertNotIn("<h3>", html)

    def test_leere_quelle_ergibt_leeres_html(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                self.assertEqual(profil(""), "")


class InformationstextLinkTests(SimpleTestCase):
    """Der Informationstext verlinkt nur nach außen und sagt das auch."""

    def test_erlaubte_schemata_werden_zu_externen_links(self) -> None:
        for ziel in (
            "https://example.org/datenschutz",
            "http://example.org",
            "mailto:forschung@example.org",
        ):
            with self.subTest(ziel=ziel):
                html: str = informationstext(f"[Hinweis]({ziel})")

                self.assertIn(f'href="{ziel}"', html)
                self.assertIn('target="_blank"', html)
                self.assertIn('rel="noopener noreferrer"', html)
                self.assertIn('class="markdown-text__extern"', html)
                self.assertIn("öffnet in neuem Tab", html)

    def test_andere_ziele_erscheinen_woertlich(self) -> None:
        for ziel in (
            "javascript:alert(1)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "/konten/anmelden/",
            "ftp://example.org",
        ):
            with self.subTest(ziel=ziel):
                html: str = informationstext(f"[Hinweis]({ziel})")

                self.assertNotIn("<a", html)
                self.assertIn(f"[Hinweis]({ziel})", html)


class SzenentextLinkTests(SimpleTestCase):
    """Im Szenentext bleibt Link-Syntax stehen, wie sie geschrieben wurde."""

    def test_link_syntax_bleibt_woertlich(self) -> None:
        html: str = szenentext("[Hinweis](https://example.org)")

        self.assertNotIn("<a", html)
        self.assertIn("[Hinweis](https://example.org)", html)

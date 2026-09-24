"""Tests der beiden Markdown-Profile über ihre HTML-Ausgabe."""

from collections.abc import Callable

from django.test import SimpleTestCase
from django.utils.html import escape
from django.utils.safestring import SafeString

from texte.markdown import PROFILE, informationstext, szenentext, woertlich

_PROFILE: tuple[Callable[[str], SafeString], ...] = (informationstext, szenentext)


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

    def test_umzaeunte_codebloecke_und_backticks_erscheinen_woertlich(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("```\n3 + 4\n```\n\n`inline`")

                self.assertNotIn("<pre", html)
                self.assertNotIn("<code", html)
                self.assertIn("```", html)
                self.assertIn("`inline`", html)

    def test_eingerueckter_codeblock_behaelt_seine_einrueckung(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("Rechnung:\n\n    3x + 4 = 10\n      3x = 6\n\nfertig")

                self.assertIn("<pre><code>3x + 4 = 10\n  3x = 6\n</code></pre>", html)
                self.assertIn("<p>fertig</p>", html)

    def test_eingerueckte_zeile_ohne_leerzeile_bleibt_im_absatz(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                html: str = profil("Rechnung:\n    3x = 6")

                self.assertNotIn("<pre", html)
                self.assertIn("3x = 6", html)

    def test_leere_quelle_ergibt_leeres_html(self) -> None:
        for profil in _PROFILE:
            with self.subTest(profil=profil.__name__):
                self.assertEqual(profil(""), "")


class InformationstextLinkTests(SimpleTestCase):
    """Der Informationstext verlinkt nur nach außen und sagt das auch."""

    def test_web_links_oeffnen_in_neuem_tab(self) -> None:
        for ziel in ("https://example.org/datenschutz", "http://example.org"):
            with self.subTest(ziel=ziel):
                html: str = informationstext(f"[Hinweis]({ziel})")

                self.assertIn(f'href="{ziel}"', html)
                self.assertIn('target="_blank"', html)
                self.assertIn('rel="noopener noreferrer"', html)
                self.assertIn('class="markdown-text__extern"', html)
                self.assertIn("öffnet in neuem Tab", html)

    def test_email_links_oeffnen_ohne_neuen_tab(self) -> None:
        html: str = informationstext("[Schreiben Sie uns](mailto:forschung@example.org)")

        self.assertIn('href="mailto:forschung@example.org"', html)
        self.assertNotIn("target=", html)
        self.assertIn('class="markdown-text__extern"> (E-Mail)', html)
        self.assertNotIn("öffnet in neuem Tab", html)

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


class WoertlichTests(SimpleTestCase):
    """Ein escapter Wert erscheint im gerenderten Text unverändert."""

    def test_markdown_zeichen_eines_werts_wirken_nicht(self) -> None:
        for wert in ("# 1. *a* _b_ [c](https://d.org) <i>", "- x", "1. y", "> z"):
            with self.subTest(wert=wert):
                html: str = szenentext(woertlich(wert))

                self.assertEqual(html, f"<p>{escape(wert)}</p>\n")


class ProfilRegisterTests(SimpleTestCase):
    """Das Register liefert je Profil Rendering und passenden Editorhinweis."""

    def test_register_rendert_wie_die_einstiegspunkte(self) -> None:
        self.assertEqual(
            PROFILE["informationstext"].rendern("[a](https://b.org)"),
            informationstext("[a](https://b.org)"),
        )
        self.assertEqual(PROFILE["szenentext"].rendern("**a**"), szenentext("**a**"))

    def test_nur_der_informationstext_nennt_link_syntax(self) -> None:
        self.assertIn("[Linktext](https://…)", PROFILE["informationstext"].hinweis)
        self.assertNotIn("[Linktext]", PROFILE["szenentext"].hinweis)
        self.assertIn("Schülernotation", PROFILE["szenentext"].hinweis)

"""Gemeinsame Zugriffe der View-Tests auf die Formulare einer Seite."""

from html.parser import HTMLParser

from django.http import HttpResponse


class _Knopfsammler(HTMLParser):
    """Sammelt Submit-Knöpfe mit Beschriftung und zugehörigem Formular."""

    def __init__(self) -> None:
        super().__init__()
        self.knoepfe: list[tuple[str, str | None]] = []
        self._formulare: list[str | None] = []
        self._knopf: tuple[str | None, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        werte: dict[str, str | None] = dict(attrs)
        if tag == "form":
            self._formulare.append(werte.get("id"))
        elif tag == "button" and werte.get("type", "submit") == "submit":
            formular: str | None = werte.get("form") or (
                self._formulare[-1] if self._formulare else None
            )
            self._knopf = (formular, [])

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._formulare:
            self._formulare.pop()
        elif tag == "button" and self._knopf is not None:
            formular, text = self._knopf
            self.knoepfe.append(("".join(text).strip(), formular))
            self._knopf = None

    def handle_data(self, data: str) -> None:
        if self._knopf is not None:
            self._knopf[1].append(data)


def submit_knoepfe(antwort: HttpResponse) -> list[tuple[str, str | None]]:
    """Liefert Beschriftung und Formular-ID aller Submit-Knöpfe einer Seite."""

    sammler: _Knopfsammler = _Knopfsammler()
    sammler.feed(antwort.content.decode())
    return sammler.knoepfe

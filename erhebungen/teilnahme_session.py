"""Die an den Browser gebundenen Tokens laufender Erhebungsteilnahmen.

Sie stehen in einem eigenen signierten Cookie, nie in der Konto-Session: Auf
dem Server liegen Konto und Token so nie im selben Datensatz (ADR-0006,
ADR-0058). Das Cookie gilt nur unter dem Teilnahmepfad und lebt gleitend
einen Tag ab dem letzten Zugriff.
"""

from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponse

_COOKIE: str = "erhebung_teilnahme_tokens"
_PFAD: str = "/erhebungen/teilnahme/"
_FRIST: timedelta = timedelta(days=1)
_SALZ: str = "erhebungen.teilnahme_tokens"
# Die Tokens dieses Requests, einmal aus dem Cookie gelesen.
_ATTRIBUT: str = "_teilnahme_tokens"


def token_aus_session(request: HttpRequest, teilnahme_link: UUID | str) -> str | None:
    """Liefert das Token, das dieser Browser für den Teilnahme-Link hält."""

    return _tokens(request).get(str(teilnahme_link))


def token_in_session_speichern(
    request: HttpRequest, teilnahme_link: UUID | str, token: str
) -> None:
    """Bindet einen tokenbasierten Wiedereinstieg an den aktuellen Browser."""

    _tokens(request)[str(teilnahme_link)] = token


def tokens_im_browser(request: HttpRequest) -> list[str]:
    """Liefert alle Tokens, die dieser Browser bisher gebunden hat."""

    return list(_tokens(request).values())


def _tokens(request: HttpRequest) -> dict[str, str]:
    # Liest die Zuordnung Teilnahme-Link -> Token einmal je Request aus dem
    # Cookie; ein Browser kann an mehreren Erhebungen teilnehmen. Ein
    # verfälschtes oder abgelaufenes Cookie zählt als leer.

    if not hasattr(request, _ATTRIBUT):
        tokens: dict[str, str] = {}
        wert: str | None = request.COOKIES.get(_COOKIE)
        if wert is not None:
            try:
                tokens = signing.loads(wert, salt=_SALZ, max_age=_FRIST)
            except signing.BadSignature:
                pass
        setattr(request, _ATTRIBUT, tokens)
    return getattr(request, _ATTRIBUT)


def teilnahme_tokens_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """Schreibt die Tokens nach jedem Zugriff auf die Teilnahme neu ins Cookie.

    Das frische Signieren verschiebt die Frist; ohne Zugriff verfällt die
    Zuordnung nach einem Tag, das Token selbst führt per Eingabe weiter.
    """

    def middleware(request: HttpRequest) -> HttpResponse:
        response: HttpResponse = get_response(request)
        if not request.path.startswith(_PFAD):
            return response
        tokens: dict[str, str] = _tokens(request)
        if tokens:
            response.set_cookie(
                _COOKIE,
                signing.dumps(tokens, salt=_SALZ),
                max_age=_FRIST,
                path=_PFAD,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=settings.SESSION_COOKIE_HTTPONLY,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
        elif _COOKIE in request.COOKIES:
            response.delete_cookie(_COOKIE, path=_PFAD)
        return response

    return middleware

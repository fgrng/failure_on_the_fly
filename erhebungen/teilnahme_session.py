"""Die an den Browser gebundenen Tokens laufender Erhebungsteilnahmen."""

from uuid import UUID

from django.http import HttpRequest

TEILNAHME_TOKENS_SESSION_KEY: str = "erhebung_teilnahme_tokens"


def token_aus_session(request: HttpRequest, teilnahme_link: UUID | str) -> str | None:
    """Liefert das Token, das dieser Browser für den Teilnahme-Link hält."""

    return _tokens(request).get(str(teilnahme_link))


def token_in_session_speichern(
    request: HttpRequest, teilnahme_link: UUID | str, token: str
) -> None:
    """Bindet einen tokenbasierten Wiedereinstieg an den aktuellen Browser."""

    tokens: dict[str, str] = _tokens(request)
    if tokens.get(str(teilnahme_link)) == token:
        return
    tokens[str(teilnahme_link)] = token
    request.session[TEILNAHME_TOKENS_SESSION_KEY] = tokens


def tokens_im_browser(request: HttpRequest) -> list[str]:
    """Liefert alle Tokens, die dieser Browser bisher gebunden hat."""

    return list(_tokens(request).values())


def _tokens(request: HttpRequest) -> dict[str, str]:
    # Ein Browser kann an mehreren Erhebungen teilnehmen: Teilnahme-Link -> Token.

    return request.session.get(TEILNAHME_TOKENS_SESSION_KEY, {})

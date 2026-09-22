"""Das Teilnahme-Token der laufenden Teilnahme für die Seitenleiste."""

from django.http import HttpRequest
from django.urls import ResolverMatch

from .teilnahme_session import token_aus_session

# Positivliste statt Ausschluss der Forschenden-Views: Eine künftig ergänzte
# Forschenden-View soll von sich aus kein Token ausspielen.
_VIEWS_MIT_TOKEN_IN_DER_URL: frozenset[str] = frozenset(
    {"gespraech", "gespraech_beenden", "debrief", "abbrechen", "itemblock"}
)
_VIEWS_MIT_TEILNAHME_LINK: frozenset[str] = frozenset(
    {"einwilligung", "instruktion", "abschluss"}
)


def teilnahme_token(request: HttpRequest) -> dict[str, str]:
    """Löst das Token der laufenden Teilnahme ohne Datenbankzugriff auf.

    Es steht in beiden Fällen schon vor der Tür: entweder in der URL selbst
    oder in dem Session-Eintrag, den die Teilnahme ohnehin führt, um einen
    tokenbasierten Wiedereinstieg an den Browser zu binden.
    """

    treffer: ResolverMatch | None = request.resolver_match
    if treffer is None or treffer.namespace != "erhebungen":
        return {}
    if treffer.url_name in _VIEWS_MIT_TOKEN_IN_DER_URL:
        return {"teilnahme_token": treffer.kwargs["token"]}
    if treffer.url_name not in _VIEWS_MIT_TEILNAHME_LINK:
        return {}
    token: str | None = token_aus_session(request, treffer.kwargs["teilnahme_link"])
    if token is None:
        return {}
    return {"teilnahme_token": token}

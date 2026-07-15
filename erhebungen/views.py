"""Öffentlicher Einstieg in pseudonyme Erhebungen."""

from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from .models import Erhebungsbindung, Stichprobe

_TEILNAHME_TOKENS_SESSION_KEY = "erhebung_teilnahme_tokens"


def teilnehmen(request: HttpRequest, teilnahme_link: UUID) -> HttpResponse:
    """Legt beim ersten Link-Aufruf eine pseudonyme Teilnahme an oder setzt sie fort."""
    stichprobe: Stichprobe = get_object_or_404(
        Stichprobe,
        teilnahme_link=teilnahme_link,
    )
    tokens: dict[str, str] = request.session.get(_TEILNAHME_TOKENS_SESSION_KEY, {})
    token: str | None = tokens.get(str(teilnahme_link))
    bindung: Erhebungsbindung | None = None
    if token is not None:
        bindung = Erhebungsbindung.objects.filter(
            stichprobe=stichprobe,
            token=token,
        ).first()
    if bindung is None:
        bindung = Erhebungsbindung.objects.anlegen(stichprobe)
        tokens[str(teilnahme_link)] = bindung.token
        request.session[_TEILNAHME_TOKENS_SESSION_KEY] = tokens
    return HttpResponse(status=204)

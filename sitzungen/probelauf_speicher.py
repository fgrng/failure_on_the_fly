"""Der laufende Probelauf eines Browsers, im kurzlebigen Speicher.

Ein eigenes signiertes Cookie unter dem Probelaufpfad trägt eine zufällige
Kennung des Browsers; der Eintrag liegt unter ihr und dem Konto. So hat jeder
Browser seinen eigenen Probelauf, und ein anderes Konto im selben Browser
findet keinen. Wie der Eintrag lebt das Cookie gleitend einen Tag ab dem
letzten Zugriff. Das Abmelden löscht die Probeläufe des Kontos.
"""

import secrets
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core import signing
from django.http import HttpRequest, HttpResponse

from sitzungen import kurzlebiger_speicher

_COOKIE: str = "probelauf"
_PFAD: str = "/sitzungen/probelauf/"
_FRIST: timedelta = timedelta(days=1)
_SALZ: str = "sitzungen.probelauf"
# Kennung und Zustand dieses Requests, einmal geladen.
_ATTRIBUT: str = "_probelauf"


def probelauf_zustand(request: HttpRequest) -> dict[str, Any]:
    """Liefert den veränderbaren Zustand des Probelaufs dieses Browsers und Kontos.

    Ohne laufenden Probelauf ist er leer. Die Middleware hält ihn nach der
    Antwort fest.
    """

    return _laden(request)[1]


def probelauf_beim_abmelden_loeschen(
    sender: object, request: HttpRequest, user: AbstractBaseUser | None, **_: object
) -> None:
    """Löscht beim Abmelden die Probeläufe des Kontos.

    Das Cookie erreicht die Abmeldung nicht, sein Pfad liegt woanders; deshalb
    gehen die Probeläufe des Kontos in allen Browsern.
    """

    if user is not None:
        kurzlebiger_speicher.alle_loeschen(_praefix(user))


def probelauf_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """Hält den Probelauf nach jedem Zugriff unter dem Probelaufpfad fest.

    Das Schreiben verschiebt die Frist von Eintrag und Cookie; ein leerer
    Zustand löscht beide.
    """

    def middleware(request: HttpRequest) -> HttpResponse:
        response: HttpResponse = get_response(request)
        if not request.path.startswith(_PFAD) or not request.user.is_authenticated:
            return response
        kennung, zustand = _laden(request)
        if zustand:
            kennung = kennung or secrets.token_hex(16)
            kurzlebiger_speicher.schreiben(_schluessel(request.user, kennung), zustand)
            response.set_cookie(
                _COOKIE,
                signing.dumps(kennung, salt=_SALZ),
                max_age=_FRIST,
                path=_PFAD,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=settings.SESSION_COOKIE_HTTPONLY,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
        elif kennung is not None:
            kurzlebiger_speicher.loeschen(_schluessel(request.user, kennung))
            response.delete_cookie(_COOKIE, path=_PFAD)
        return response

    return middleware


def _laden(request: HttpRequest) -> tuple[str | None, dict[str, Any]]:
    # Liest Kennung und Zustand einmal je Request. Ein verfälschtes oder
    # abgelaufenes Cookie zählt als keines, ein fehlender oder abgelaufener
    # Eintrag als leerer Zustand.

    if not hasattr(request, _ATTRIBUT):
        kennung: str | None = None
        zustand: dict[str, Any] = {}
        wert: str | None = request.COOKIES.get(_COOKIE)
        if wert is not None:
            try:
                kennung = signing.loads(wert, salt=_SALZ, max_age=_FRIST)
            except signing.BadSignature:
                pass
        if kennung is not None and request.user.is_authenticated:
            zustand = (
                kurzlebiger_speicher.lesen(_schluessel(request.user, kennung)) or {}
            )
        setattr(request, _ATTRIBUT, (kennung, zustand))
    return getattr(request, _ATTRIBUT)


def _praefix(konto: AbstractBaseUser | AnonymousUser) -> str:
    # Alle Probeläufe eines Kontos teilen diesen Anfang ihres Schlüssels.

    return f"probelauf-{konto.pk}-"


def _schluessel(konto: AbstractBaseUser | AnonymousUser, kennung: str) -> str:
    # Der Eintrag eines Browsers für ein Konto.

    return f"{_praefix(konto)}{kennung}"

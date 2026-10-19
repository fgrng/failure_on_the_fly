"""Ein signiertes Cookie unter einem Pfad, das gleitend eine Frist lebt.

Teilnahme-Tokens und Probelauf liegen so jeweils in einem eigenen Cookie
neben der Session; Secure, HttpOnly und SameSite folgen deren Einstellungen.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponse


@dataclass(frozen=True)
class PfadCookie:
    """Name, Pfad, Salz und Frist eines signierten Cookies."""

    name: str
    pfad: str
    salz: str
    frist: timedelta = timedelta(days=1)

    def lesen(self, request: HttpRequest) -> Any | None:
        """Liefert den Wert; ein verfälschtes oder abgelaufenes Cookie zählt als keines."""

        wert: str | None = request.COOKIES.get(self.name)
        if wert is None:
            return None
        try:
            return signing.loads(wert, salt=self.salz, max_age=self.frist)
        except signing.BadSignature:
            return None

    def setzen(self, response: HttpResponse, wert: Any) -> None:
        """Signiert den Wert frisch und verschiebt so die Frist."""

        response.set_cookie(
            self.name,
            signing.dumps(wert, salt=self.salz),
            max_age=self.frist,
            path=self.pfad,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )

    def loeschen(self, response: HttpResponse) -> None:
        """Löscht das Cookie unter seinem Pfad."""

        response.delete_cookie(self.name, path=self.pfad)

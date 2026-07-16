"""Rollen und Sichtbarkeit der globalen Navigation."""

from functools import wraps
from typing import TYPE_CHECKING, Callable, Concatenate, ParamSpec

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from .models import Konto


AUTORIN_GRUPPE: str = "Autor:in"
AUSBILDERIN_GRUPPE: str = "Ausbilder:in"
FORSCHENDE_GRUPPE: str = "Forschende:r"
ADMINISTRATORIN_GRUPPE: str = "Administrator:in"
KONTOROLLEN: tuple[str, ...] = (
    AUTORIN_GRUPPE,
    AUSBILDERIN_GRUPPE,
    FORSCHENDE_GRUPPE,
    ADMINISTRATORIN_GRUPPE,
)
P: ParamSpec = ParamSpec("P")


def _rollen(konto: "Konto") -> set[str]:
    """Liefert die für die Anwendung relevanten Gruppen eines Kontos."""
    return set(konto.groups.filter(name__in=KONTOROLLEN).values_list("name", flat=True))


def ist_autorin(konto: "Konto") -> bool:
    """Prüft die Entwicklungsrolle einschließlich Administrations-Override."""
    return bool(_rollen(konto) & {AUTORIN_GRUPPE, ADMINISTRATORIN_GRUPPE})


def autorin_erforderlich(
    view: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """Schützt Entwicklungs-Views mit der Autorenrolle."""

    @wraps(view)
    def geschuetzte_view(
        request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
    ) -> HttpResponse:
        if not ist_autorin(request.user):
            return HttpResponse(status=403)
        return view(request, *args, **kwargs)

    return geschuetzte_view


def navigation(request: HttpRequest) -> dict[str, bool]:
    """Stellt der Sidebar die ausschließlich rollenbasierten Sichtbarkeiten bereit."""
    if not request.user.is_authenticated:
        return {
            "zeige_entwicklung": False,
            "zeige_ausbildung_kuratieren": False,
            "zeige_teilnahme": False,
            "zeige_forschung": False,
            "zeige_system": False,
            "simulationskern_verwalten": False,
        }

    rollen: set[str] = _rollen(request.user)
    ist_administratorin: bool = ADMINISTRATORIN_GRUPPE in rollen
    return {
        "zeige_entwicklung": ist_administratorin or AUTORIN_GRUPPE in rollen,
        "zeige_ausbildung_kuratieren": ist_administratorin
        or AUSBILDERIN_GRUPPE in rollen,
        "zeige_teilnahme": ist_administratorin or not rollen,
        "zeige_forschung": ist_administratorin or FORSCHENDE_GRUPPE in rollen,
        "zeige_system": ist_administratorin,
        "simulationskern_verwalten": ist_administratorin,
    }

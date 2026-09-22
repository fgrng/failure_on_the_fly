"""Rollen und Sichtbarkeit der globalen Navigation."""

from functools import wraps
from typing import TYPE_CHECKING, Callable, Concatenate, ParamSpec

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from .models import Konto


AUTORIN_GRUPPE: str = "Autor:in"
AUSBILDERIN_GRUPPE: str = "Ausbilder:in"
FORSCHENDE_GRUPPE: str = "Forschende:r"
KONTOROLLEN: tuple[str, ...] = (
    AUTORIN_GRUPPE,
    AUSBILDERIN_GRUPPE,
    FORSCHENDE_GRUPPE,
)
P: ParamSpec = ParamSpec("P")


def _rollen(konto: "Konto") -> set[str]:
    """Liefert die für die Anwendung relevanten Gruppen eines Kontos."""
    return set(konto.groups.filter(name__in=KONTOROLLEN).values_list("name", flat=True))


def ist_autorin(konto: "Konto") -> bool:
    """Prüft die Entwicklungsrolle einschließlich Administrations-Override."""
    return ist_administratorin(konto) or AUTORIN_GRUPPE in _rollen(konto)


def ist_administratorin(konto: "Konto") -> bool:
    """Prüft die Administrationsrolle."""
    return konto.is_superuser


def rolle_oder_administration(gruppe: str) -> Callable[["Konto"], bool]:
    """Erzeugt ein Rollen-Prädikat einschließlich Administrations-Override."""

    def praedikat(konto: "Konto") -> bool:
        return ist_administratorin(konto) or konto.groups.filter(name=gruppe).exists()

    return praedikat


def rolle_erforderlich(
    rollen_pruefung: Callable[["Konto"], bool],
) -> Callable[
    [Callable[Concatenate[HttpRequest, P], HttpResponse]],
    Callable[Concatenate[HttpRequest, P], HttpResponse],
]:
    """Erzeugt einen View-Decorator, der eine Rolle mit 403 durchsetzt."""

    def decorator(
        view: Callable[Concatenate[HttpRequest, P], HttpResponse],
    ) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
        @wraps(view)
        def geschuetzte_view(
            request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
        ) -> HttpResponse:
            if not rollen_pruefung(request.user):
                return HttpResponse(status=403)
            return view(request, *args, **kwargs)

        return geschuetzte_view

    return decorator


autorin_erforderlich = rolle_erforderlich(ist_autorin)
administratorin_erforderlich = rolle_erforderlich(ist_administratorin)


def navigation(request: HttpRequest) -> dict[str, bool]:
    """Stellt der Sidebar jede Sichtbarkeit als fertig berechnetes Boolean bereit."""
    if not request.user.is_authenticated:
        return {
            "zeige_entwicklung": False,
            "zeige_ausbildung_kuratieren": False,
            "zeige_teilnahme": False,
            "zeige_abschriften": False,
            "zeige_forschung": False,
            "zeige_system": False,
        }

    rollen: set[str] = _rollen(request.user)
    administration: bool = ist_administratorin(request.user)
    return {
        "zeige_entwicklung": administration or AUTORIN_GRUPPE in rollen,
        "zeige_ausbildung_kuratieren": administration or AUSBILDERIN_GRUPPE in rollen,
        "zeige_teilnahme": not rollen and not administration,
        # Die Abschrift hängt am Konto, nicht an einer Rolle (ADR-0043): Wer ein
        # Teilnahme-Token hat, holt sie sich — unabhängig von den Rollen des Kontos.
        "zeige_abschriften": True,
        "zeige_forschung": administration or FORSCHENDE_GRUPPE in rollen,
        "zeige_system": administration,
    }

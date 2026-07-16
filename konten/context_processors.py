"""Template-Kontext für die rollenbasierte Navigation."""

from django.http import HttpRequest


def navigation(request: HttpRequest) -> dict[str, bool]:
    """Liefert die Sichtbarkeit der Sidebar-Bereiche für das aktuelle Konto."""
    gruppen: set[str] = (
        set(request.user.groups.values_list("name", flat=True))
        if request.user.is_authenticated
        else set()
    )
    ist_administratorin: bool = "Administrator:in" in gruppen
    hat_sonderrolle: bool = bool(gruppen)

    return {
        "zeige_entwicklung": ist_administratorin or "Autor:in" in gruppen,
        "zeige_ausbildung_kuratieren": ist_administratorin
        or "Ausbilder:in" in gruppen,
        "zeige_teilnahme": ist_administratorin
        or (request.user.is_authenticated and not hat_sonderrolle),
        "zeige_forschung": "Forschende:r" in gruppen,
        "zeige_system": ist_administratorin and request.user.is_staff,
    }

"""Django-Admin für Nutzerkonten."""

from collections.abc import Callable
from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm
from django.http import HttpRequest

from konten.models import Konto


class KontoCreationForm(AdminUserCreationForm):
    """Ergänzt die sichere Standard-Anlage um die Rollenfelder."""

    class Meta(AdminUserCreationForm.Meta):
        """Beschränkt die Anlage auf Kontodaten und Rollen."""

        model = Konto
        fields = ("username", "is_active", "is_superuser", "groups")


@admin.register(Konto)
class KontoAdmin(UserAdmin):
    """Verwaltet Konten mit Djangos sicherer Passwortbehandlung."""

    # is_staff bleibt überall unsichtbar: Konto.save() leitet es aus
    # is_superuser ab, ein zweiter Anzeigeort wäre eine zweite Wahrheit.
    list_display: tuple[str, ...] = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_superuser",
    )
    list_filter: tuple[str, ...] = ("is_superuser", "is_active", "groups")
    fieldsets: tuple[tuple[str | None, dict[str, Any]], ...] = (
        (None, {"fields": ("username", "password")}),
        ("Persönliche Angaben", {"fields": ("first_name", "last_name", "email")}),
        ("Berechtigungen", {"fields": ("is_active", "is_superuser", "groups")}),
        ("Wichtige Daten", {"fields": ("last_login", "date_joined")}),
    )
    add_form: type[KontoCreationForm] = KontoCreationForm
    add_fieldsets: tuple[tuple[str | None, dict[str, Any]], ...] = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "usable_password",
                    "password1",
                    "password2",
                    "is_active",
                    "is_superuser",
                    "groups",
                ),
            },
        ),
    )

    def has_delete_permission(
        self, request: HttpRequest, obj: Konto | None = None
    ) -> bool:
        """Verweigert das Löschen von Konten."""
        # #156 legt die Behandlung von Konto-Löschbegehren noch fest.
        return False

    def get_actions(
        self, request: HttpRequest
    ) -> dict[str, tuple[Callable[..., Any], str, str]]:
        """Blendet das Massenlöschen aus, bis #156 entschieden ist."""
        actions: dict[str, tuple[Callable[..., Any], str, str]] = super().get_actions(
            request
        )
        actions.pop("delete_selected", None)
        return actions

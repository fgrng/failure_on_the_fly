"""Django-Admin für Nutzerkonten."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm

from konten.models import Konto


class KontoCreationForm(AdminUserCreationForm):
    """Ergänzt die sichere Standard-Anlage um die Rollenfelder."""

    class Meta(AdminUserCreationForm.Meta):
        model = Konto
        fields = ("username", "is_active", "is_superuser", "groups")


@admin.register(Konto)
class KontoAdmin(UserAdmin):
    """Verwaltet Konten mit Djangos sicherer Passwortbehandlung."""

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Persönliche Angaben", {"fields": ("first_name", "last_name", "email")}),
        ("Berechtigungen", {"fields": ("is_active", "is_superuser", "groups")}),
        ("Wichtige Daten", {"fields": ("last_login", "date_joined")}),
    )
    add_form = KontoCreationForm
    add_fieldsets = (
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

    def has_delete_permission(self, request, obj=None) -> bool:
        # #156 entscheidet erst noch, was ein Konto-Löschbegehren bedeutet.
        return False

    def get_actions(self, request):
        """Blendet das Massenlöschen aus, bis #156 entschieden ist."""
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

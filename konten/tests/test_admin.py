"""Integrationstests für die Kontoverwaltung im Django-Admin."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class KontoAdminTests(TestCase):
    """Die Administration verwaltet Konten über Djangos sichere UserAdmin-Naht."""

    def test_administration_legt_konto_mit_gehashtem_passwort_an(self) -> None:
        """Ein im Admin angelegtes Konto speichert das Passwort nie im Klartext."""
        admin = get_user_model().objects.create_user(
            username="admin", password="admin-passwort", is_superuser=True
        )
        self.client.force_login(admin)

        response = self.client.post(
            "/admin/konten/konto/add/",
            {
                "username": "ada",
                "password1": "sicheres-passwort",
                "password2": "sicheres-passwort",
            },
        )

        self.assertEqual(response.status_code, 302)
        konto = get_user_model().objects.get(username="ada")
        self.assertTrue(konto.check_password("sicheres-passwort"))
        self.assertNotEqual(konto.password, "sicheres-passwort")

    def test_administration_vergibt_rolle_und_superuser_beim_anlegen(self) -> None:
        """Die Anlage-Maske kann fachliche Rolle und Administration setzen."""
        admin = get_user_model().objects.create_user(
            username="admin", password="admin-passwort", is_superuser=True
        )
        gruppe = Group.objects.get(name="Autor:in")
        self.client.force_login(admin)

        response = self.client.post(
            "/admin/konten/konto/add/",
            {
                "username": "ada",
                "password1": "sicheres-passwort",
                "password2": "sicheres-passwort",
                "is_active": "on",
                "is_superuser": "on",
                "groups": [str(gruppe.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        konto = get_user_model().objects.get(username="ada")
        self.assertTrue(konto.is_superuser)
        self.assertTrue(konto.is_staff)
        self.assertTrue(konto.groups.filter(pk=gruppe.pk).exists())

    def test_nur_superuser_erreicht_nicht_leeren_admin_index(self) -> None:
        """Die Administration bleibt der einzige Zugang zum Nutzerbereich."""
        konto = get_user_model().objects.create_user(
            username="ada", password="sicheres-passwort"
        )
        self.client.force_login(konto)

        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(response, "/admin/login/?next=/admin/")

        konto.is_superuser = True
        konto.save()
        self.client.force_login(konto)

        response = self.client.get(reverse("admin:index"))

        self.assertContains(response, 'href="/admin/konten/konto/"')
        self.assertContains(response, 'href="/admin/auth/group/"')

    def test_admin_masken_zeigen_nur_rollenfelder_und_keine_loeschwege(self) -> None:
        """Konten bleiben bearbeitbar, aber bis #156 weder löschbar noch individualisiert."""
        admin = get_user_model().objects.create_user(
            username="admin", password="admin-passwort", is_superuser=True
        )
        konto = get_user_model().objects.create_user(
            username="ada", password="sicheres-passwort"
        )
        self.client.force_login(admin)

        detail = self.client.get(reverse("admin:konten_konto_change", args=(konto.pk,)))
        liste = self.client.get(reverse("admin:konten_konto_changelist"))
        loeschen = self.client.get(reverse("admin:konten_konto_delete", args=(konto.pk,)))

        self.assertContains(detail, 'name="groups"')
        self.assertContains(detail, 'name="is_superuser"')
        self.assertNotContains(detail, 'name="is_staff"')
        self.assertNotContains(detail, 'name="user_permissions"')
        self.assertNotContains(detail, "deletelink")
        self.assertNotContains(liste, "delete_selected")
        self.assertEqual(loeschen.status_code, 403)

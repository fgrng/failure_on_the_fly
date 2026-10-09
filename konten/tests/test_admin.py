"""Integrationstests für die Kontoverwaltung im Django-Admin."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from config.tests.aufbau import konto_mit_rollen
from konten.models import Konto


class KontoAdminTests(TestCase):
    """Die Administration verwaltet Konten über Djangos sichere UserAdmin-Naht."""

    def test_administration_legt_konto_mit_gehashtem_passwort_an(self) -> None:
        """Ein im Admin angelegtes Konto speichert das Passwort nie im Klartext."""
        administratorin: Konto = get_user_model().objects.create_user(
            username="administratorin",
            password="sicheres-passwort",
            is_superuser=True,
        )
        self.client.force_login(administratorin)

        response: HttpResponse = self.client.post(
            reverse("admin:konten_konto_add"),
            {
                "username": "ada",
                "password1": "sicheres-passwort",
                "password2": "sicheres-passwort",
            },
        )

        self.assertEqual(response.status_code, 302)
        konto: Konto = get_user_model().objects.get(username="ada")
        self.assertTrue(konto.check_password("sicheres-passwort"))
        self.assertNotEqual(konto.password, "sicheres-passwort")

    def test_administration_vergibt_rolle_und_superuser_beim_anlegen(self) -> None:
        """Die Anlage-Maske kann fachliche Rolle und Administration setzen."""
        administratorin: Konto = get_user_model().objects.create_user(
            username="administratorin",
            password="sicheres-passwort",
            is_superuser=True,
        )
        gruppe: Group = Group.objects.get(name="Autor:in")
        self.client.force_login(administratorin)

        response: HttpResponse = self.client.post(
            reverse("admin:konten_konto_add"),
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
        konto: Konto = get_user_model().objects.get(username="ada")
        self.assertTrue(konto.is_superuser)
        self.assertTrue(konto.is_staff)
        self.assertTrue(konto.groups.filter(pk=gruppe.pk).exists())

    def test_administration_aendert_passwort_gehasht(self) -> None:
        """Ein im Admin neu gesetztes Passwort wird gehasht gespeichert."""
        administratorin: Konto = get_user_model().objects.create_user(
            username="administratorin",
            password="sicheres-passwort",
            is_superuser=True,
        )
        konto: Konto = get_user_model().objects.create_user(
            username="ada", password="altes-passwort"
        )
        self.client.force_login(administratorin)

        response: HttpResponse = self.client.post(
            reverse("admin:auth_user_password_change", args=(konto.pk,)),
            {"password1": "neues-passwort", "password2": "neues-passwort"},
        )

        self.assertEqual(response.status_code, 302)
        konto.refresh_from_db()
        self.assertTrue(konto.check_password("neues-passwort"))

    def test_administration_entzieht_rolle(self) -> None:
        """Die Änderungsmaske entfernt eine zuvor zugewiesene fachliche Rolle."""
        administratorin: Konto = get_user_model().objects.create_user(
            username="administratorin",
            password="sicheres-passwort",
            is_superuser=True,
        )
        gruppe: Group = Group.objects.get(name="Autor:in")
        konto: Konto = get_user_model().objects.create_user(
            username="ada", password="sicheres-passwort"
        )
        konto.groups.add(gruppe)
        self.client.force_login(administratorin)

        response: HttpResponse = self.client.post(
            reverse("admin:konten_konto_change", args=(konto.pk,)),
            {
                "username": konto.username,
                "is_active": "on",
                "date_joined_0": konto.date_joined.strftime("%Y-%m-%d"),
                "date_joined_1": konto.date_joined.strftime("%H:%M:%S"),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(konto.groups.filter(pk=gruppe.pk).exists())

    def test_nur_superuser_erreicht_nicht_leeren_admin_index(self) -> None:
        """Die Administration bleibt der einzige Zugang zum Nutzerbereich."""
        konto: Konto = get_user_model().objects.create_user(
            username="ada", password="sicheres-passwort"
        )
        self.client.force_login(konto)

        response: HttpResponse = self.client.get(reverse("admin:index"))

        self.assertRedirects(response, "/admin/login/?next=/admin/")

        konto.is_superuser = True
        konto.save()
        self.client.force_login(konto)

        response: HttpResponse = self.client.get(reverse("admin:index"))

        self.assertContains(
            response, f'href="{reverse("admin:konten_konto_changelist")}"'
        )
        self.assertContains(
            response, f'href="{reverse("admin:auth_group_changelist")}"'
        )

    def test_masken_zeigen_nur_rollenfelder(self) -> None:
        """Konten tragen Rollen und Administration, aber keine Einzelrechte."""
        administratorin: Konto = konto_mit_rollen("administratorin", is_superuser=True)
        konto: Konto = konto_mit_rollen("ada")
        self.client.force_login(administratorin)

        detail = self.client.get(reverse("admin:konten_konto_change", args=(konto.pk,)))
        liste = self.client.get(reverse("admin:konten_konto_changelist"))

        felder: set[str] = set(detail.context["adminform"].form.fields)
        self.assertLessEqual({"groups", "is_superuser"}, felder)
        self.assertFalse({"is_staff", "user_permissions"} & felder)
        spalten: tuple[str, ...] = tuple(liste.context["cl"].list_display)
        self.assertIn("is_superuser", spalten)
        self.assertNotIn("is_staff", spalten)

    def test_konten_sind_nicht_loeschbar(self) -> None:
        """Bis #156 löscht weder die Löschseite noch die Sammelaktion ein Konto."""
        administratorin: Konto = konto_mit_rollen("administratorin", is_superuser=True)
        konto: Konto = konto_mit_rollen("ada")
        self.client.force_login(administratorin)

        loeschen: HttpResponse = self.client.get(
            reverse("admin:konten_konto_delete", args=(konto.pk,))
        )
        self.client.post(
            reverse("admin:konten_konto_changelist"),
            {
                "action": "delete_selected",
                "_selected_action": [konto.pk],
                "post": "yes",
            },
        )

        self.assertEqual(loeschen.status_code, 403)
        self.assertTrue(Konto.objects.filter(pk=konto.pk).exists())

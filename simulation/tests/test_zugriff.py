"""Zugriffsvertrag aller Routen der App simulation (#476)."""

from urllib.parse import quote

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.urls.converters import IntConverter
from django.urls.resolvers import URLPattern

from config.tests.aufbau import konto_mit_rollen
from simulation.urls import app_name, urlpatterns


def _url(muster: URLPattern) -> str:
    # Füllt jeden Pfadparameter mit einem Platzhalter passenden Typs.
    kwargs: dict[str, int | str] = {
        name: 1 if isinstance(konverter, IntConverter) else "x"
        for name, konverter in muster.pattern.converters.items()
    }
    return reverse(f"{app_name}:{muster.name}", kwargs=kwargs)


class AnonymerZugriffTests(TestCase):
    """Anonyme Anfragen an kontogebundene Seiten führen auf den Login."""

    def test_leitet_anonym_auf_den_login_um(self) -> None:
        for muster in urlpatterns:
            url: str = _url(muster)
            with self.subTest(route=muster.name):
                response: HttpResponse = self.client.post(url)

                self.assertRedirects(
                    response,
                    f"/accounts/login/?next={quote(url)}",
                    fetch_redirect_response=False,
                )

    def test_weist_konto_ohne_rolle_weiter_ab(self) -> None:
        """Angemeldet ohne Rolle bleibt es bei der Zugriffsverweigerung."""
        self.client.force_login(konto_mit_rollen("studi"))

        for muster in urlpatterns:
            with self.subTest(route=muster.name):
                self.assertEqual(self.client.post(_url(muster)).status_code, 403)

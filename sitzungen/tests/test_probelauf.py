"""HTTP-Tests für den schreibfreien Probelauf."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from vignetten.models import Vignette


class ProbelaufStartTests(TestCase):
    """Die HTTP-Naht startet einen Probelauf über einem festen Tripel."""

    def setUp(self) -> None:
        """Legt die sichtbaren und fremden Entwürfe für die HTTP-Tests an."""

        self.ada: Konto = get_user_model().objects.create_user(username="ada")
        grace: Konto = get_user_model().objects.create_user(username="grace")
        self.kern: Simulationskern = Simulationskern.objects.anlegen(
            rahmenhandlung_einleitung=(
                "$lehrperson_anrede $lehrperson_name begleitet Sie bei "
                "$fach in Klasse $klassenstufe."
            )
        )
        self.kern.finalisieren()
        self.konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter={"skript": []}
        )
        ModellKonfiguration.objects.aktivieren(self.konfiguration)
        self.entwurf: Vignette = Vignette.objects.anlegen(self.ada)
        self.entwurf.historie.name = "Eigener Entwurf"
        self.entwurf.historie.save()
        self.entwurf.schuelerin_name = "Mia"
        self.entwurf.schuelerin_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.lehrperson_name = "Weber"
        self.entwurf.lehrperson_geschlecht = Vignette.Geschlecht.WEIBLICH
        self.entwurf.fach = "Mathematik"
        self.entwurf.thema = "Brüche"
        self.entwurf.klassenstufe = "5"
        self.entwurf.save()
        fremder_entwurf: Vignette = Vignette.objects.anlegen(grace)
        fremder_entwurf.historie.name = "Fremder Entwurf"
        fremder_entwurf.historie.save()
        self.client.force_login(self.ada)

    def test_auswahl_zeigt_nur_eigene_entwuerfe_und_startet_rahmenhandlung(
        self,
    ) -> None:
        """Der Start pinnt das automatische Tripel in der Session und rendert einleitend."""

        auswahl: HttpResponse = self.client.get(reverse("sitzungen:probelauf_auswahl"))

        self.assertContains(auswahl, "Eigener Entwurf")
        self.assertNotContains(auswahl, "Fremder Entwurf")

        response: HttpResponse = self.client.post(
            reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk])
        )

        self.assertContains(response, "Frau Weber begleitet Sie bei Mathematik in Klasse 5.")
        session = self.client.session
        self.assertEqual(session["probelauf"], {
            "vignette_pk": self.entwurf.pk,
            "kern_pk": self.kern.pk,
            "modell_konfiguration_pk": self.konfiguration.pk,
            "gespraechsschritte": [],
        })

    def test_startzustand_ueberlebt_folge_request_ohne_domaenenschreiben(
        self,
    ) -> None:
        """Der Probelauf bleibt allein als Session-Zustand über mehrere Requests erhalten."""

        anzahl_vignetten: int = Vignette.objects.count()
        anzahl_kerne: int = Simulationskern.objects.count()
        anzahl_konfigurationen: int = ModellKonfiguration.objects.count()
        self.client.post(reverse("sitzungen:probelauf_starten", args=[self.entwurf.pk]))

        self.client.get(reverse("sitzungen:probelauf_auswahl"))

        self.assertEqual(self.client.session["probelauf"], {
            "vignette_pk": self.entwurf.pk,
            "kern_pk": self.kern.pk,
            "modell_konfiguration_pk": self.konfiguration.pk,
            "gespraechsschritte": [],
        })
        self.assertEqual(Vignette.objects.count(), anzahl_vignetten)
        self.assertEqual(Simulationskern.objects.count(), anzahl_kerne)
        self.assertEqual(ModellKonfiguration.objects.count(), anzahl_konfigurationen)

"""Befüllt eine frische Entwicklungsinstanz mit Testdaten für einen manuellen Testlauf.

Best-Practice-Hinweise für dieses Command:

* **Idempotent.** Jeder Aufruf ist sicher wiederholbar; bereits vorhandene
  Objekte werden erkannt und nicht doppelt angelegt.
* **Offizielle Nähte.** Vignetten, Kern und Trainings tragen strikte
  Lebenszyklus-Invarianten. Djangos ``loaddata``/Fixtures umgehen diese Nähte
  und scheitern hier an ``save()``. Deshalb baut der Seed alle Objekte über
  ``anlegen()``/``finalisieren()``/``veroeffentlichen()`` — genau wie die App.
* **Nur Entwicklung.** Der Seed weigert sich bei ``DEBUG=False``, damit keine
  Testkonten in eine Produktivdatenbank geraten.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from simulation.models import ModellKonfiguration, Simulationskern
from training.models import Training
from vignetten.models import Vignette


# Ein bewusst schwaches, dokumentiertes Entwicklungspasswort für alle Testkonten.
ENTWICKLUNGSPASSWORT: str = "entwicklung"

# Die Testkonten je Rolle. Der Schlüssel ist der Anmeldename, der Wert die Rolle
# (Gruppenname aus konten.apps.KONTOROLLEN) oder None für ein reines
# Teilnehmerinnenkonto ohne Sonderrolle.
TESTKONTEN: dict[str, str | None] = {
    "admin": "Administrator:in",
    "autorin": "Autor:in",
    "ausbilderin": "Ausbilder:in",
    "forschende": "Forschende:r",
    "studi": None,
}

# Ein funktionsfähiger Simulationskern für einen echten Testlauf. Die Vorlagen
# nutzen ausschließlich vertragskonforme Platzhalter (siehe VERTRAG_PROMPT bzw.
# VERTRAG_RAHMEN in simulation.models).
SYSTEM_PROMPT_VORLAGE: str = (
    "Du bist $schuelerin_name, eine simulierte Schüler:in der Klassenstufe "
    "$klassenstufe im Fach $fach zum Thema $thema.\n\n"
    "Du wendest durchgehend und konsequent dieses Fehlermuster an:\n"
    "$fehlermuster_beschreibung\n\n"
    "Du bleibst in der Rolle der Schüler:in, sprichst altersgemäß und gibst "
    "dein Fehlermuster niemals als solches zu erkennen. Du kennst deine "
    "eigene Denkweise als richtig."
)
USER_PROMPT_VORLAGE: str = (
    "Deine Aufgabe war:\n$lernauftrag\n\n"
    "Deine Bearbeitung im Arbeitsheft:\n$arbeitsheft_beschreibung"
)
RAHMEN_EINLEITUNG: str = (
    "Du hospitierst im Fach $fach in einer $klassenstufe. "
    "$lehrperson_anrede $lehrperson_name bittet dich, mit $schuelerin_name über "
    "$schuelerin_possessiv Bearbeitung ins Gespräch zu kommen."
)
RAHMEN_DEBRIEF: str = (
    "$lehrperson_anrede $lehrperson_name kommt auf dich zu: „Und, was ist Ihnen "
    "bei $schuelerin_name aufgefallen?“"
)

# Die aktive Modell-Konfiguration für den manuellen Testlauf: OpenAI über
# LiteLLM. Braucht OPENAI_API_KEY in der .env (siehe .env.example).
SIMULATIONSMODELL: str = "openai/gpt-4o"
SIMULATIONSPARAMETER: dict[str, object] = {"temperature": 0.2}

# Ein kleines Fake-Skript für Offline-Klicktests ohne API-Schlüssel. Zum
# Aktivieren: ModellKonfiguration.objects.aktivieren(fake_konfiguration).
FAKE_SKRIPT: list[dict[str, str]] = [
    {"denkspur": "Ich addiere Zähler und Nenner.", "aeusserung": "Das ist doch 2/7!"},
    {"denkspur": "Wieder Zähler und Nenner getrennt.", "aeusserung": "Also 3/9."},
]

# Die finalen Vignetten des Seeds. Jede beschreibt ein stabiles Fehlermuster.
VIGNETTEN: list[dict[str, object]] = [
    {
        "historienname": "Brüche addieren",
        "fehlermuster_beschreibung": (
            "Beim Addieren zweier Brüche addierst du Zähler mit Zähler und "
            "Nenner mit Nenner (1/2 + 1/3 = 2/5)."
        ),
        "lernauftrag": "Berechne 1/2 + 1/3 und begründe dein Vorgehen.",
        "arbeitsheft_beschreibung": (
            "Notiert steht: 1/2 + 1/3 = 2/5, daneben die Rechnung 1+1=2 und 2+3=5."
        ),
        "arbeitsheft_text": "1/2 + 1/3 = 2/5",
        "schuelerin_name": "Mia",
        "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "lehrperson_name": "Berger",
        "lehrperson_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "fach": "Mathematik",
        "thema": "Bruchrechnung",
        "klassenstufe": "6. Klasse",
        "referenzdiagnose": (
            "Zähler-Nenner-Addition: Der Bruchstrich wird als Trenner zweier "
            "unabhängiger Zahlen statt als Division gedeutet."
        ),
        "budget_typ": Vignette.BudgetTyp.SCHRITTE,
        "budget_wert": 12,
    },
    {
        "historienname": "Multiplikation mit Null",
        "fehlermuster_beschreibung": (
            "Du behandelst die Multiplikation mit 0 wie eine Addition mit 0: "
            "Ein Faktor 0 lässt die andere Zahl unverändert (7 · 0 = 7)."
        ),
        "lernauftrag": "Berechne 7 · 0 und 0 · 4.",
        "arbeitsheft_beschreibung": "Notiert steht: 7 · 0 = 7 und 0 · 4 = 4.",
        "arbeitsheft_text": "7 · 0 = 7\n0 · 4 = 4",
        "schuelerin_name": "Jonas",
        "schuelerin_geschlecht": Vignette.Geschlecht.MAENNLICH,
        "lehrperson_name": "Berger",
        "lehrperson_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "fach": "Mathematik",
        "thema": "Multiplikation",
        "klassenstufe": "3. Klasse",
        "referenzdiagnose": (
            "Verwechslung des neutralen Elements: Die 0 der Addition wird auf "
            "die Multiplikation übertragen."
        ),
        "budget_typ": Vignette.BudgetTyp.SCHRITTE,
        "budget_wert": 10,
    },
]


class Command(BaseCommand):
    """Legt idempotent Konten, Kern, Modell-Konfiguration, Vignetten und Trainings an."""

    help = "Befüllt eine Entwicklungsinstanz mit Testdaten für einen manuellen Testlauf."

    def handle(self, *args: object, **options: object) -> None:
        """Führt den Seed in einer Transaktion aus; nur bei DEBUG=True."""
        if not settings.DEBUG:
            raise CommandError(
                "entwicklungsdaten_anlegen läuft nur mit DEBUG=True. "
                "Dieser Seed gehört nicht in eine Produktivdatenbank."
            )

        with transaction.atomic():
            konten = self._konten_anlegen()
            kern = self._kern_sicherstellen()
            self._modell_konfiguration_sicherstellen()
            vignetten = self._vignetten_anlegen(konten["autorin"], kern)
            self._trainings_anlegen(konten["ausbilderin"], vignetten)

        self._zusammenfassung_ausgeben()

    def _konten_anlegen(self) -> dict[str, object]:
        """Legt je Rolle ein Testkonto an und weist die passende Gruppe zu."""
        konto_modell = get_user_model()
        konten: dict[str, object] = {}
        for anmeldename, rolle in TESTKONTEN.items():
            konto, neu = konto_modell.objects.get_or_create(username=anmeldename)
            if neu:
                konto.set_password(ENTWICKLUNGSPASSWORT)
                if rolle == "Administrator:in":
                    konto.is_staff = True
                    konto.is_superuser = True
                konto.save()
            if rolle is not None:
                konto.groups.add(Group.objects.get(name=rolle))
            konten[anmeldename] = konto
            self.stdout.write(
                f"  Konto {anmeldename} ({rolle or 'ohne Rolle'}) "
                f"{'angelegt' if neu else 'vorhanden'}."
            )
        return konten

    def _kern_sicherstellen(self) -> Simulationskern:
        """Stellt genau eine finale Simulationskern-Fassung bereit."""
        final = Simulationskern.objects.filter(
            zustand=Simulationskern.Zustand.FINAL
        ).order_by("-finalisiert_am", "-pk").first()
        if final is not None:
            self.stdout.write("  Simulationskern vorhanden.")
            return final
        if Simulationskern.objects.exists():
            raise CommandError(
                "Es existiert bereits ein nicht-finaler Simulationskern-Entwurf; "
                "bitte manuell finalisieren."
            )
        kern = Simulationskern.objects.anlegen(
            system_prompt_vorlage=SYSTEM_PROMPT_VORLAGE,
            user_prompt_vorlage=USER_PROMPT_VORLAGE,
            rahmenhandlung_einleitung=RAHMEN_EINLEITUNG,
            rahmenhandlung_debrief=RAHMEN_DEBRIEF,
        )
        kern.finalisieren()
        self.stdout.write("  Simulationskern angelegt und finalisiert.")
        return kern

    def _modell_konfiguration_sicherstellen(self) -> None:
        """Legt eine OpenAI- und eine Fake-Konfiguration an und aktiviert OpenAI."""
        openai = ModellKonfiguration.objects.filter(
            sprachmodell=SIMULATIONSMODELL
        ).first() or ModellKonfiguration.objects.create(
            sprachmodell=SIMULATIONSMODELL, parameter=SIMULATIONSPARAMETER
        )
        if not ModellKonfiguration.objects.filter(sprachmodell="fake").exists():
            ModellKonfiguration.objects.create(
                sprachmodell="fake", parameter={"skript": FAKE_SKRIPT}
            )
        ModellKonfiguration.objects.aktivieren(openai)
        self.stdout.write(
            f"  Modell-Konfiguration '{SIMULATIONSMODELL}' aktiv "
            "(Fake-Konfig für Offline-Tests angelegt)."
        )

    def _vignetten_anlegen(
        self, autorin: object, kern: Simulationskern
    ) -> list[Vignette]:
        """Legt je Beschreibung eine finale Vignette an, sofern noch nicht vorhanden."""
        from vignetten.models import Vignettenhistorie

        finale: list[Vignette] = []
        for beschreibung in VIGNETTEN:
            historienname = str(beschreibung["historienname"])
            vorhandene = Vignette.objects.filter(
                historie__name=historienname, zustand=Vignette.Zustand.FINAL
            ).first()
            if vorhandene is not None:
                finale.append(vorhandene)
                self.stdout.write(f"  Vignette '{historienname}' vorhanden.")
                continue

            vignette = Vignette.objects.anlegen(autorin)
            historie: Vignettenhistorie = vignette.historie
            historie.name = historienname
            historie.save(update_fields=["name"])
            for feld, wert in beschreibung.items():
                if feld == "historienname":
                    continue
                setattr(vignette, feld, wert)
            vignette.save()
            vignette.finalisieren()
            finale.append(vignette)
            self.stdout.write(f"  Vignette '{historienname}' angelegt und finalisiert.")
        return finale

    def _trainings_anlegen(
        self, ausbilderin: object, vignetten: list[Vignette]
    ) -> None:
        """Legt ein veröffentlichtes und ein Entwurfs-Training an."""
        veroeffentlicht, neu = Training.objects.get_or_create(
            name="Diagnose-Grundlagen", eigentuemerin=ausbilderin
        )
        if neu:
            veroeffentlicht.vignetten.add(*vignetten)
            veroeffentlicht.veroeffentlichen()
            self.stdout.write("  Training 'Diagnose-Grundlagen' angelegt und veröffentlicht.")
        else:
            self.stdout.write("  Training 'Diagnose-Grundlagen' vorhanden.")

        entwurf, neu = Training.objects.get_or_create(
            name="Entwurf: Bruchrechnung vertiefen", eigentuemerin=ausbilderin
        )
        if neu and vignetten:
            entwurf.vignetten.add(vignetten[0])
            self.stdout.write("  Training 'Entwurf: Bruchrechnung vertiefen' als Entwurf angelegt.")
        elif not neu:
            self.stdout.write("  Training 'Entwurf: Bruchrechnung vertiefen' vorhanden.")

    def _zusammenfassung_ausgeben(self) -> None:
        """Nennt die Anmeldedaten für den manuellen Testlauf."""
        self.stdout.write(self.style.SUCCESS("\nEntwicklungsdaten bereit."))
        self.stdout.write(f"Passwort für alle Testkonten: {ENTWICKLUNGSPASSWORT}")
        self.stdout.write("Konten: " + ", ".join(TESTKONTEN))
        self.stdout.write(
            "Aktives Modell: "
            f"{SIMULATIONSMODELL} (setze OPENAI_API_KEY in der .env)."
        )

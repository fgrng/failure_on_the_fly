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

from konten.apps import KONTOROLLEN
from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.standardkern import STANDARDKERN_VORLAGEN
from training.models import Training
from vignetten.models import Vignette


# Ein bewusst schwaches, dokumentiertes Entwicklungspasswort für alle Testkonten.
ENTWICKLUNGSPASSWORT: str = "entwicklung"

# Die Testkonten. Der Schlüssel ist der Anmeldename, der Wert die Liste der
# zugewiesenen Rollen (Gruppennamen aus konten.apps.KONTOROLLEN). "autor" trägt
# alle Rollen gleichzeitig, "studi" ist ein reines Teilnehmerinnenkonto ohne
# Sonderrolle.
TESTKONTEN: dict[str, list[str]] = {
    "autor": list(KONTOROLLEN),
    "studi": [],
}

# Die optionale OpenAI-Konfiguration für einen echten Modelllauf.
SIMULATIONSMODELL: str = "openai/gpt-4o"
SIMULATIONSPARAMETER: dict[str, object] = {"temperature": 0.2}

# Die aktive Fake-Antwort für beliebig viele Offline-Gesprächsschritte. Der
# Adapter wird je Schritt neu erzeugt und beginnt deshalb immer von vorn.
FAKE_SKRIPT: list[dict[str, str]] = [
    {
        "denkspur": "Ich bleibe bei meiner eigenen Regel und prüfe die Frage damit.",
        "aeusserung": "Ich habe die Zeichen so gelesen und dann genau so gerechnet.",
    },
]

# Die finalen Vignetten des Seeds. Jede beschreibt ein stabiles Fehlermuster.
VIGNETTEN: list[dict[str, object]] = [
    {
        "historienname": "Gleichheitszeichen als Rechenaufforderung",
        "fehlermuster_beschreibung": (
            "Du verstehst das Gleichheitszeichen als Aufforderung, die Rechnung "
            "links davon auszurechnen, nicht als Zeichen dafür, dass beide Seiten "
            "denselben Wert haben. Bei einer Platzhalteraufgabe trägst du deshalb "
            "das Ergebnis der linken Rechnung in die Lücke ein und beachtest den "
            "Term rechts von der Lücke nicht weiter."
        ),
        "lernauftrag": "Setze die passende Zahl ein: 8 + 4 = ___ + 5.",
        "arbeitsheft_beschreibung": (
            "Auf dem Arbeitsblatt steht die Platzhalteraufgabe 8 + 4 = ___ + 5. "
            "Lukas hat 12 in die Lücke eingetragen."
        ),
        "arbeitsheft_text": "8 + 4 = 12 + 5",
        "schuelerin_name": "Lukas",
        "schuelerin_geschlecht": Vignette.Geschlecht.MAENNLICH,
        "lehrperson_name": "Berger",
        "lehrperson_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "fach": "Mathematik",
        "thema": "Gleichheitszeichen und Platzhalter",
        "klassenstufe": "5. Klasse",
        "referenzdiagnose": (
            "Operationales Verständnis des Gleichheitszeichens: Lukas deutet es "
            "als Rechenaufforderung statt relational als Äquivalenzzeichen. Er "
            "fokussiert 8 + 4 und blendet + 5 rechts vom Platzhalter aus."
        ),
        "budget_typ": Vignette.BudgetTyp.SCHRITTE,
        "budget_wert": 10,
    },
    {
        "historienname": "Variablen als Objektbezeichnungen",
        "fehlermuster_beschreibung": (
            "Du verstehst Variablen als Abkürzungen für Gegenstände oder Wörter, "
            "nicht als Platzhalter für Anzahlen. Deshalb liest du 6S als sechs "
            "Studierende und P als einen Professor und schreibst 6S = P. Auch bei "
            "Nachfragen hältst du an dieser Abkürzungslogik fest."
        ),
        "lernauftrag": (
            "An einer Universität gibt es sechsmal so viele Studierende wie "
            "Professoren. Schreibe eine Gleichung mit S für die Anzahl der "
            "Studierenden und P für die Anzahl der Professoren."
        ),
        "arbeitsheft_beschreibung": (
            "Julia hat zur beschriebenen Beziehung die Gleichung 6S = P "
            "aufgeschrieben."
        ),
        "arbeitsheft_text": "6S = P",
        "schuelerin_name": "Julia",
        "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "lehrperson_name": "Kant",
        "lehrperson_geschlecht": Vignette.Geschlecht.MAENNLICH,
        "fach": "Mathematik",
        "thema": "Variablen und Gleichungen",
        "klassenstufe": "7. Klasse",
        "referenzdiagnose": (
            "Variable als Objektbezeichnung: Julia liest S und P als Etiketten "
            "für Studierende und Professoren statt als Anzahlen. Dadurch kehrt "
            "sie die Beziehung S = 6P zur Gleichung 6S = P um."
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
            konten: dict[str, object] = self._konten_anlegen()
            kern: Simulationskern = self._kern_sicherstellen()
            self._modell_konfiguration_sicherstellen()
            vignetten: list[Vignette] = self._vignetten_anlegen(konten["autor"], kern)
            self._trainings_anlegen(konten["autor"], vignetten)

        self._zusammenfassung_ausgeben()

    def _konten_anlegen(self) -> dict[str, object]:
        """Legt je Testkonto an und weist die zugehörigen Gruppen zu."""
        konto_modell: type[Konto] = get_user_model()
        konten: dict[str, object] = {}
        for anmeldename, rollen in TESTKONTEN.items():
            konto, neu = konto_modell.objects.get_or_create(username=anmeldename)
            if neu:
                konto.set_password(ENTWICKLUNGSPASSWORT)
                if "Administrator:in" in rollen:
                    konto.is_staff = True
                    konto.is_superuser = True
                konto.save()
            for rolle in rollen:
                konto.groups.add(Group.objects.get(name=rolle))
            konten[anmeldename] = konto
            self.stdout.write(
                f"  Konto {anmeldename} ({', '.join(rollen) or 'ohne Rolle'}) "
                f"{'angelegt' if neu else 'vorhanden'}."
            )
        return konten

    def _kern_sicherstellen(self) -> Simulationskern:
        """Stellt die aktuelle Standardkern-Fassung bereit."""
        final: Simulationskern | None = Simulationskern.objects.filter(
            zustand=Simulationskern.Zustand.FINAL
        ).order_by("-finalisiert_am", "-pk").first()
        if final is not None and all(
            getattr(final, feld) == wert
            for feld, wert in STANDARDKERN_VORLAGEN.items()
        ):
            self.stdout.write("  Simulationskern vorhanden.")
            return final
        if Simulationskern.objects.filter(
            zustand=Simulationskern.Zustand.ENTWURF
        ).exists():
            raise CommandError(
                "Es existiert bereits ein Simulationskern-Entwurf; "
                "bitte manuell finalisieren."
            )
        kern: Simulationskern = (
            final.bearbeiten()
            if final is not None
            else Simulationskern.objects.anlegen(**STANDARDKERN_VORLAGEN)
        )
        if final is not None:
            for feld, wert in STANDARDKERN_VORLAGEN.items():
                setattr(kern, feld, wert)
            kern.save(update_fields=list(STANDARDKERN_VORLAGEN))
        kern.finalisieren()
        self.stdout.write("  Simulationskern angelegt und finalisiert.")
        return kern

    def _modell_konfiguration_sicherstellen(self) -> None:
        """Legt OpenAI und Fake an und aktiviert Fake für Offline-Klicktests."""
        ModellKonfiguration.objects.filter(
            sprachmodell=SIMULATIONSMODELL
        ).first() or ModellKonfiguration.objects.create(
            sprachmodell=SIMULATIONSMODELL, parameter=SIMULATIONSPARAMETER
        )
        fake_parameter: dict[str, object] = {"skript": FAKE_SKRIPT}
        fake: ModellKonfiguration = ModellKonfiguration.objects.filter(
            sprachmodell="fake", parameter=fake_parameter
        ).first() or ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter=fake_parameter
        )
        ModellKonfiguration.objects.aktivieren(fake)
        self.stdout.write(
            "  Modell-Konfiguration 'fake' für Offline-Tests aktiv "
            f"('{SIMULATIONSMODELL}' ebenfalls vorhanden)."
        )

    def _vignetten_anlegen(
        self, autorin: object, kern: Simulationskern
    ) -> list[Vignette]:
        """Legt je Beschreibung eine finale Vignette an, sofern noch nicht vorhanden."""
        from vignetten.models import Vignettenhistorie

        finale: list[Vignette] = []
        for beschreibung in VIGNETTEN:
            historienname: str = str(beschreibung["historienname"])
            vorhandene: Vignette | None = Vignette.objects.filter(
                historie__name=historienname, zustand=Vignette.Zustand.FINAL
            ).order_by("-finalisiert_am", "-pk").first()
            if vorhandene is not None:
                if vorhandene.gepinnter_kern_id == kern.pk:
                    finale.append(vorhandene)
                    self.stdout.write(f"  Vignette '{historienname}' vorhanden.")
                    continue
                neue_fassung: Vignette = vorhandene.bearbeiten()
                neue_fassung.vorspulen()
                neue_fassung.finalisieren()
                finale.append(neue_fassung)
                self.stdout.write(
                    f"  Vignette '{historienname}' auf neuen Kern vorgespult."
                )
                continue

            vignette: Vignette = Vignette.objects.anlegen(autorin)
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
        veroeffentlicht.vignetten.set(vignetten)
        if neu:
            veroeffentlicht.veroeffentlichen()
            self.stdout.write("  Training 'Diagnose-Grundlagen' angelegt und veröffentlicht.")
        else:
            self.stdout.write("  Training 'Diagnose-Grundlagen' vorhanden.")

        entwurf: Training | None = Training.objects.filter(
            name__in=(
                "Entwurf: Gleichheitszeichen diagnostizieren",
                "Entwurf: Bruchrechnung vertiefen",
            ),
            eigentuemerin=ausbilderin,
        ).first()
        neu = entwurf is None
        if entwurf is None:
            entwurf = Training.objects.create(
                name="Entwurf: Gleichheitszeichen diagnostizieren",
                eigentuemerin=ausbilderin,
            )
        elif entwurf.name != "Entwurf: Gleichheitszeichen diagnostizieren":
            entwurf.name = "Entwurf: Gleichheitszeichen diagnostizieren"
            entwurf.save(update_fields=["name"])
        entwurf.vignetten.set(vignetten[:1])
        if neu and vignetten:
            self.stdout.write(
                "  Training 'Entwurf: Gleichheitszeichen diagnostizieren' "
                "als Entwurf angelegt."
            )
        elif not neu:
            self.stdout.write(
                "  Training 'Entwurf: Gleichheitszeichen diagnostizieren' vorhanden."
            )

    def _zusammenfassung_ausgeben(self) -> None:
        """Nennt die Anmeldedaten für den manuellen Testlauf."""
        self.stdout.write(self.style.SUCCESS("\nEntwicklungsdaten bereit."))
        self.stdout.write(f"Passwort für alle Testkonten: {ENTWICKLUNGSPASSWORT}")
        self.stdout.write("Konten: " + ", ".join(TESTKONTEN))
        self.stdout.write(
            "Aktives Modell: fake (für echte Antworten "
            f"'{SIMULATIONSMODELL}' mit OPENAI_API_KEY aktivieren)."
        )

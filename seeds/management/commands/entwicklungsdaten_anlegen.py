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

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files import File
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
# Eingecheckte Beispielabbildungen. Sie liegen ausserhalb von ``media/`` und
# werden beim Anlegen in das ``ImageField`` kopiert, damit die Demovignetten
# echte Bilder zeigen.
BEISPIELBILDER: Path = Path(__file__).resolve().parents[2] / "beispielbilder"
BILDFELDER: tuple[str, ...] = ("lernauftrag_bild", "arbeitsheft_bild")

# Die Testkonten. Der Schlüssel ist der Anmeldename, der Wert die zugewiesenen
# Rollen (Gruppennamen aus konten.navigation.KONTOROLLEN) und die Administration.
# Die Administration ist keine Rolle mehr, sondern Djangos Superuser (ADR-0033).
# "autor" trägt alles gleichzeitig, "studi" ist ein reines Teilnehmerinnenkonto.
TESTKONTEN: dict[str, tuple[list[str], bool]] = {
    "autor": (list(KONTOROLLEN), True),
    "studi": ([], False),
}

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
        "lernauftrag_text": "Setze die passende Zahl ein:\n[bild]\nBegründe deine Lösung.",
        "lernauftrag_bild": "lernauftrag.png",
        "lernauftrag_bildbeschreibung": (
            "Arbeitsblatt mit der Platzhalteraufgabe 8 + 4 = ___ + 5."
        ),
        "lernauftrag_simulationshinweise": (
            "Lukas rechnet 8 + 4 = 12 und trägt 12 in die Lücke ein. Die + 5 "
            "rechts der Lücke ignoriert er vollständig."
        ),
        "arbeitsheft_text": "8 + 4 = 12 + 5",
        "arbeitsheft_bild": "",
        "arbeitsheft_bildbeschreibung": "",
        "arbeitsheft_simulationshinweise": (
            "Wenn nach der 12 gefragt wird, erklärt Lukas, dass 8 plus 4 eben 12 ergibt."
        ),
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
        "lernauftrag_text": (
            "An einer Universität gibt es sechsmal so viele Studierende wie "
            "Professoren. Schreibe eine Gleichung mit S für die Anzahl der "
            "Studierenden und P für die Anzahl der Professoren."
        ),
        "lernauftrag_bild": "",
        "lernauftrag_bildbeschreibung": "",
        "lernauftrag_simulationshinweise": (
            "Julia vertauscht die Zuordnung und fasst S als 'Studierende' und P "
            "als 'Professoren' auf."
        ),
        "arbeitsheft_text": "",
        "arbeitsheft_bild": "arbeitsheft.png",
        "arbeitsheft_bildbeschreibung": (
            "Handschriftlicher Eintrag im Arbeitsheft mit der Gleichung 6S = P."
        ),
        "arbeitsheft_simulationshinweise": (
            "Auf Nachfragen beharrt Julia darauf, dass 6S für 'sechs Studierende' "
            "steht und P für 'ein Professor'."
        ),
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

    help = (
        "Befüllt eine Entwicklungsinstanz mit Testdaten für einen manuellen Testlauf."
    )

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
        for anmeldename, (rollen, administration) in TESTKONTEN.items():
            konto, neu = konto_modell.objects.get_or_create(username=anmeldename)
            if neu:
                konto.set_password(ENTWICKLUNGSPASSWORT)
            konto.is_superuser = administration
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
        final: Simulationskern | None = (
            Simulationskern.objects.filter(zustand=Simulationskern.Zustand.FINAL)
            .order_by("-finalisiert_am", "-pk")
            .first()
        )
        if final is not None and all(
            getattr(final, feld) == wert for feld, wert in STANDARDKERN_VORLAGEN.items()
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
        """Legt die Fake-Konfiguration an und aktiviert sie für Offline-Klicktests."""
        fake_parameter: dict[str, object] = {"skript": FAKE_SKRIPT}
        fake: ModellKonfiguration = ModellKonfiguration.objects.filter(
            sprachmodell="fake", parameter=fake_parameter
        ).first() or ModellKonfiguration.objects.create(
            sprachmodell="fake", parameter=fake_parameter
        )
        ModellKonfiguration.objects.aktivieren(fake)
        self.stdout.write("  Modell-Konfiguration 'fake' für Offline-Tests aktiv.")

    def _vignetten_anlegen(
        self, autorin: object, kern: Simulationskern
    ) -> list[Vignette]:
        """Legt je Beschreibung eine finale Vignette an, sofern noch nicht vorhanden."""
        from vignetten.models import Vignettenhistorie

        finale: list[Vignette] = []
        for beschreibung in VIGNETTEN:
            historienname: str = str(beschreibung["historienname"])
            vorhandene: Vignette | None = (
                Vignette.objects.filter(
                    historie__name=historienname, zustand=Vignette.Zustand.FINAL
                )
                .order_by("-finalisiert_am", "-pk")
                .first()
            )
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
                if feld in BILDFELDER and wert:
                    with (BEISPIELBILDER / str(wert)).open("rb") as quelle:
                        getattr(vignette, feld).save(
                            str(wert), File(quelle), save=False
                        )
                    continue
                setattr(vignette, feld, wert)
            vignette.save()
            vignette.finalisieren()
            finale.append(vignette)
            self.stdout.write(f"  Vignette '{historienname}' angelegt und finalisiert.")
        return finale

    def _trainings_anlegen(self, ausbilderin: Konto, vignetten: list[Vignette]) -> None:
        """Legt ein veröffentlichtes und ein Entwurfs-Training an."""
        veroeffentlicht: Training | None = Training.objects.filter(
            name="Diagnose-Grundlagen", eigentuemerinnen=ausbilderin
        ).first()
        ist_neu: bool = veroeffentlicht is None
        if veroeffentlicht is None:
            veroeffentlicht = Training.objects.anlegen(
                ausbilderin, name="Diagnose-Grundlagen"
            )
        veroeffentlicht.vignetten.set(vignetten)
        if ist_neu:
            veroeffentlicht.veroeffentlichen()
            self.stdout.write(
                "  Training 'Diagnose-Grundlagen' angelegt und veröffentlicht."
            )
        else:
            self.stdout.write("  Training 'Diagnose-Grundlagen' vorhanden.")

        entwurf: Training | None = Training.objects.filter(
            name__in=(
                "Entwurf: Gleichheitszeichen diagnostizieren",
                "Entwurf: Bruchrechnung vertiefen",
            ),
            eigentuemerinnen=ausbilderin,
        ).first()
        ist_neu = entwurf is None
        if entwurf is None:
            entwurf = Training.objects.anlegen(
                ausbilderin,
                name="Entwurf: Gleichheitszeichen diagnostizieren",
            )
        elif entwurf.name != "Entwurf: Gleichheitszeichen diagnostizieren":
            entwurf.name = "Entwurf: Gleichheitszeichen diagnostizieren"
            entwurf.save(update_fields=["name"])
        entwurf.vignetten.set(vignetten[:1])
        if ist_neu and vignetten:
            self.stdout.write(
                "  Training 'Entwurf: Gleichheitszeichen diagnostizieren' "
                "als Entwurf angelegt."
            )
        elif not ist_neu:
            self.stdout.write(
                "  Training 'Entwurf: Gleichheitszeichen diagnostizieren' vorhanden."
            )

    def _zusammenfassung_ausgeben(self) -> None:
        """Nennt die Anmeldedaten für den manuellen Testlauf."""
        self.stdout.write(self.style.SUCCESS("\nEntwicklungsdaten bereit."))
        self.stdout.write(f"Passwort für alle Testkonten: {ENTWICKLUNGSPASSWORT}")
        self.stdout.write("Konten: " + ", ".join(TESTKONTEN))
        self.stdout.write(
            "Aktives Modell: fake (für echte Antworten eine Konfiguration mit "
            "Anbieter und Token anlegen und aktivieren)."
        )

"""Richtet eine Produktivinstanz für einen Autor:innen-Workshop ein.

Anders als ``entwicklungsdaten_anlegen`` läuft dieses Command bewusst auch mit
``DEBUG=False``: Es legt keine Testdaten an, sondern genau das Minimum, das
Workshop-Teilnehmer:innen zum Anlegen, Bearbeiten und Proben von Vignetten
brauchen — Konten mit ausschließlich der Autorenrolle, einen finalen
Simulationskern und eine aktive Modell-Konfiguration.

Ein Konto ist bewusst mehrfach gleichzeitig anmeldbar: Der Probelauf lebt in der
Django-Session, also je Browser, während die Vignetten des Kontos allen seinen
Anmeldungen gemeinsam gehören.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils.crypto import get_random_string

from konten.models import Konto
from konten.navigation import AUTORIN_GRUPPE
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.standardkern import STANDARDKERN_VORLAGEN


# Das Sprachmodell des Workshops. Ohne eigene Parameter gelten die Standardwerte
# des Anbieters.
SIMULATIONSMODELL: str = "openai/gpt-4o"

# Zeichenvorrat ohne verwechselbare Zeichen (kein l, I, 1, O, 0): Die Passwörter
# werden im Workshop von Zetteln abgetippt.
PASSWORTZEICHEN: str = "abcdefghjkmnpqrstuvwxyzACDEFGHJKLMNPQRSTUVWXYZ23456789"
PASSWORTLAENGE: int = 10


class Command(BaseCommand):
    """Legt idempotent Autorenkonten, Kern und Modell-Konfiguration an."""

    help = "Richtet eine Instanz für einen Autor:innen-Workshop ein."

    def add_arguments(self, parser: CommandParser) -> None:
        """Erlaubt Anzahl, gemeinsames Passwort und das Neusetzen der Passwörter."""

        parser.add_argument(
            "--anzahl",
            type=int,
            default=10,
            help="Zahl der Workshop-Konten (Standard: 10).",
        )
        parser.add_argument(
            "--praefix",
            default="workshop",
            help="Namenspräfix der Konten (Standard: workshop).",
        )
        parser.add_argument(
            "--passwort",
            default=None,
            help="Gemeinsames Passwort statt eines zufälligen je Konto.",
        )
        parser.add_argument(
            "--passwoerter-neu",
            action="store_true",
            help="Setzt auch bei vorhandenen Konten ein neues Passwort.",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Führt die Einrichtung in einer Transaktion aus."""

        with transaction.atomic():
            self._kern_sicherstellen()
            self._modell_konfiguration_aktivieren()
            konten: list[tuple[str, str]] = self._konten_anlegen(
                anzahl=int(options["anzahl"]),
                praefix=str(options["praefix"]),
                passwort=options["passwort"],
                passwoerter_neu=bool(options["passwoerter_neu"]),
            )

        self._zusammenfassung_ausgeben(konten)

    def _kern_sicherstellen(self) -> None:
        """Legt den finalen Standardkern an, falls die Instanz noch keinen hat."""

        if Simulationskern.objects.filter(
            zustand=Simulationskern.Zustand.FINAL
        ).exists():
            self.stdout.write("  Simulationskern vorhanden.")
            return

        kern: Simulationskern = Simulationskern.objects.anlegen(
            **STANDARDKERN_VORLAGEN
        )
        kern.finalisieren()
        self.stdout.write("  Simulationskern angelegt und finalisiert.")

    def _modell_konfiguration_aktivieren(self) -> None:
        """Stellt die Konfiguration des Workshop-Modells bereit und aktiviert sie."""

        konfiguration: ModellKonfiguration | None = ModellKonfiguration.objects.filter(
            sprachmodell=SIMULATIONSMODELL, parameter={}
        ).first()
        if konfiguration is None:
            konfiguration = ModellKonfiguration.objects.create(
                sprachmodell=SIMULATIONSMODELL, parameter={}
            )
        ModellKonfiguration.objects.aktivieren(konfiguration)
        self.stdout.write(f"  Modell-Konfiguration '{SIMULATIONSMODELL}' aktiv.")

    def _konten_anlegen(
        self,
        *,
        anzahl: int,
        praefix: str,
        passwort: str | None,
        passwoerter_neu: bool,
    ) -> list[tuple[str, str]]:
        """Legt die Konten an und gibt je Konto sein nutzbares Passwort zurück."""

        autorinnen: Group = Group.objects.get(name=AUTORIN_GRUPPE)
        konten: list[tuple[str, str]] = []
        for nummer in range(1, anzahl + 1):
            anmeldename: str = f"{praefix}{nummer:02d}"
            konto: Konto
            neu: bool
            konto, neu = get_user_model().objects.get_or_create(username=anmeldename)
            if neu or passwoerter_neu:
                gesetztes: str = passwort or get_random_string(
                    PASSWORTLAENGE, PASSWORTZEICHEN
                )
                konto.set_password(gesetztes)
                konto.save(update_fields=["password"])
            else:
                gesetztes = "(unverändert)"
            konto.groups.set([autorinnen])
            konten.append((anmeldename, gesetztes))
        return konten

    def _zusammenfassung_ausgeben(self, konten: list[tuple[str, str]]) -> None:
        """Gibt die Anmeldedaten aus — die einzige Stelle, an der sie lesbar sind."""

        self.stdout.write(self.style.SUCCESS("\nWorkshop-Instanz bereit."))
        self.stdout.write("Konto        Passwort")
        for anmeldename, passwort in konten:
            self.stdout.write(f"{anmeldename:<12} {passwort}")
        self.stdout.write(
            "\nJedes Konto trägt ausschließlich die Rolle "
            f"'{AUTORIN_GRUPPE}' und ist mehrfach gleichzeitig anmeldbar."
        )

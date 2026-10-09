"""Gemeinsamer Aufbau der Tests über die öffentlichen Manager- und Lebenszyklusmethoden.

Aufgenommen ist nur, was in mindestens zwei Apps gebraucht wird.
"""

from django.contrib.auth.models import Group

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from vignetten.models import Vignette


def konto_mit_rollen(username: str, *rollen: str, is_superuser: bool = False) -> Konto:
    """Legt ein Konto mit den übergebenen Fachrollen an, auf Wunsch als Admin.

    Die Rollen-Gruppen legt die Migration an; ein unbekannter Name scheitert
    deshalb, statt eine wirkungslose Gruppe zu erzeugen.
    """

    angelegt: Konto = Konto.objects.create_user(
        username=username, is_superuser=is_superuser
    )
    for rolle in rollen:
        angelegt.groups.add(Group.objects.get(name=rolle))
    return angelegt


def aktive_modell_konfiguration(verwendung: Verwendung) -> ModellKonfiguration:
    """Legt eine Konfiguration des Fake-Anbieters an und aktiviert sie."""

    return ModellKonfiguration.objects.aktivieren(
        ModellKonfiguration.objects.create(bezeichnung="Test", sprachmodell="fake"),
        verwendung,
    )


def finaler_kern() -> Simulationskern:
    """Liefert den finalen Simulationskern und legt ihn beim ersten Aufruf an."""

    vorhandener: Simulationskern | None = Simulationskern.objects.filter(
        zustand=Simulationskern.Zustand.FINAL
    ).first()
    if vorhandener is not None:
        return vorhandener
    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    return kern


def vignetten_entwurf(konto: Konto) -> Vignette:
    """Legt einen Vignetten-Entwurf im Bestand des Kontos an."""

    finaler_kern()  # Vignette.objects.anlegen pinnt den aktuellen finalen Kern.
    return Vignette.objects.anlegen(konto)


def finale_vignette(konto: Konto, *, name: str = "", **felder: object) -> Vignette:
    """Legt eine finale Vignetten-Fassung mit vollständigen Pflichtfeldern an.

    Übergebene Felder ersetzen die Vorgaben; ein unbekanntes Feld scheitert,
    statt still ignoriert zu werden. Ein Name geht an die Historie: So
    lassen sich mehrere Fassungen im gerenderten Text auseinanderhalten.
    """

    vignette: Vignette = vignetten_entwurf(konto)
    if name:
        vignette.historie.name = name
        vignette.historie.save(update_fields=["name"])
    werte: dict[str, object] = {
        "fehlermuster_beschreibung": "Zähler und Nenner addieren",
        "lernauftrag_text": "Addiere **die** Brüche.\n[Tipp](https://example.org)",
        "arbeitsheft_bildbeschreibung": "Falsche Bruchrechnung",
        "arbeitsheft_text": "1/2 + 1/3\n\\= 2/5",
        "schuelerin_name": "Lea",
        "schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "lehrperson_name": "Ada",
        "lehrperson_geschlecht": Vignette.Geschlecht.WEIBLICH,
        "fach": "Mathematik",
        "thema": "Bruchrechnung",
        "klassenstufe": "6",
        "budget_typ": Vignette.BudgetTyp.SCHRITTE,
        "budget_wert": 3,
    } | felder
    for feld, wert in werte.items():
        if not hasattr(vignette, feld):
            raise TypeError(f"Vignette hat kein Feld {feld!r}.")
        setattr(vignette, feld, wert)
    vignette.save()
    vignette.finalisieren()
    return vignette

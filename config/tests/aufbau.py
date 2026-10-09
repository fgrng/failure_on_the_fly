"""Gemeinsamer Aufbau der Tests über die öffentlichen Manager- und Lebenszyklusmethoden.

Aufgenommen ist nur, was in mindestens zwei Apps gebraucht wird.
"""

from django.contrib.auth.models import Group

from konten.models import Konto
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from vignetten.models import Vignette


def konto(username: str, *rollen: str) -> Konto:
    """Legt ein Konto mit den übergebenen Fachrollen an."""

    angelegt: Konto = Konto.objects.create_user(username=username)
    for rolle in rollen:
        angelegt.groups.add(Group.objects.get_or_create(name=rolle)[0])
    return angelegt


def aktive_modell_konfiguration(
    verwendung: Verwendung = Verwendung.SCHUELERIN,
) -> ModellKonfiguration:
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

    Übergebene Felder ersetzen die Vorgaben. Ein Name geht an die Historie: So
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
        setattr(vignette, feld, wert)
    vignette.save()
    vignette.finalisieren()
    return vignette

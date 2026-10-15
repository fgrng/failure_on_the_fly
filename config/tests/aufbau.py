"""Gemeinsamer Aufbau der Tests über die öffentlichen Manager- und Lebenszyklusmethoden.

Aufgenommen ist nur, was in mindestens zwei Apps gebraucht wird.
"""

from django.contrib.auth.models import Group

from konten.models import Konto
from simulation.models import (
    Anbieter,
    ModellKonfiguration,
    Simulationskern,
    TranskriptionsKonfiguration,
    Verwendung,
    ZeroRetentionFeldgruppe,
)
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


def aktive_modell_konfiguration(
    verwendung: Verwendung, skript: list[dict[str, str]] | None = None
) -> ModellKonfiguration:
    """Legt eine Konfiguration des Fake-Anbieters an und aktiviert sie.

    Ein Skript gibt dem Fake-Anbieter seine Antworten vor.
    """

    return ModellKonfiguration.objects.aktivieren(
        ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            parameter={"skript": skript} if skript is not None else {},
        ),
        verwendung,
    )


def erklaerte[K: ZeroRetentionFeldgruppe](konfiguration: K) -> K:
    """Gibt an der Konfiguration eine Zero-Retention-Erklärung ab.

    Erklärt wird im Namen eines eigenen Administrationskontos, damit die
    Erklärung keinem Konto des Tests in die Quere kommt.
    """

    konto: Konto
    konto, _ = Konto.objects.get_or_create(
        username="zero-retention-erklaerende", defaults={"is_superuser": True}
    )
    konfiguration.zero_retention_erklaeren("AVV mit dem Anbieter vom 01.10.2026", konto)
    return konfiguration


def transkriptions_fassung() -> TranskriptionsKonfiguration:
    """Legt eine Transkriptions-Fassung mit echtem Anbieter an, ohne Erklärung.

    Sie ist nicht aktiv; ihr Tor bleibt zu, bis sie erklärt ist.
    """

    return TranskriptionsKonfiguration.objects.create(
        anbieter=Anbieter.OPENROUTER,
        anbieter_token="sk-or-testtoken",
        transkriptionsmodell="whisper-large-v3",
    )


def erklaerte_aktive_transkription() -> TranskriptionsKonfiguration:
    """Legt eine erklärte Transkriptions-Fassung mit echtem Anbieter an und aktiviert sie.

    Damit ist das Tor der Transkription offen. Den Adapter speisen Tests
    weiter über die Naht `anbieter_bilden` als `FakeTranskription` ein.
    """

    return TranskriptionsKonfiguration.objects.aktivieren(
        erklaerte(transkriptions_fassung())
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

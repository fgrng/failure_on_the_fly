"""Aufbau der Evals-Tests: finaler Katalog und drei fortlesende Fake-Konfigurationen."""

from collections.abc import Sequence

from simulation.models import (
    Evalinput,
    Evalkatalog,
    Inputschritt,
    ModellKonfiguration,
    Verwendung,
)

LEHRPERSON_VORLAGE: str = "Sprich mit $schuelerin_name nach $inputstrategie."
BEWERTER_VORLAGE: str = (
    "Prüfe $kriterium für $schuelerin_name mit $fehlermuster_beschreibung "
    "am Verlauf $verlauf."
)


def antworten(anzahl: int) -> list[dict[str, str]]:
    """Liefert so viele nummerierte Schüler:innen-Antworten."""

    return [
        {"denkspur": f"Denkspur {nummer}", "aeusserung": f"Antwort {nummer}"}
        for nummer in range(1, anzahl + 1)
    ]


def urteile(*erfuellt: bool) -> list[dict[str, object]]:
    """Liefert je Wahrheitswert eine Bewerter-Ausgabe."""

    return [
        {"begruendung": f"Begründung {nummer}", "erfuellt": wert}
        for nummer, wert in enumerate(erfuellt, 1)
    ]


def fake_aktivieren(
    verwendung: Verwendung, skript: Sequence[dict[str, object]] = ()
) -> ModellKonfiguration:
    """Aktiviert eine Fake-Konfiguration, die ihr Skript im Evallauf fortliest."""

    return ModellKonfiguration.objects.aktivieren(
        ModellKonfiguration.objects.create(
            bezeichnung=f"Fake {verwendung.label}",
            sprachmodell="fake",
            parameter={"skript": list(skript), "skript_fortlesen": True},
        ),
        verwendung,
    )


def drei_fakes(
    schuelerin: Sequence[dict[str, object]] = (),
    bewerter: Sequence[dict[str, object]] = (),
    lehrperson: Sequence[dict[str, object]] = (),
) -> None:
    """Belegt alle drei Verwendungen mit fortlesenden Fake-Konfigurationen."""

    fake_aktivieren(Verwendung.SCHUELERIN, schuelerin)
    fake_aktivieren(Verwendung.LEHRPERSON, lehrperson)
    fake_aktivieren(Verwendung.BEWERTER, bewerter)


def finaler_katalog(
    *,
    k: int = 3,
    schritte: Sequence[str] = ("Wie hast du gerechnet?", "Warum so?"),
    gelenkt: Sequence[str] = (),
    evalkriterien: Sequence[str] = ("Muster gezeigt",),
    uebergreifende: Sequence[str] = ("Rollentreue",),
) -> Evalkatalog:
    """Finalisiert einen Katalog mit einem Eval „Muster“ und einem Evalinput.

    Die festen Schritte stehen vorn, die gelenkten dahinter.
    """

    katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    katalog.k = k
    katalog.lehrperson_vorlage = LEHRPERSON_VORLAGE
    katalog.bewerter_vorlage = BEWERTER_VORLAGE
    katalog.save()
    for text in uebergreifende:
        katalog.kriterium_anlegen(text)
    eval_ = katalog.eval_anlegen("Muster")
    for text in evalkriterien:
        eval_.kriterium_anlegen(text)
    evalinput = Evalinput.anhaengen(eval_)
    for text in schritte:
        evalinput.schritt_anlegen(text=text)
    for text in gelenkt:
        evalinput.schritt_anlegen(Inputschritt.Art.GELENKT, text)
    katalog.finalisieren()
    return katalog

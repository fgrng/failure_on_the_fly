"""Baut Evalkataloge, die sich finalisieren lassen, für die Tests des Katalogs."""

from simulation.models import (
    Evalkatalog,
    Evalkriterium,
    Inputschritt,
    UebergreifendesKriterium,
)

LEHRPERSON_VORLAGE: str = "Sprich mit $schuelerin_name nach $inputstrategie."
BEWERTER_VORLAGE: str = "Prüfe $kriterium am Verlauf $verlauf."
FUELLTEXT: str = "Ergänzt"


def vervollstaendigen(katalog: Evalkatalog) -> Evalkatalog:
    """Ergänzt, was dem Entwurf zum Finalisieren fehlt; Vorhandenes bleibt.

    Leere Vorlagen und Texte erhalten Fülltext, ein Katalog ohne Eval ein Eval
    „Ergänzt“, ein Eval ohne Kriterium oder Evalinput je eines.
    """
    katalog.lehrperson_vorlage = katalog.lehrperson_vorlage or LEHRPERSON_VORLAGE
    katalog.bewerter_vorlage = katalog.bewerter_vorlage or BEWERTER_VORLAGE
    katalog.save()
    if not katalog.evals.exists():
        katalog.eval_anlegen(FUELLTEXT)
    for eval_ in katalog.evals.all():
        if not eval_.kriterien.exists():
            eval_.kriterium_anlegen(FUELLTEXT)
        if not eval_.inputs.exists():
            eval_.input_anlegen()
        for evalinput in eval_.inputs.all():
            if not evalinput.schritte.exists():
                evalinput.schritt_anlegen(text=FUELLTEXT)
    for teile in (
        UebergreifendesKriterium.objects.filter(katalog=katalog),
        Evalkriterium.objects.filter(eval__katalog=katalog),
        Inputschritt.objects.filter(evalinput__eval__katalog=katalog),
    ):
        for teil in teile.filter(text=""):
            teil.text = FUELLTEXT
            teil.save(update_fields=["text"])
    return katalog


def vollstaendiger_katalog() -> Evalkatalog:
    """Legt den ersten Katalog an, vollständig genug zum Finalisieren."""
    return vervollstaendigen(Evalkatalog.objects.anlegen())

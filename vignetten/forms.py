"""Formulare des Vignetten-Editors."""

import random

from django.forms import ModelForm

from .models import Vignette


_SCHUELERINNEN: tuple[tuple[str, Vignette.Geschlecht], ...] = (
    ("Mia", Vignette.Geschlecht.WEIBLICH),
    ("Noah", Vignette.Geschlecht.MAENNLICH),
)
_LEHRPERSONEN: tuple[tuple[str, Vignette.Geschlecht], ...] = (
    ("Weber", Vignette.Geschlecht.WEIBLICH),
    ("Koch", Vignette.Geschlecht.MAENNLICH),
)


class VignetteForm(ModelForm):
    """Die bearbeitbaren Inhaltsfelder einer Vignette."""

    class Meta:
        """Schließt Lebenszyklus- und Kernfelder vom Anlegeformular aus."""

        model: type[Vignette] = Vignette
        fields: list[str] = [
            "fehlermuster_beschreibung",
            "lernauftrag",
            "arbeitsheft_beschreibung",
            "arbeitsheft_text",
            "schuelerin_name",
            "schuelerin_geschlecht",
            "lehrperson_name",
            "lehrperson_geschlecht",
            "fach",
            "thema",
            "klassenstufe",
            "referenzdiagnose",
            "budget_typ",
            "budget_wert",
        ]


def zufaellige_akteure() -> dict[str, str]:
    """Liefert überschreibbare Startwerte für die beiden Akteure."""
    schuelerin_name, schuelerin_geschlecht = random.choice(_SCHUELERINNEN)
    lehrperson_name, lehrperson_geschlecht = random.choice(_LEHRPERSONEN)
    return {
        "schuelerin_name": schuelerin_name,
        "schuelerin_geschlecht": schuelerin_geschlecht,
        "lehrperson_name": lehrperson_name,
        "lehrperson_geschlecht": lehrperson_geschlecht,
    }

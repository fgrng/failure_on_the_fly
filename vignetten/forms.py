"""Formulare des Vignetten-Editors."""

import random

from django.forms import Form, ModelForm

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
            "arbeitsheft_bild",
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
        labels: dict[str, str] = {
            "fehlermuster_beschreibung": "Fehlermuster Beschreibung",
            "arbeitsheft_beschreibung": "Arbeitsheft Beschreibung",
            "arbeitsheft_text": "Arbeitsheft Text",
            "arbeitsheft_bild": "Arbeitsheft Bild",
            "schuelerin_name": "Schüler:in Name",
            "schuelerin_geschlecht": "Schüler:in Geschlecht",
            "lehrperson_name": "Lehrperson Name",
            "lehrperson_geschlecht": "Lehrperson Geschlecht",
            "referenzdiagnose": "Referenzdiagnose (optional)",
            "budget_typ": "Budget Typ",
            "budget_wert": "Budget Wert",
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Ergänzt die beiden Unterrichtskontext-Felder um Alpine-Hooks."""
        super().__init__(*args, **kwargs)
        for feldname in ("fach", "thema"):
            self.fields[feldname].widget.attrs.update(
                {
                    "x-ref": "eingabe",
                    "@input": "suche($event.target.value)",
                    "@focus": "suche($event.target.value)",
                    "@keydown.escape": "vorschlaege = []",
                    "autocomplete": "off",
                }
            )


class FinalisierenForm(Form):
    """Trägt die nicht feldgebundenen Fehler der Finalisieren-Aktion."""


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

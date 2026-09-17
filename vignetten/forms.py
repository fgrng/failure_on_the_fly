"""Formulare des Vignetten-Editors."""

from django.forms import Form, ModelForm

from .models import Vignette


class VignetteForm(ModelForm):
    """Die bearbeitbaren Inhaltsfelder einer Vignette."""

    class Meta:
        """Schließt Lebenszyklus- und Kernfelder vom Anlegeformular aus."""

        model: type[Vignette] = Vignette
        fields: list[str] = [
            "fehlermuster_beschreibung",
            "lernauftrag_text",
            "lernauftrag_bild",
            "lernauftrag_bildbeschreibung",
            "lernauftrag_simulationshinweise",
            "arbeitsheft_text",
            "arbeitsheft_bild",
            "arbeitsheft_bildbeschreibung",
            "arbeitsheft_simulationshinweise",
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
            "lernauftrag_text": "Lernauftrag Text",
            "lernauftrag_bild": "Lernauftrag Bild",
            "lernauftrag_bildbeschreibung": "Lernauftrag Bildbeschreibung",
            "lernauftrag_simulationshinweise": "Lernauftrag Simulationshinweise (optional)",
            "arbeitsheft_text": "Arbeitsheft Text",
            "arbeitsheft_bild": "Arbeitsheft Bild",
            "arbeitsheft_bildbeschreibung": "Arbeitsheft Bildbeschreibung",
            "arbeitsheft_simulationshinweise": "Arbeitsheft Simulationshinweise (optional)",
            "schuelerin_name": "Schüler:in Vorname",
            "schuelerin_geschlecht": "Schüler:in Geschlecht",
            "lehrperson_name": "Lehrperson Nachname (Frau/Herr …)",
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

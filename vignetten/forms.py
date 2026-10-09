"""Formulare des Vignetten-Editors."""

from typing import Any

from django.forms import ClearableFileInput, ModelForm

from .models import FELDBESCHRIFTUNGEN, Vignette

_BILDTEILE: tuple[str, ...] = ("lernauftrag", "arbeitsheft")


class Bildeingabe(ClearableFileInput):
    """Rendert nur das Dateifeld; Vorschau und Entfernen zeichnet die Bildkarte.

    Die Clear-Logik von ClearableFileInput (``<name>-clear``) bleibt erhalten.
    """

    template_name: str = "django/forms/widgets/file.html"


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
        labels: dict[str, str] = FELDBESCHRIFTUNGEN
        widgets: dict[str, type[Bildeingabe]] = {
            f"{teil}_bild": Bildeingabe for teil in _BILDTEILE
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Ergänzt Unterrichtskontext- und Bildfelder um Alpine-Hooks."""
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
        for teil in _BILDTEILE:
            self.fields[f"{teil}_bild"].widget.attrs.update(
                {
                    "accept": "image/*",
                    "class": "bildkarte__eingabe",
                    "x-ref": "eingabe",
                    "@change": "gewaehlt($el)",
                    "aria-describedby": f"id_{teil}_bild_status",
                }
            )
            self.fields[f"{teil}_bildbeschreibung"].widget.attrs.update(
                {
                    "x-model": "beschreibung",
                    ":readonly": "wirdEntfernt",
                }
            )

    def clean(self) -> dict[str, Any]:
        """Leert mit einem entfernten Bild auch dessen Bildbeschreibung (#288)."""
        cleaned_data: dict[str, Any] = super().clean()
        for teil in _BILDTEILE:
            if cleaned_data.get(f"{teil}_bild") is False:
                cleaned_data[f"{teil}_bildbeschreibung"] = ""
        return cleaned_data

    @property
    def bildkarten(self) -> dict[str, dict[str, Any]]:
        """Liefert je Aufgabenkontextteil, was die Bildkarte zum Zeichnen braucht."""
        karten: dict[str, dict[str, Any]] = {}
        for teil in _BILDTEILE:
            bild = self[f"{teil}_bild"]
            # Ein ungültiges Formular kann die hochgeladene Datei nicht wieder
            # anzeigen; die Karte nennt sie deshalb, damit sie neu gewählt wird.
            # War die Datei selbst kein Bild, nennt die Karte sie als Fehler.
            datei = (
                self.files.get(bild.html_name)
                if self.is_bound and self.errors
                else None
            )
            dateiname: str = datei.name if datei else ""
            fehlerhafte_datei: str = dateiname if bild.errors else ""
            verlorene_datei: str = "" if bild.errors else dateiname
            gespeichert_url: str = bild.initial.url if bild.initial else ""
            entfernen: bool = f"{bild.html_name}-clear" in self.data
            if bild.errors:
                zustand: str = "fehler"
            elif verlorene_datei:
                zustand = "verloren"
            elif entfernen:
                zustand = "entfernen"
            elif gespeichert_url:
                zustand = "gespeichert"
            else:
                zustand = "leer"
            karten[teil] = {
                "bild": bild,
                "beschreibung": self[f"{teil}_bildbeschreibung"],
                "text_id": self[f"{teil}_text"].id_for_label,
                "zustand": zustand,
                "gespeichert_url": gespeichert_url,
                "fehlerhafte_datei": fehlerhafte_datei,
                "verlorene_datei": verlorene_datei,
                "entfernen": entfernen,
            }
        return karten

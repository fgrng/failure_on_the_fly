"""Formulare der Simulationskern-Verwaltung."""

from django.forms import ModelForm, PasswordInput

from .models import (
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_RAHMEN,
    Simulationskern,
    TranskriptionsKonfiguration,
)

_RAHMEN_FELDER: dict[str, str] = {
    "rahmenhandlung_einleitung": "Hospitationseinleitung",
    "rahmenhandlung_gespraechseinleitung": "Gesprächseinleitung",
    "rahmenhandlung_debrief": "Debrief",
}
_PROMPT_FELDER: dict[str, str] = {
    "system_prompt_vorlage": "System-Prompt-Vorlage",
    "user_prompt_vorlage": "User-Prompt-Vorlage",
}


def _platzhalter_hinweis(
    vertrag: frozenset[str],
    umgebungsplatzhalter: frozenset[str] = frozenset(),
) -> str:
    """Erklärt einen Platzhaltervertrag unmittelbar am zugehörigen Feld."""
    erlaubte: str = ", ".join(f"${platzhalter}" for platzhalter in sorted(vertrag))
    hinweis: str = f"Erlaubte Platzhalter: {erlaubte}."
    if umgebungsplatzhalter:
        umgebungen: str = ", ".join(
            f"${platzhalter}" for platzhalter in sorted(umgebungsplatzhalter)
        )
        hinweis += f" Erzeugen eine benannte Umgebung: {umgebungen}."
    return hinweis


class SimulationskernForm(ModelForm):
    """Bearbeitbare Vorlagen eines Kern-Entwurfs."""

    class Meta:
        """Beschränkt das Formular auf die Inhaltsfelder einer Fassung."""

        model: type[Simulationskern] = Simulationskern
        fields: list[str] = list(_RAHMEN_FELDER) + list(_PROMPT_FELDER)

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Leitet die sichtbaren Vertragsbeschreibungen aus den Prüfkonstanten ab."""
        super().__init__(*args, **kwargs)
        self._beschriften(_RAHMEN_FELDER, _platzhalter_hinweis(VERTRAG_RAHMEN))
        self._beschriften(
            _PROMPT_FELDER,
            _platzhalter_hinweis(VERTRAG_PROMPT, PROMPT_PLATZHALTER_MIT_UMGEBUNG),
        )

    def _beschriften(self, felder: dict[str, str], hinweis: str) -> None:
        # Versieht die angegebenen Felder mit Bezeichnung und Vertragshinweis.

        for feldname, bezeichnung in felder.items():
            self.fields[feldname].label = bezeichnung
            self.fields[feldname].help_text = hinweis


class TranskriptionsKonfigurationForm(ModelForm):
    """Der eine, veränderliche Anbieterzugang der Transkription."""

    class Meta:
        """Führt alle fünf Felder; das Token gibt das Formular nie zurück."""

        model: type[TranskriptionsKonfiguration] = TranskriptionsKonfiguration
        fields: list[str] = [
            "anbieter",
            "anbieter_basis_url",
            "anbieter_token",
            "transkriptionsmodell",
            "sprache",
        ]
        labels: dict[str, str] = {
            "anbieter": "Anbieter",
            "anbieter_basis_url": "Basis-URL",
            "anbieter_token": "Zugangstoken",
            "transkriptionsmodell": "Transkriptionsmodell",
            "sprache": "Sprache",
        }
        help_texts: dict[str, str] = {
            "anbieter_basis_url": "Bei Infomaniak die Wurzel des eigenen Kontos.",
            "anbieter_token": "Leer lassen behält das hinterlegte Token.",
            "sprache": "Sprachkürzel, damit die Transkription nicht raten muss.",
        }
        widgets: dict[str, PasswordInput] = {
            "anbieter_token": PasswordInput(render_value=False),
        }

    def clean_anbieter_token(self) -> str:
        """Liest eine leere Eingabe als »unverändert«, nicht als »löschen«."""
        # Das Feld gibt den gesetzten Wert nie zurück; eine leere Eingabe wäre
        # sonst bei jeder anderen Änderung ein versehentlicher Tokenverlust.
        return self.cleaned_data["anbieter_token"] or self.instance.anbieter_token

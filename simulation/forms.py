"""Formulare der Simulationskern-Verwaltung."""

from django.forms import ModelForm

from .models import (
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_RAHMEN,
    Simulationskern,
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

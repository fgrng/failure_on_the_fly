"""Formulare der Simulationskern-Verwaltung."""

from django.forms import ModelForm

from . import models

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
        """Beschränkt das Formular auf die fünf Inhaltsfelder."""

        model: type[models.Simulationskern] = models.Simulationskern
        fields: list[str] = list(_RAHMEN_FELDER) + list(_PROMPT_FELDER)

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Leitet die sichtbaren Vertragsbeschreibungen aus den Prüfkonstanten ab."""
        super().__init__(*args, **kwargs)
        for felder, hinweis in (
            (_RAHMEN_FELDER, _platzhalter_hinweis(models.VERTRAG_RAHMEN)),
            (
                _PROMPT_FELDER,
                _platzhalter_hinweis(
                    models.VERTRAG_PROMPT,
                    models.PROMPT_PLATZHALTER_MIT_UMGEBUNG,
                ),
            ),
        ):
            for feldname, bezeichnung in felder.items():
                self.fields[feldname].label = bezeichnung
                self.fields[feldname].help_text = hinweis

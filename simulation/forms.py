"""Formulare der Simulation: Kern-Entwurf, Modell- und Transkriptions-Konfiguration."""

from django.forms import ModelForm, PasswordInput

from .models import (
    ANBIETER_PROFIL,
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_RAHMEN,
    Anbieter,
    ModellKonfiguration,
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


def _stellschrauben_hinweis() -> str:
    """Erklärt die anbieterabhängige Allowlist unmittelbar am Parameter-Feld."""
    echte: str = ", ".join(sorted(ANBIETER_PROFIL[Anbieter.OPENROUTER].stellschrauben))
    fake: str = ", ".join(sorted(ANBIETER_PROFIL[Anbieter.FAKE].stellschrauben))
    return f"Erlaubt sind bei echten Anbietern: {echte}. Beim Anbieter »fake«: {fake}."


class ModellKonfigurationForm(ModelForm):
    """Die einzige Schreibgeste an einer append-only Modell-Konfiguration."""

    class Meta:
        """Beschränkt das Formular auf die Felder einer neuen Fassung."""

        model: type[ModellKonfiguration] = ModellKonfiguration
        fields: list[str] = [
            "anbieter",
            "sprachmodell",
            "anbieter_basis_url",
            "anbieter_token",
            "parameter",
        ]
        labels: dict[str, str] = {
            "anbieter": "Anbieter",
            "sprachmodell": "Sprachmodell",
            "anbieter_basis_url": "Basis-URL",
            "anbieter_token": "Token",
            "parameter": "Parameter",
        }
        help_texts: dict[str, str] = {
            "sprachmodell": "Mit dem Präfix des gewählten Anbieters.",
            "anbieter_basis_url": "Die Endpunktwurzel des Anbieters.",
            "anbieter_token": "Wird gespeichert, aber nie wieder angezeigt.",
        }
        # Write-only: Der gesetzte Wert wird nie zurückgerendert — bei einem
        # Formularfehler ebenso wenig wie nach dem Speichern.
        widgets: dict[str, PasswordInput] = {
            "anbieter_token": PasswordInput(render_value=False),
        }
        error_messages: dict[str, dict[str, str]] = {
            "parameter": {"invalid": "Bitte gültiges JSON eintragen."},
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Leitet den sichtbaren Allowlist-Hinweis aus den Prüfkonstanten ab."""
        super().__init__(*args, **kwargs)
        self.fields["parameter"].help_text = _stellschrauben_hinweis()

    def clean_parameter(self) -> dict[str, object]:
        """Liest ein leer gelassenes Feld als leeren Beutel, nicht als Nichts."""
        parameter: dict[str, object] | None = self.cleaned_data["parameter"]
        return {} if parameter is None else parameter


class TranskriptionsKonfigurationForm(ModelForm):
    """Der eine, veränderliche Anbieterzugang der Transkription."""

    class Meta:
        """Führt die Felder der Konfiguration; das Token gibt sie nie zurück."""

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
            "anbieter_basis_url": (
                "Bei Infomaniak die Wurzel des eigenen Kontos; bei OpenRouter "
                "leer lassen für die Vorgabe https://openrouter.ai/api/v1."
            ),
            "anbieter_token": "Leer lassen behält das hinterlegte Token.",
            "sprache": "Sprachkürzel, damit die Transkription nicht raten muss.",
        }
        widgets: dict[str, PasswordInput] = {
            "anbieter_token": PasswordInput(render_value=False),
        }

    def clean_anbieter_token(self) -> str:
        """Liest eine leere Eingabe als »unverändert«, nicht als »löschen«.

        Das Feld zeigt den gesetzten Wert nie an; ohne diese Lesart wäre jede
        Änderung an einem anderen Feld ein versehentlicher Tokenverlust.
        """
        return self.cleaned_data["anbieter_token"] or self.instance.anbieter_token

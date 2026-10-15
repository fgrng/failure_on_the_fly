"""Formulare der Simulation: Kern- und Evalkatalog-Entwurf, Modell- und Transkriptions-Konfiguration."""

from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError
from django.forms import (
    BooleanField,
    CharField,
    Form,
    ModelForm,
    PasswordInput,
    Textarea,
)

from konten.models import Konto

from .models import (
    ANBIETER_PROFIL,
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_RAHMEN,
    Anbieter,
    Evalkatalog,
    ModellKonfiguration,
    Simulationskern,
    TranskriptionsKonfiguration,
    ZeroRetentionFeldgruppe,
)

# Das Feld heißt an beiden Nähten gleich und wird an beiden gleich gefüllt —
# also steht an beiden derselbe Hinweis.
BASIS_URL_HINWEIS: str = (
    "Die Endpunktwurzel des Anbieters. Bei Infomaniak füllt der Ladeknopf sie; "
    "bei OpenRouter leer lassen für die Vorgabe https://openrouter.ai/api/v1."
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
        # Altfeld (ADR-0052): nur sichtbar, solange Entwurf oder Eingabe es
        # füllen. Ohne Feld lässt das Speichern die Vorlage unberührt.
        if not (
            self.instance.user_prompt_vorlage
            or self.data.get(self.add_prefix("user_prompt_vorlage"))
        ):
            del self.fields["user_prompt_vorlage"]

    def _beschriften(self, felder: dict[str, str], hinweis: str) -> None:
        # Versieht die angegebenen Felder mit Bezeichnung und Vertragshinweis.

        for feldname, bezeichnung in felder.items():
            self.fields[feldname].label = bezeichnung
            self.fields[feldname].help_text = hinweis


class EvalkatalogDurchlaufForm(ModelForm):
    """Der Knoten Durchlauf und Vorlagen eines Evalkatalog-Entwurfs."""

    class Meta:
        """Beschränkt das Formular auf *k* und die beiden Vorlagen."""

        model: type[Evalkatalog] = Evalkatalog
        fields: list[str] = ["k", "lehrperson_vorlage", "bewerter_vorlage"]


# Beide Konfigurationen tragen dieselbe Erklärung, also denselben Wortlaut.
ZERO_RETENTION_BELEG_LABEL: str = "Beleg der Zusage"
ZERO_RETENTION_BELEG_HINWEIS: str = (
    "Worauf sich die Zusage stützt, etwa „AVV mit Infomaniak vom …“ oder "
    "„OpenRouter: Modell nur über ZDR-Endpunkte, Stand …“. Zeitpunkt und Konto "
    "werden mitgeschrieben; danach ist die Erklärung nicht mehr änderbar."
)


def _beleg_feld() -> CharField:
    """Das Belegfeld der Erklärung, gleich an beiden Konfigurationen."""
    # Nicht Pflicht am Feld: Den leeren Beleg meldet die Domäne mit ihrem
    # eigenen Wortlaut, damit beide Wege dieselbe Meldung zeigen.
    return CharField(
        label=ZERO_RETENTION_BELEG_LABEL,
        help_text=ZERO_RETENTION_BELEG_HINWEIS,
        required=False,
        widget=Textarea(attrs={"rows": 3}),
    )


class ZeroRetentionFeldgruppeForm(ModelForm):
    """Die Erklärung beim Anlegen einer Fassung, für beide Konfigurationen.

    Das Häkchen ist die Erklärung selbst; der Beleg allein erklärt nichts.
    """

    zero_retention_erklaert = BooleanField(
        label="Zero-Retention-Erklärung abgeben",
        help_text=(
            "Für dieses Modell bei diesem Anbieter liegt eine Zusage vor, dass "
            "Eingaben weder gespeichert noch zum Training genutzt werden."
        ),
        required=False,
    )
    zero_retention_beleg = _beleg_feld()

    def __init__(self, *args: object, konto: Konto, **kwargs: object) -> None:
        """Merkt sich das erklärende Konto."""
        super().__init__(*args, **kwargs)
        self._konto: Konto = konto

    def clean(self) -> dict[str, object]:
        """Gibt die Erklärung mit der Fassung ab, nach den Regeln der Domäne."""
        daten: dict[str, object] = super().clean()
        beleg: str = str(daten.get("zero_retention_beleg") or "")
        # Ohne gültige Erklärung bleibt auch kein Beleg an der Fassung stehen.
        daten["zero_retention_beleg"] = ""
        if not daten.get("zero_retention_erklaert") or "anbieter" not in daten:
            return daten
        self.instance.anbieter = daten["anbieter"]
        try:
            self.instance.zero_retention_erklaeren(beleg, self._konto)
        except ValidationError as fehler:
            self.add_error(None, fehler)
            return daten
        daten["zero_retention_beleg"] = self.instance.zero_retention_beleg
        return daten


class ZeroRetentionErklaerungForm(Form):
    """Die nachträgliche Erklärung an einer bestehenden Fassung."""

    zero_retention_beleg = _beleg_feld()

    def erklaeren(self, konfiguration: ZeroRetentionFeldgruppe, konto: Konto) -> bool:
        """Gibt die Erklärung ab; scheitert sie, stehen die Gründe am Formular."""
        return _an_der_domaene(
            self,
            lambda daten: konfiguration.zero_retention_erklaeren(
                daten["zero_retention_beleg"], konto
            ),
        )


class ZeroRetentionWiderrufForm(Form):
    """Der Widerruf einer abgegebenen Erklärung, an beiden Konfigurationen."""

    # Nicht Pflicht am Feld: Den leeren Grund meldet die Domäne.
    zero_retention_widerrufsgrund = CharField(
        label="Grund des Widerrufs",
        help_text=(
            "Warum die Zusage nicht mehr gilt, etwa „Anbieter zieht die Zusage "
            "zurück“ oder „Modell hat keinen ZDR-Endpunkt mehr“. Zeitpunkt und "
            "Konto werden mitgeschrieben; der Widerruf ist endgültig."
        ),
        required=False,
        widget=Textarea(attrs={"rows": 3}),
    )

    def widerrufen(self, konfiguration: ZeroRetentionFeldgruppe, konto: Konto) -> bool:
        """Widerruft die Erklärung; scheitert es, stehen die Gründe am Formular."""
        return _an_der_domaene(
            self,
            lambda daten: konfiguration.zero_retention_widerrufen(
                daten["zero_retention_widerrufsgrund"], konto
            ),
        )


def _an_der_domaene(form: Form, aenderung: Callable[[dict[str, Any]], None]) -> bool:
    # Führt die Änderung der Domäne mit den bereinigten Daten aus; was sie
    # abweist, steht danach am Formular.
    if not form.is_valid():
        return False
    try:
        aenderung(form.cleaned_data)
    except ValidationError as fehler:
        form.add_error(None, fehler)
        return False
    return True


def _stellschrauben_hinweis() -> str:
    """Erklärt die anbieterabhängige Allowlist unmittelbar am Parameter-Feld."""
    echte: str = ", ".join(sorted(ANBIETER_PROFIL[Anbieter.OPENROUTER].stellschrauben))
    fake: str = ", ".join(sorted(ANBIETER_PROFIL[Anbieter.FAKE].stellschrauben))
    return f"Erlaubt sind bei echten Anbietern: {echte}. Beim Anbieter »fake«: {fake}."


class ModellKonfigurationForm(ZeroRetentionFeldgruppeForm):
    """Die einzige Schreibgeste an einer append-only Modell-Konfiguration."""

    class Meta:
        """Beschränkt das Formular auf die Felder einer neuen Fassung."""

        model: type[ModellKonfiguration] = ModellKonfiguration
        # Die Reihenfolge der Eingabe, nicht die des Modells: Das Token steht
        # beim Anbieter, weil der Ladeknopf der Modellliste es braucht.
        fields: list[str] = [
            "bezeichnung",
            "anbieter",
            "anbieter_token",
            "anbieter_basis_url",
            "sprachmodell",
            "parameter",
            "zero_retention_beleg",
        ]
        labels: dict[str, str] = {
            "bezeichnung": "Bezeichnung",
            "anbieter": "Anbieter",
            "anbieter_token": "Token",
            "anbieter_basis_url": "Basis-URL",
            "sprachmodell": "Sprachmodell",
            "parameter": "Parameter",
        }
        help_texts: dict[str, str] = {
            "bezeichnung": (
                "Unter ihr findet man die Konfiguration wieder. Nach dem Anlegen "
                "nicht mehr änderbar."
            ),
            "anbieter_token": (
                "Der Ladeknopf unten braucht es. Wird gespeichert, aber nie "
                "wieder angezeigt."
            ),
            "anbieter_basis_url": BASIS_URL_HINWEIS,
            "sprachmodell": "Mit dem Präfix des gewählten Anbieters.",
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


class TranskriptionsKonfigurationForm(ZeroRetentionFeldgruppeForm):
    """Die Schreibgeste an der append-only Transkription: eine neue Fassung."""

    class Meta:
        """Führt die Felder einer Fassung; das Token gibt sie nie zurück."""

        model: type[TranskriptionsKonfiguration] = TranskriptionsKonfiguration
        # Dieselbe Eingabefolge wie in der Modell-Konfiguration: Das Token
        # steht beim Anbieter, weil der Ladeknopf der Modellliste es braucht.
        fields: list[str] = [
            "anbieter",
            "anbieter_token",
            "anbieter_basis_url",
            "transkriptionsmodell",
            "sprache",
            "zero_retention_beleg",
        ]
        labels: dict[str, str] = {
            "anbieter": "Anbieter",
            "anbieter_token": "Token",
            "anbieter_basis_url": "Basis-URL",
            "transkriptionsmodell": "Transkriptionsmodell",
            "sprache": "Sprache",
        }
        help_texts: dict[str, str] = {
            "anbieter_token": (
                "Der Ladeknopf unten braucht es. Leer lassen übernimmt das Token "
                "der aktiven Fassung, solange Anbieter und Basis-URL gleich bleiben."
            ),
            "anbieter_basis_url": BASIS_URL_HINWEIS,
            "transkriptionsmodell": "Mit dem Präfix des gewählten Anbieters.",
            "sprache": "Sprachkürzel, damit die Transkription nicht raten muss.",
        }
        widgets: dict[str, PasswordInput] = {
            "anbieter_token": PasswordInput(render_value=False),
        }

    def __init__(
        self, *args: object, vorlage: TranskriptionsKonfiguration, **kwargs: object
    ) -> None:
        """Merkt sich die aktive Fassung, deren Token eine leere Eingabe meint.

        Das erklärende Konto geht als `konto` an die Feldgruppe der Erklärung.
        """
        super().__init__(*args, **kwargs)
        self._vorlage: TranskriptionsKonfiguration = vorlage

    def clean(self) -> dict[str, object]:
        """Liest eine leere Eingabe am selben Endpunkt als »Token der Vorlage«.

        Das Feld zeigt das hinterlegte Token nie an; ohne diese Lesart hieße
        jede neue Fassung mit anderem Modell oder anderer Sprache, das Token
        neu zu beschaffen. Bei neuem Anbieter oder neuer Basis-URL ginge das
        alte Token an einen anderen Empfänger, also bleibt es dort leer (#493).
        """
        cleaned_data: dict[str, object] = super().clean()
        if (
            not cleaned_data.get("anbieter_token")
            and cleaned_data.get("anbieter") == self._vorlage.anbieter
            and cleaned_data.get("anbieter_basis_url")
            == self._vorlage.anbieter_basis_url
        ):
            cleaned_data["anbieter_token"] = self._vorlage.anbieter_token
        return cleaned_data


class TokenRotationForm(Form):
    """Ein neues Token für eine bestehende Fassung, ohne neue Fassung."""

    # Nicht Pflicht am Feld: Das leere Token meldet die Domäne.
    anbieter_token = CharField(
        label="Neues Token",
        help_text=(
            "Ersetzt das hinterlegte Token dieser Fassung; Anbieter und "
            "Basis-URL bleiben. Wird gespeichert, aber nie wieder angezeigt."
        ),
        required=False,
        widget=PasswordInput(render_value=False),
    )

    def rotieren(self, konfiguration: TranskriptionsKonfiguration) -> bool:
        """Rotiert das Token; scheitert es, stehen die Gründe am Formular."""
        return _an_der_domaene(
            self,
            lambda daten: konfiguration.token_rotieren(daten["anbieter_token"]),
        )

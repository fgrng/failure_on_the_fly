"""Vertragstests für die dokumentierte Anbieter-Konfiguration (Spec C)."""

from pathlib import Path

from config.tests.dokumentation import (
    CONTEXT_PATH,
    README_PATH,
    REPO_ROOT,
    VERHALTEN_PATH,
    glossareintrag,
    readme_abschnitt,
    verhalten_abschnitt,
)


ENV_BEISPIEL_PATH: Path = REPO_ROOT / ".env.example"


def test_readme_nennt_den_betriebsschritt_nach_der_migration() -> None:
    """Das Deployment endet nicht mit der Migration, sondern mit dem Aktivieren."""
    deployment: str = readme_abschnitt("Deployment auf Uberspace")

    for klausel in (
        "/system/modell-konfiguration/",
        "anlegen und aktivieren",
        "nicht aus der Umgebung",
        "antwortet bis dahin kein Sprachmodell",
        "/system/transkription/",
    ):
        assert klausel in deployment


def test_verhaltensdoku_beschreibt_die_anbieterwahl_in_heutiger_form() -> None:
    """Der Anbieter ist eine feste Auswahl und trägt seine Zugangsdaten selbst."""
    konfiguration: str = verhalten_abschnitt("Modell-Konfiguration")

    for klausel in (
        "feste Auswahl",
        "`fake`",
        "`openrouter`",
        "`infomaniak`",
        "an der Konfiguration",
    ):
        assert klausel in konfiguration


def test_dokumentation_nennt_das_abgeloeste_vorgabemodell_nicht_mehr() -> None:
    """Weder Seed noch Anleitung kennen noch ein OpenAI-Vorgabemodell."""
    for pfad in (README_PATH, VERHALTEN_PATH):
        text: str = pfad.read_text()
        for abgeloest in ("OpenAI", "gpt-"):
            assert abgeloest not in text


def test_env_beispiel_fuehrt_nur_noch_die_zero_retention_einstellung() -> None:
    """Die Transkriptionseinstellungen sind entfallen, das Tor bleibt."""
    env_beispiel: str = ENV_BEISPIEL_PATH.read_text()

    assert "TRANSKRIPTION_ZERO_RETENTION" in env_beispiel
    for entfallen in ("TRANSKRIPTION_ANBIETER", "TRANSKRIPTION_MODELL="):
        assert entfallen not in env_beispiel


def test_keine_dokumentationsstelle_nennt_zugangsdaten_in_der_umgebung() -> None:
    """Zugangsdaten für das Sprachmodell stehen nirgends als Umgebungsvariable."""
    for pfad in (README_PATH, VERHALTEN_PATH, CONTEXT_PATH, ENV_BEISPIEL_PATH):
        assert "API_KEY" not in pfad.read_text()


def test_glossar_fuehrt_den_anbieter_als_eigenen_begriff() -> None:
    """Der Anbieter ist Fachsprache: feste Auswahl, je Naht eigen gewählt."""
    anbieter: str = glossareintrag("Anbieter")

    for klausel in ("`fake`", "`openrouter`", "`infomaniak`", "ADR-0036"):
        assert klausel in anbieter


def test_glossar_stellt_die_lebenszyklen_der_konfigurationen_gegenueber() -> None:
    """Unveränderlich und gepinnt gegenüber veränderlich und nicht exportiert."""
    modell: str = glossareintrag("Modell-Konfiguration")
    transkription: str = glossareintrag("Transkriptions-Konfiguration")

    assert "unveränderlich" in modell
    assert "gepinnt" in modell
    assert "aber veränderlich" in transkription
    assert "unveränderlich" not in transkription
    assert "weder gepinnt noch exportiert" in transkription


def test_glossar_nennt_den_anbieter_an_beiden_konfigurationen() -> None:
    """Sprachmodell und Transkription benennen je ihren eigenen Anbieter."""
    assert "**Anbieter**" in glossareintrag("Modell-Konfiguration")
    assert "**Anbieter**" in glossareintrag("Transkriptions-Konfiguration")

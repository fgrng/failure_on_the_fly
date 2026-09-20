"""Anbieterbindung und Parameter-Allowlist der Modell-Konfiguration."""

import pytest
from django.core.exceptions import ValidationError

from simulation.models import Anbieter, ModellKonfiguration


def _openrouter(**werte: object) -> ModellKonfiguration:
    # Legt eine gültige OpenRouter-Konfiguration an, geändert um die Testwerte.

    return ModellKonfiguration.objects.create(
        **{
            "anbieter": Anbieter.OPENROUTER,
            "sprachmodell": "openrouter/anthropic/claude-opus-4-8",
            "anbieter_token": "sk-or-geheim",
            **werte,
        }
    )


@pytest.mark.django_db
def test_fake_laeuft_ohne_endpunkt_und_ohne_token() -> None:
    """Die Vorgabe telefoniert nicht nach außen und braucht keine Zugangsdaten."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake",
        parameter={"skript": []},
    )

    assert konfiguration.anbieter == Anbieter.FAKE
    assert konfiguration.anbieter_basis_url == ""
    assert konfiguration.anbieter_token == ""


@pytest.mark.django_db
def test_openrouter_verlangt_praefix_und_token_und_kommt_ohne_url_aus() -> None:
    """Bei OpenRouter genügen Modellpräfix und Token."""

    konfiguration: ModellKonfiguration = _openrouter()

    assert konfiguration.anbieter_basis_url == ""


@pytest.mark.django_db
def test_infomaniak_verlangt_praefix_url_und_token() -> None:
    """Infomaniak spricht das OpenAI-Protokoll an einer kontoeigenen Wurzel."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        anbieter=Anbieter.INFOMANIAK,
        sprachmodell="openai/mistral24b",
        anbieter_basis_url="https://api.infomaniak.com/1/ai/4711/openai",
        anbieter_token="infomaniak-geheim",
    )

    assert konfiguration.pk is not None


@pytest.mark.django_db
def test_der_modellname_wird_nicht_gegen_eine_liste_geprueft() -> None:
    """Ein neues Modell ist ohne Codeänderung konfigurierbar."""

    konfiguration: ModellKonfiguration = _openrouter(
        sprachmodell="openrouter/hersteller/modell-das-es-2099-gibt"
    )

    assert konfiguration.pk is not None


@pytest.mark.django_db
def test_lehnt_fremdes_praefix_beim_anbieter_ab() -> None:
    """Ein Modellname ohne passendes Präfix erreicht den Anbieter nicht."""

    with pytest.raises(ValidationError, match="sprachmodell"):
        _openrouter(sprachmodell="openai/gpt-4o")


@pytest.mark.django_db
def test_lehnt_echten_anbieter_ohne_token_ab() -> None:
    """Ohne Token bedient der Anbieter keinen Aufruf."""

    with pytest.raises(ValidationError, match="anbieter_token"):
        _openrouter(anbieter_token="")


@pytest.mark.django_db
def test_lehnt_infomaniak_ohne_basis_url_ab() -> None:
    """Die Kontowurzel ist bei Infomaniak Teil der Anbieterbindung."""

    with pytest.raises(ValidationError, match="anbieter_basis_url"):
        ModellKonfiguration.objects.create(
            anbieter=Anbieter.INFOMANIAK,
            sprachmodell="openai/mistral24b",
            anbieter_token="infomaniak-geheim",
        )


@pytest.mark.django_db
def test_lehnt_fake_mit_zugangsdaten_ab() -> None:
    """Der deterministische Adapter hat weder Endpunkt noch Schlüssel."""

    with pytest.raises(ValidationError, match="anbieter_token"):
        ModellKonfiguration.objects.create(
            sprachmodell="fake",
            anbieter_token="sk-or-geheim",
        )


@pytest.mark.django_db
def test_lehnt_fake_mit_fremdem_modellnamen_ab() -> None:
    """Der Anbieter `fake` bedient genau ein Modell."""

    with pytest.raises(ValidationError, match="sprachmodell"):
        ModellKonfiguration.objects.create(sprachmodell="openrouter/gpt-4o")


@pytest.mark.django_db
def test_nimmt_mikro_stellschrauben_an() -> None:
    """Was das Modellverhalten feinjustiert, bleibt konfigurierbar."""

    konfiguration: ModellKonfiguration = _openrouter(
        parameter={"temperature": 0.2, "max_tokens": 800, "reasoning_effort": "low"}
    )

    assert konfiguration.parameter["temperature"] == 0.2


@pytest.mark.django_db
def test_lehnt_schluessel_ausserhalb_der_allowlist_ab() -> None:
    """Ein Tippfehler geht nicht wirkungslos an das Modell."""

    with pytest.raises(ValidationError, match="temperatur"):
        _openrouter(parameter={"temperatur": 0.2})


@pytest.mark.django_db
def test_lehnt_mock_response_ab() -> None:
    """Erfundene Antworten dürfen keine Erhebung durchlaufen lassen."""

    with pytest.raises(ValidationError, match="mock_response"):
        _openrouter(parameter={"mock_response": "Ich addiere."})


@pytest.mark.django_db
def test_lehnt_api_key_ab() -> None:
    """Der Schlüssel hat genau ein Feld und keinen zweiten Weg."""

    with pytest.raises(ValidationError, match="api_key"):
        _openrouter(parameter={"api_key": "sk-or-geheim"})


@pytest.mark.django_db
def test_lehnt_extra_body_ab() -> None:
    """Der Provider-Filter ist abgeleitet und nicht überschreibbar."""

    with pytest.raises(ValidationError, match="extra_body"):
        _openrouter(parameter={"extra_body": {"provider": {"zdr": False}}})


@pytest.mark.django_db
def test_erlaubt_skript_nur_beim_anbieter_fake() -> None:
    """Das Fake-Skript ist der Konfigurationskanal des zweiten Adapters."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake",
        parameter={"skript": [{"denkspur": "Ich addiere.", "aeusserung": "2/5."}]},
    )

    assert konfiguration.parameter["skript"] != []


@pytest.mark.django_db
def test_lehnt_skript_bei_echtem_anbieter_ab() -> None:
    """Ein echter Anbieter kennt keinen Skript-Parameter."""

    with pytest.raises(ValidationError, match="skript"):
        _openrouter(parameter={"skript": []})


@pytest.mark.django_db
def test_lehnt_ungueltiges_json_ab() -> None:
    """Was sich nicht als JSON schreiben lässt, wird nicht angelegt."""

    with pytest.raises(ValidationError, match="JSON"):
        _openrouter(parameter={"stop": {"unschreibbar"}})


@pytest.mark.django_db
def test_lehnt_parameter_ohne_schluesselraum_ab() -> None:
    """Parameter sind ein Objekt, keine Liste."""

    with pytest.raises(ValidationError, match="parameter"):
        _openrouter(parameter=[{"temperature": 0.2}])


@pytest.mark.django_db
def test_maskiertes_token_zeigt_nur_die_letzten_vier_zeichen() -> None:
    """Die Anzeige belegt, welches Token hängt, ohne es preiszugeben."""

    konfiguration: ModellKonfiguration = _openrouter(anbieter_token="sk-or-geheim1234")

    assert konfiguration.anbieter_token_maskiert == "••••••••1234"


@pytest.mark.django_db
def test_maskiertes_token_bleibt_ohne_token_leer() -> None:
    """Wo kein Token hängt, täuscht die Maske auch keines vor."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="fake",
    )

    assert konfiguration.anbieter_token_maskiert == ""


@pytest.mark.django_db
def test_maskiertes_token_gibt_ein_kurzes_token_gar_nicht_preis() -> None:
    """Bei vier Zeichen oder weniger stünde die »Maske« sonst für das Ganze."""

    konfiguration: ModellKonfiguration = _openrouter(anbieter_token="kurz")

    assert konfiguration.anbieter_token_maskiert == "••••••••"

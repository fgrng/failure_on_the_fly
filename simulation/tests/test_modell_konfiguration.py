"""Anbieterbindung und Parameter-Allowlist der Modell-Konfiguration."""

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from simulation.models import (
    AktiveModellKonfiguration,
    Anbieter,
    ModellKonfiguration,
    Verwendung,
)


def _openrouter(**werte: object) -> ModellKonfiguration:
    # Legt eine gültige OpenRouter-Konfiguration an, geändert um die Testwerte.

    return ModellKonfiguration.objects.create(
        **{
            "bezeichnung": "Test",
            "anbieter": Anbieter.OPENROUTER,
            "sprachmodell": "openrouter/anthropic/claude-opus-4-8",
            "anbieter_token": "sk-or-geheim",
            **werte,
        },
    )


@pytest.mark.django_db
def test_fake_laeuft_ohne_endpunkt_und_ohne_token() -> None:
    """Die Vorgabe telefoniert nicht nach außen und braucht keine Zugangsdaten."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Test",
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
        bezeichnung="Test",
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
            bezeichnung="Test",
            anbieter=Anbieter.INFOMANIAK,
            sprachmodell="openai/mistral24b",
            anbieter_token="infomaniak-geheim",
        )


@pytest.mark.django_db
def test_lehnt_fake_mit_zugangsdaten_ab() -> None:
    """Der deterministische Adapter hat weder Endpunkt noch Schlüssel."""

    with pytest.raises(ValidationError, match="anbieter_token"):
        ModellKonfiguration.objects.create(
            bezeichnung="Test",
            sprachmodell="fake",
            anbieter_token="sk-or-geheim",
        )


@pytest.mark.django_db
def test_lehnt_fake_mit_fremdem_modellnamen_ab() -> None:
    """Der Anbieter `fake` bedient genau ein Modell."""

    with pytest.raises(ValidationError, match="sprachmodell"):
        ModellKonfiguration.objects.create(
            bezeichnung="Test", sprachmodell="openrouter/gpt-4o"
        )


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
        bezeichnung="Test",
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
def test_maskiert_das_token_bis_auf_die_letzten_vier_zeichen() -> None:
    """Die letzten vier Zeichen genügen zum Abgleich mit dem Anbieter-Dashboard."""

    konfiguration: ModellKonfiguration = _openrouter(
        anbieter_token="sk-or-v1-geheimnis-wxyz"
    )

    assert konfiguration.anbieter_token_maskiert == "••••••••wxyz"


@pytest.mark.django_db
def test_maskiert_kurze_token_vollstaendig() -> None:
    """Bei einem kurzen Wert gäben vier Zeichen zu viel preis."""

    konfiguration: ModellKonfiguration = _openrouter(anbieter_token="sk-abc")

    assert konfiguration.anbieter_token_maskiert == "••••••••"


@pytest.mark.django_db
def test_maskiert_das_fehlende_token_als_leeren_wert() -> None:
    """Ohne Token gibt es nichts zu maskieren; den Hinweis trägt die Ansicht."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Test", sprachmodell="fake"
    )

    assert konfiguration.anbieter_token_maskiert == ""


@pytest.mark.django_db
def test_verlangt_eine_bezeichnung() -> None:
    """Eine namenlose Konfiguration entsteht nicht neu."""

    with pytest.raises(ValidationError) as fehler:
        ModellKonfiguration.objects.create(sprachmodell="fake")

    assert "bezeichnung" in fehler.value.message_dict


@pytest.mark.django_db
def test_die_bezeichnung_ist_nach_dem_anlegen_unveraenderlich() -> None:
    """Eine gepinnte Konfiguration heißt nie anders als bei der Erhebung."""

    konfiguration: ModellKonfiguration = _openrouter()
    konfiguration.bezeichnung = "Umbenannt"

    with pytest.raises(RuntimeError):
        konfiguration.save()


@pytest.mark.django_db
def test_unbelegte_verwendung_liefert_keine() -> None:
    """Solange die Administration nichts gesetzt hat, gibt es keine Konfiguration."""

    assert ModellKonfiguration.objects.aktive(Verwendung.BEWERTER) is None
    with pytest.raises(AktiveModellKonfiguration.DoesNotExist):
        ModellKonfiguration.objects.belegte(Verwendung.BEWERTER)


@pytest.mark.django_db
def test_dieselbe_konfiguration_dient_mehreren_verwendungen() -> None:
    """Eine kleine Instanz braucht nicht drei gleiche Datensätze."""

    konfiguration: ModellKonfiguration = _openrouter()
    for verwendung in Verwendung:
        ModellKonfiguration.objects.aktivieren(konfiguration, verwendung)

    assert ModellKonfiguration.objects.aktive_je_verwendung() == {
        Verwendung.SCHUELERIN: konfiguration.pk,
        Verwendung.LEHRPERSON: konfiguration.pk,
        Verwendung.BEWERTER: konfiguration.pk,
    }


@pytest.mark.django_db
def test_umschalten_einer_verwendung_laesst_die_anderen_unberuehrt() -> None:
    """Je Verwendung ein Zeiger; ein Wechsel bewegt nur den eigenen."""

    schuelerin: ModellKonfiguration = _openrouter()
    bewerter: ModellKonfiguration = _openrouter(bezeichnung="Bewerter")
    ModellKonfiguration.objects.aktivieren(schuelerin, Verwendung.SCHUELERIN)
    ModellKonfiguration.objects.aktivieren(schuelerin, Verwendung.BEWERTER)

    ModellKonfiguration.objects.aktivieren(bewerter, Verwendung.BEWERTER)

    assert ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN) == schuelerin
    assert ModellKonfiguration.objects.belegte(Verwendung.BEWERTER) == bewerter
    assert AktiveModellKonfiguration.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_migration_macht_die_aktive_zur_schuelerin_und_benennt_den_bestand() -> None:
    """Der Umstieg auf Verwendungen verliert keine aktive Konfiguration."""

    vorher = [("simulation", "0006_transkriptionskonfiguration")]
    nachher = [("simulation", "0007_modellkonfiguration_je_verwendung")]
    executor: MigrationExecutor = MigrationExecutor(connection)
    executor.migrate(vorher)
    try:
        alte_apps = executor.loader.project_state(vorher).apps
        alte_konfiguration = alte_apps.get_model(
            "simulation", "ModellKonfiguration"
        ).objects.create(sprachmodell="fake")
        alte_apps.get_model("simulation", "AktiveModellKonfiguration").objects.create(
            konfiguration=alte_konfiguration, singleton=1
        )
        MigrationExecutor(connection).migrate(nachher)
        konfiguration: ModellKonfiguration = ModellKonfiguration.objects.get(
            pk=alte_konfiguration.pk
        )
        aktive: ModellKonfiguration | None = ModellKonfiguration.objects.aktive(
            Verwendung.SCHUELERIN
        )
    finally:
        MigrationExecutor(connection).migrate(nachher)

    assert konfiguration.bezeichnung == f"fake (Nr. {konfiguration.pk})"
    assert konfiguration.angelegt_am is None
    assert aktive == konfiguration
    assert ModellKonfiguration.objects.aktive(Verwendung.LEHRPERSON) is None

"""Anbieterbindung und Parameter-Allowlist der Modell-Konfiguration."""

from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from config.tests.aufbau import erklaerte
from konten.models import Konto
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
        }
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
def test_lehnt_timeout_ab() -> None:
    """Die Frist gehört der Naht und ist keine Stellschraube."""

    with pytest.raises(ValidationError, match="timeout"):
        _openrouter(parameter={"timeout": 5})


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
def test_nach_dem_aktivieren_liefert_die_verwendung_genau_diese() -> None:
    """Der Zeiger einer Verwendung zeigt auf die zuletzt aktivierte."""

    erste: ModellKonfiguration = _openrouter()
    zweite: ModellKonfiguration = _openrouter(bezeichnung="Zweite")
    ModellKonfiguration.objects.aktivieren(erste, Verwendung.LEHRPERSON)

    ModellKonfiguration.objects.aktivieren(zweite, Verwendung.LEHRPERSON)

    assert ModellKonfiguration.objects.aktive(Verwendung.LEHRPERSON) == zweite
    assert AktiveModellKonfiguration.objects.count() == 1


@pytest.mark.django_db
def test_unbelegte_verwendung_liefert_keine() -> None:
    """Solange die Administration nichts gesetzt hat, gibt es keine Konfiguration."""

    ModellKonfiguration.objects.aktivieren(
        erklaerte(_openrouter()), Verwendung.SCHUELERIN
    )

    assert ModellKonfiguration.objects.aktive(Verwendung.BEWERTER) is None
    with pytest.raises(AktiveModellKonfiguration.DoesNotExist):
        ModellKonfiguration.objects.belegte(Verwendung.BEWERTER)


@pytest.mark.django_db
def test_dieselbe_konfiguration_dient_mehreren_verwendungen() -> None:
    """Eine kleine Instanz braucht nicht drei gleiche Datensätze."""

    konfiguration: ModellKonfiguration = erklaerte(_openrouter())
    for verwendung in Verwendung:
        ModellKonfiguration.objects.aktivieren(konfiguration, verwendung)

    for verwendung in Verwendung:
        assert ModellKonfiguration.objects.belegte(verwendung) == konfiguration


@pytest.mark.django_db
def test_umschalten_einer_verwendung_laesst_die_anderen_unberuehrt() -> None:
    """Je Verwendung ein Zeiger; ein Wechsel bewegt nur den eigenen."""

    schuelerin: ModellKonfiguration = erklaerte(_openrouter())
    bewerter: ModellKonfiguration = _openrouter(bezeichnung="Bewerter")
    ModellKonfiguration.objects.aktivieren(schuelerin, Verwendung.SCHUELERIN)
    ModellKonfiguration.objects.aktivieren(schuelerin, Verwendung.BEWERTER)

    ModellKonfiguration.objects.aktivieren(bewerter, Verwendung.BEWERTER)

    assert ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN) == schuelerin
    assert ModellKonfiguration.objects.aktive(Verwendung.BEWERTER) == bewerter
    assert ModellKonfiguration.objects.aktive(Verwendung.LEHRPERSON) is None


@pytest.mark.django_db
def test_aktive_je_verwendung_nennt_nur_belegte_verwendungen() -> None:
    """Die Tabelle erfährt in einer Abfrage, welche Verwendung wohin zeigt."""

    konfiguration: ModellKonfiguration = erklaerte(_openrouter())
    ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)
    ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.BEWERTER)

    assert ModellKonfiguration.objects.aktive_je_verwendung() == {
        Verwendung.SCHUELERIN: konfiguration.pk,
        Verwendung.BEWERTER: konfiguration.pk,
    }


@pytest.mark.django_db
def test_haelt_den_anlagezeitpunkt_fest() -> None:
    """Das Anlagedatum unterscheidet gleichnamige Fassungen in der Tabelle."""

    vorher: datetime = timezone.now()

    konfiguration: ModellKonfiguration = _openrouter()

    assert konfiguration.angelegt_am is not None
    assert vorher <= konfiguration.angelegt_am <= timezone.now()


def test_die_verwendung_hat_keinen_default() -> None:
    """Keine neue Stelle erwischt versehentlich die Schüler:innen-Konfiguration."""

    with pytest.raises(TypeError):
        ModellKonfiguration.objects.aktive()  # ty: ignore[missing-argument]
    with pytest.raises(TypeError):
        ModellKonfiguration.objects.belegte()  # ty: ignore[missing-argument]
    with pytest.raises(TypeError):
        ModellKonfiguration.objects.aktivieren(  # ty: ignore[missing-argument]
            ModellKonfiguration(bezeichnung="Test", sprachmodell="fake")
        )


@pytest.mark.django_db
def test_erlaubt_fortlesen_des_skripts_nur_beim_anbieter_fake() -> None:
    """Das Fortlesen über Aufrufe ist ein opt-in des Fakes, kein Modellparameter."""

    ModellKonfiguration.objects.create(
        bezeichnung="Test",
        sprachmodell="fake",
        parameter={"skript": [], "skript_fortlesen": True},
    )

    with pytest.raises(ValidationError, match="skript_fortlesen"):
        _openrouter(parameter={"skript_fortlesen": True})


@pytest.mark.django_db
def test_die_erklaerung_haelt_beleg_zeitpunkt_und_konto_fest() -> None:
    """Zeitpunkt und Konto schreibt die Erklärung selbst mit."""

    konto: Konto = Konto.objects.create_user(username="linus", is_superuser=True)
    konfiguration: ModellKonfiguration = _openrouter()

    konfiguration.zero_retention_erklaeren("AVV mit OpenRouter vom 01.10.2026", konto)

    gespeichert: ModellKonfiguration = ModellKonfiguration.objects.get(
        pk=konfiguration.pk
    )
    assert gespeichert.zero_retention_erklaert
    assert gespeichert.zero_retention_beleg == "AVV mit OpenRouter vom 01.10.2026"
    assert gespeichert.zero_retention_erklaert_von == konto
    assert gespeichert.zero_retention_erklaert_am is not None


@pytest.mark.django_db
def test_die_erklaerung_laesst_sich_beim_anlegen_abgeben() -> None:
    """Die Erklärung kann mit der Fassung zusammen entstehen."""

    konto: Konto = Konto.objects.create_user(username="linus", is_superuser=True)
    konfiguration: ModellKonfiguration = ModellKonfiguration(
        bezeichnung="Test",
        anbieter=Anbieter.OPENROUTER,
        sprachmodell="openrouter/anthropic/claude-opus-4-8",
        anbieter_token="sk-or-geheim",
    )

    konfiguration.zero_retention_erklaeren("AVV", konto)
    konfiguration.save()

    assert ModellKonfiguration.objects.get(pk=konfiguration.pk).zero_retention_erklaert


@pytest.mark.django_db
def test_die_erklaerung_verlangt_einen_beleg() -> None:
    """Ein bloßes Häkchen ohne Grundlage ist keine Erklärung."""

    konto: Konto = Konto.objects.create_user(username="linus", is_superuser=True)
    konfiguration: ModellKonfiguration = _openrouter()

    with pytest.raises(ValidationError) as fehler:
        konfiguration.zero_retention_erklaeren("  ", konto)

    assert "zero_retention_beleg" in fehler.value.message_dict
    assert not ModellKonfiguration.objects.get(
        pk=konfiguration.pk
    ).zero_retention_erklaert


@pytest.mark.django_db
def test_bei_fake_ist_keine_erklaerung_zulaessig() -> None:
    """Ohne Auftragsverarbeiter gibt es nichts zu erklären."""

    konto: Konto = Konto.objects.create_user(username="linus", is_superuser=True)
    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Test", sprachmodell="fake"
    )

    with pytest.raises(ValidationError) as fehler:
        konfiguration.zero_retention_erklaeren("AVV", konto)

    assert "zero_retention_beleg" in fehler.value.message_dict
    assert not ModellKonfiguration.objects.get(
        pk=konfiguration.pk
    ).zero_retention_erklaert


@pytest.mark.django_db
def test_eine_abgegebene_erklaerung_laesst_sich_nicht_aendern() -> None:
    """Eine zweite Erklärung überschriebe Beleg und Zeitpunkt der ersten."""

    konto: Konto = Konto.objects.create_user(username="linus", is_superuser=True)
    konfiguration: ModellKonfiguration = _openrouter()
    konfiguration.zero_retention_erklaeren("AVV vom 01.10.2026", konto)

    with pytest.raises(ValidationError):
        ModellKonfiguration.objects.get(pk=konfiguration.pk).zero_retention_erklaeren(
            "AVV vom 15.10.2026", konto
        )

    assert (
        ModellKonfiguration.objects.get(pk=konfiguration.pk).zero_retention_beleg
        == "AVV vom 01.10.2026"
    )


@pytest.mark.django_db
def test_eine_gleichzeitige_erklaerung_gewinnt_und_wird_sichtbar() -> None:
    """Wer zu spät erklärt, überschreibt nichts und sieht die frühere Erklärung."""

    konto: Konto = Konto.objects.create_user(username="linus", is_superuser=True)
    konfiguration: ModellKonfiguration = _openrouter()
    veraltet: ModellKonfiguration = ModellKonfiguration.objects.get(pk=konfiguration.pk)
    konfiguration.zero_retention_erklaeren("AVV vom 01.10.2026", konto)

    with pytest.raises(ValidationError):
        veraltet.zero_retention_erklaeren("AVV vom 15.10.2026", konto)

    assert veraltet.zero_retention_erklaert
    assert veraltet.zero_retention_beleg == "AVV vom 01.10.2026"


@pytest.mark.django_db
def test_ohne_erklaerung_scheitert_die_aktivierung_fuer_die_schuelerin() -> None:
    """Das Tor sitzt in der Domäne, nicht nur in der Oberfläche."""

    konfiguration: ModellKonfiguration = _openrouter()

    with pytest.raises(ValidationError):
        ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)

    assert ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN) is None


@pytest.mark.django_db
def test_mit_erklaerung_gelingt_die_aktivierung_fuer_die_schuelerin() -> None:
    """Eine erklärte Fassung darf Eingaben echter Personen verarbeiten."""

    konfiguration: ModellKonfiguration = _openrouter()
    konfiguration.zero_retention_erklaeren(
        "AVV", Konto.objects.create_user(username="linus", is_superuser=True)
    )

    ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)

    assert ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN) == konfiguration


@pytest.mark.django_db
def test_lehrperson_und_bewerter_bleiben_ohne_erklaerung_frei() -> None:
    """Evals verarbeiten nur simulierte Gespräche (ADR-0046)."""

    konfiguration: ModellKonfiguration = _openrouter()

    ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.LEHRPERSON)
    ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.BEWERTER)

    assert ModellKonfiguration.objects.aktive(Verwendung.LEHRPERSON) == konfiguration
    assert ModellKonfiguration.objects.aktive(Verwendung.BEWERTER) == konfiguration


@pytest.mark.django_db
def test_fake_laesst_sich_ohne_erklaerung_fuer_die_schuelerin_aktivieren() -> None:
    """Entwicklung und Workshop laufen ohne externen Anbieter."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Test", sprachmodell="fake"
    )

    ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung.SCHUELERIN)

    assert ModellKonfiguration.objects.aktive(Verwendung.SCHUELERIN) == konfiguration

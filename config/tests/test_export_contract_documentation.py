"""Vertragstests für den veröffentlichten Datenspur-Export."""

from pathlib import Path

from config.tests.dokumentation import REPO_ROOT


ADR_PATH: Path = REPO_ROOT / "docs/adr/0029-datenspur-export-kontrakt.md"
OPEN_QUESTIONS_PATH: Path = REPO_ROOT / "docs/open-questions.md"
ADR_0030_PATH: Path = (
    REPO_ROOT
    / "docs/adr/0030-positionsmarker-umhuellung-im-platzhalterwert-und-harte-umstellung-des-platzhaltervertrags.md"
)


def test_adr_0029_documents_the_self_contained_long_relational_export() -> None:
    """Der Export-Kontrakt hält seine wesentlichen Festlegungen fest."""
    adr: str = ADR_PATH.read_text()

    assert adr.startswith("---\nstatus: accepted\n---")
    for contract_clause in (
        "long-relational",
        "Erhebung ist die Exporteinheit",
        "selbsttragend",
        "RFC 4180",
        "elf Dateien",
        "UTF-8 ohne BOM",
        "ISO 8601",
        "`NA` für `NULL`",
        "Leerstring",
        "Klarnamen",
        "#122",
    ):
        assert contract_clause in adr


def test_adr_0029_documents_the_provider_column_and_its_exclusions() -> None:
    """Der Kontrakt nennt Anbieterspalte, ausgeschlossene Felder und Provider-Filter."""
    adr: str = ADR_PATH.read_text()

    for provider_clause in (
        "`id`, `anbieter`, `sprachmodell`, `parameter`",
        "`anbieter_token`",
        "`anbieter_basis_url`",
        "product_id",
        "Provider-Filter",
        "ADR-0026",
    ):
        assert provider_clause in adr


def test_open_questions_removes_the_resolved_export_question() -> None:
    """Die übrigen offenen Fragen bleiben lückenlos nummeriert."""
    open_questions: str = OPEN_QUESTIONS_PATH.read_text()

    assert "## 2. Export-Formate und Granularität" not in open_questions
    assert "## 1. Wiederholversuche und Sitzungsobergrenze" in open_questions
    assert "## 2. Zulässige Anbieter und Modelle" in open_questions
    assert "## 3." not in open_questions


def test_adr_0030_documents_positionsmarker_umhuellung_and_contract_break() -> None:
    """ADR 0030 hält Positionsmarker, Umhüllung und den harten Schnitt fest."""
    adr: str = ADR_0030_PATH.read_text()

    assert adr.startswith("---\nstatus: accepted\n---")
    for clause in (
        "Positionsmarker im Text anstelle eines separaten Layout-Feldes",
        "Umhüllung als Eigenschaft des Platzhalterwerts anstelle der Kern-Vorlage",
        "Harter Schnitt am Platzhaltervertrag",
        "keine Produktivdaten",
    ):
        assert clause in adr

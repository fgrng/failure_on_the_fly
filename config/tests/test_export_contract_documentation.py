"""Vertragstests für den veröffentlichten Datenspur-Export."""

from pathlib import Path


REPO_ROOT: Path = Path(__file__).parents[2]
ADR_PATH: Path = REPO_ROOT / "docs/adr/0029-datenspur-export-kontrakt.md"
OPEN_QUESTIONS_PATH: Path = REPO_ROOT / "docs/open-questions.md"
DOMAIN_ADR_PATH: Path = (
    REPO_ROOT / "docs/adr/0016-domaenenobjekte-als-django-apps-zwei-naehte.md"
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


def test_open_questions_removes_the_resolved_export_question() -> None:
    """Die übrigen offenen Fragen bleiben lückenlos nummeriert."""
    open_questions: str = OPEN_QUESTIONS_PATH.read_text()

    assert "## 2. Export-Formate und Granularität" not in open_questions
    assert "## 2. Wiederholversuche und Sitzungsobergrenze" in open_questions
    assert "## 3. Zulässige Anbieter und Modelle" in open_questions
    assert "## 4." not in open_questions


def test_adr_0016_references_the_renumbered_model_question() -> None:
    """Der Verweis auf die offene Modellfrage folgt ihrer neuen Nummer."""
    domain_adr: str = DOMAIN_ADR_PATH.read_text()

    assert "Frage 3" in domain_adr
    assert "Frage 7" not in domain_adr

"""Vertragstests für den veröffentlichten Datenspur-Export."""

from pathlib import Path


REPO_ROOT = Path(__file__).parents[2]


def test_adr_0029_holds_the_self_contained_long_relational_export_contract() -> None:
    """Der Export-Kontrakt bleibt samt NULL-Begründung und Fragenpflege sichtbar."""
    adr = (REPO_ROOT / "docs/adr/0029-datenspur-export-kontrakt.md").read_text()
    open_questions = (REPO_ROOT / "docs/open-questions.md").read_text()
    domain_adr = (
        REPO_ROOT / "docs/adr/0016-domaenenobjekte-als-django-apps-zwei-naehte.md"
    ).read_text()

    assert adr.startswith("---\nstatus: accepted\n---")
    for contract_clause in (
        "long-relational",
        "Erhebung ist die Exporteinheit",
        "selbsttragend",
        "RFC 4180",
        "`NA` für `NULL`",
        "Leerstring",
        "Klarnamen",
        "#122",
    ):
        assert contract_clause in adr

    assert "## 2. Export-Formate und Granularität" not in open_questions
    assert "## 2. Wiederholversuche und Sitzungsobergrenze" in open_questions
    assert "## 3. Zulässige Anbieter und Modelle" in open_questions
    assert "## 4." not in open_questions
    assert "Frage 3" in domain_adr
    assert "Frage 7" not in domain_adr

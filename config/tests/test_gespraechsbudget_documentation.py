"""Vertragstests für die dokumentierte Uhr des Gesprächsbudgets."""

from pathlib import Path

from config.tests.dokumentation import (
    REPO_ROOT,
    abschnitt,
    glossareintrag,
    in_einer_zeile,
)

ADR_0012_PATH: Path = (
    REPO_ROOT / "docs/adr/0012-gespraechsbudget-unsichtbar-uhr-pausiert.md"
)


def test_adr_0012_haelt_die_uhr_beim_schrittbudget_an() -> None:
    """Der Abschnitt zur Uhr sagt, dass ein Schrittbudget keine Uhr trägt."""
    uhrenabschnitt: str = in_einer_zeile(
        abschnitt(ADR_0012_PATH, "Die Uhr läuft nur, wenn die Teilnehmer:in am Zug ist")
    )

    for klausel in (
        "schrittbasiertem Budget läuft überhaupt keine Uhr",
        "Abwesenheit einer Messung",
    ):
        assert klausel in uhrenabschnitt, klausel


def test_adr_0012_zieht_die_folge_fuer_den_export() -> None:
    """Die Konsequenzen nennen die echte Null, die der Export danach trägt."""
    folgen: str = in_einer_zeile(abschnitt(ADR_0012_PATH, "Consequences"))

    assert "eine echte Null" in folgen
    assert "ADR-0029" in folgen


def test_glossar_sagt_dass_die_uhr_nur_beim_zeitbudget_laeuft() -> None:
    """Das Glossar bindet die Uhr an die Zeitbegrenzung, nicht an jedes Budget."""
    eintrag: str = glossareintrag("Gesprächsbudget")

    assert "Bei schrittbasiertem Budget läuft keine Uhr" in eintrag

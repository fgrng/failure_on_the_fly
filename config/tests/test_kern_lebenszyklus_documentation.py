"""Vertragstests für die dokumentierte Lebenszyklus-Form des Simulationskerns."""

from pathlib import Path

from config.tests.dokumentation import (
    REPO_ROOT,
    glossareintrag,
    readme_abschnitt,
)

ADR_0003_PATH: Path = (
    REPO_ROOT / "docs/adr/0003-versionierte-artefakte-entwurf-final.md"
)
ADR_0021_PATH: Path = (
    REPO_ROOT / "docs/adr/0021-lebenszyklus-form-vier-felder-partielle-indizes.md"
)
ADR_0035_PATH: Path = (
    REPO_ROOT / "docs/adr/0035-simulationskern-genau-eine-finale-fassung.md"
)
AUTOR_GEM_PATH: Path = (
    REPO_ROOT / "docs/vignette-author-gem/knowledge/01-editor-felder-und-schema.md"
)
ZEIGER_AUF_ADR_0035: str = "Für den Simulationskern gilt stattdessen ADR-0035."


def absatz_mit(text: str, zusage: str) -> str:
    """Liefert den durch Leerzeilen begrenzten Absatz, der die Zusage trägt."""
    return next(absatz for absatz in text.split("\n\n") if zusage in absatz)


def test_adr_0035_haelt_widerruf_und_preis_fest() -> None:
    """Das neue ADR trägt die volle Begründung der einen finalen Fassung."""
    adr: str = ADR_0035_PATH.read_text()

    assert adr.startswith("---\nstatus: accepted\n---")
    for klausel in (
        "simulation_eine_finale_fassung_pro_historie",
        "überholt",
        "Widerruf",
        "wieder zur Basis für neue Entwürfe",
        "Archivierung ist umkehrbar",
        "physisches Löschen mit besserer Presse",
        "ADR-0029",
        "Preis",
        "ADR-0021",
        "Considered Options",
    ):
        assert klausel in adr


def test_adr_0035_zaehlt_die_verworfenen_optionen_der_session_auf() -> None:
    """Jede in der Grilling-Session verworfene Option steht im ADR."""
    verworfene_optionen: str = ADR_0035_PATH.read_text().split("Considered Options")[1]

    for option in (
        "vierter Zustand",
        "`archivieren()`",
        "`entarchivieren()`",
        "`bearbeiten()`",
        "Datenmigration",
        "`messages`",
        "simulation_keine_nichtarchivierten_schwestern",
    ):
        assert option in verworfene_optionen


def test_die_widerrufenen_adrs_tragen_den_zeiger_auf_adr_0035() -> None:
    """ADR-0003 und ADR-0021 markieren die für den Kern gebrochene Zusage."""
    assert ZEIGER_AUF_ADR_0035 in ADR_0003_PATH.read_text()
    assert ZEIGER_AUF_ADR_0035 in ADR_0021_PATH.read_text()


def test_jede_von_adr_0035_widerrufene_zusage_traegt_den_zeiger() -> None:
    """Keiner der drei widerrufenen Sätze aus ADR-0003 steht unmarkiert."""
    adr: str = ADR_0003_PATH.read_text()

    for zusage in (
        "Archivierung ist umkehrbar",
        "wieder zur Basis für neue Entwürfe",
        "physisches Löschen mit besserer Presse",
    ):
        assert ZEIGER_AUF_ADR_0035 in absatz_mit(adr, zusage)


def test_der_zeiger_steht_bei_den_drei_kanten_des_automaten() -> None:
    """ADR-0021 markiert die Kantenzusage, nicht irgendeine andere Stelle."""
    adr: str = ADR_0021_PATH.read_text()

    assert ZEIGER_AUF_ADR_0035 in absatz_mit(adr, "Der Automat hat drei Kanten")


def test_glossar_fuehrt_die_linie_des_kerns_als_erzwungen() -> None:
    """Die eine Linie des Kerns ist erzwungen, nicht bloß konzeptionell."""
    historie: str = glossareintrag("Historie")

    assert "Der Kern ist konzeptionell eine einzige Linie" not in historie
    assert "Der Kern ist eine einzige Linie" in historie


def test_glossar_nimmt_den_kern_von_der_umkehrbarkeit_aus() -> None:
    """Der Eintrag »Archiviert« verspricht Umkehrbarkeit nicht mehr pauschal."""
    archiviert: str = glossareintrag("Archiviert")

    assert "Beim Simulationskern heißt derselbe Zustand **überholt**" in archiviert
    assert "nicht umkehrbar (ADR-0035)" in archiviert


def test_keine_projektdokumentation_kennt_die_kern_archivgesten() -> None:
    """Archivieren und Entarchivieren des Kerns stehen nirgends als Geste."""
    for text in (
        readme_abschnitt("Simulationskern"),
        glossareintrag("Historie"),
        glossareintrag("Archiviert"),
        AUTOR_GEM_PATH.read_text(),
    ):
        assert "entarchivier" not in text.lower()
        assert "zurückholen" not in text


def test_readme_beschreibt_den_kern_nach_dem_ueberholen() -> None:
    """Der README-Abschnitt zum Kern nennt die eine Fassung und den Hinweis."""
    kern_abschnitt: str = readme_abschnitt("Simulationskern")

    for klausel in (
        "genau eine finale Fassung",
        "Das Finalisieren archiviert die bisherige",
        "tragen aber keine Aktionen mehr",
        "weist neben dem Vorspulen-Knopf auf den überholten Pin hin",
    ):
        assert klausel in kern_abschnitt
    for veraltete_zusage in (
        "alle finalen",
        "zurückholen",
        "umkehrbar",
        "scheitern erst beim Finalisieren",
        "kann nicht archiviert werden",
    ):
        assert veraltete_zusage not in kern_abschnitt


def test_autoren_wissensbasis_sperrt_den_ueberholten_kern_nicht_mehr() -> None:
    """Das Finalisieren einer Vignette verlangt keinen aktuellen Kern."""
    wissensbasis: str = AUTOR_GEM_PATH.read_text()

    assert "ein archivierter Kern" not in wissensbasis
    assert "verlangt vorher ein Vorspulen" not in wissensbasis

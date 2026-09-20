"""Vertragstests für die dokumentierte Lebenszyklus-Form des Simulationskerns."""

from pathlib import Path


REPO_ROOT: Path = Path(__file__).parents[2]
ADR_0003_PATH: Path = (
    REPO_ROOT / "docs/adr/0003-versionierte-artefakte-entwurf-final.md"
)
ADR_0021_PATH: Path = (
    REPO_ROOT / "docs/adr/0021-lebenszyklus-form-vier-felder-partielle-indizes.md"
)
ADR_0035_PATH: Path = (
    REPO_ROOT / "docs/adr/0035-simulationskern-genau-eine-finale-fassung.md"
)
CONTEXT_PATH: Path = REPO_ROOT / "CONTEXT.md"
README_PATH: Path = REPO_ROOT / "README.md"
AUTOR_GEM_PATH: Path = (
    REPO_ROOT / "docs/vignette-author-gem/knowledge/01-editor-felder-und-schema.md"
)


def readme_kern_abschnitt() -> str:
    """Liefert den README-Abschnitt zum Simulationskern in einer Zeile."""
    abschnitt: str = (
        README_PATH.read_text().split("## Simulationskern")[1].split("\n## ")[0]
    )
    return " ".join(abschnitt.split())


def test_adr_0035_haelt_widerruf_preis_und_verworfene_optionen_fest() -> None:
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
    zeiger: str = "Für den Simulationskern gilt stattdessen ADR-0035."

    assert zeiger in ADR_0003_PATH.read_text()
    assert zeiger in ADR_0021_PATH.read_text()


def test_glossar_behauptet_die_linie_nicht_mehr_als_bloszes_konzept() -> None:
    """Die eine Linie des Kerns ist erzwungen, nicht konzeptionell."""
    glossar: str = CONTEXT_PATH.read_text()

    assert "Der Kern ist konzeptionell eine einzige Linie" not in glossar
    assert "Der Kern ist eine einzige Linie" in glossar


def test_keine_projektdokumentation_kennt_die_kern_archivgesten() -> None:
    """Archivieren und Entarchivieren des Kerns stehen nirgends als Geste."""
    for text in (
        readme_kern_abschnitt(),
        CONTEXT_PATH.read_text(),
        AUTOR_GEM_PATH.read_text(),
    ):
        assert "entarchivier" not in text.lower()
        assert "zurückholen" not in text


def test_readme_beschreibt_den_kern_nach_dem_ueberholen() -> None:
    """Der README-Abschnitt zum Kern nennt die eine Fassung und den Hinweis."""
    kern_abschnitt: str = readme_kern_abschnitt()

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

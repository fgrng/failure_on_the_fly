"""Vertragstests für den dokumentierten Export-Kontrakt aus ADR-0029."""

from config.tests.dokumentation import (
    ADR_0029_PATH,
    abschnitt,
    in_einer_zeile,
    readme_abschnitt,
)


def adr_text() -> str:
    """Liefert ADR-0029 in einer Zeile, damit der Umbruch nichts verdeckt."""
    return in_einer_zeile(ADR_0029_PATH.read_text())


def adr_abschnitt(ueberschrift: str) -> str:
    """Liefert den ADR-Abschnitt unter der Überschrift in einer Zeile."""
    return in_einer_zeile(abschnitt(ADR_0029_PATH, ueberschrift))


def test_adr_0029_nennt_die_ausgelieferte_dateizahl() -> None:
    """Die Dateizahl im Kontrakt ist die des gebauten ZIP."""
    dateiformat: str = adr_abschnitt("Dateiformat")

    assert "**fünfzehn Dateien**" in dateiformat
    assert "elf Dateien" not in dateiformat


def test_adr_0029_listet_die_fragebogen_tabellen_mit_ihren_spalten() -> None:
    """Die Dateitabelle trägt die Fragebogen-Tabellen vollständig."""
    dateiformat: str = adr_abschnitt("Dateiformat")

    for zeile in (
        "| `itembloecke.csv` | `id`, `teilnahme_token`, `andockpunkt`, "
        "`sitzung_id`, `vorgelegt_am`, `erledigt_am` |",
        "| `item_antworten.csv` | `itemblock_id`, `teilnahme_token`, `item_id`, "
        "`item_typ`, `andockpunkt`, `sitzung_id`, `position`, `freitext`, "
        "`likert_stufe` |",
        "| `fragebogen_items.csv` | `id`, `typ`, `wortlaut` |",
        "| `likert_skala.csv` | `stufe`, `pol` |",
    ):
        assert zeile in dateiformat


def test_adr_0029_haelt_die_kodierungsrichtung_der_likert_skala_fest() -> None:
    """Die Richtung der Skala steht im Kontrakt, nicht nur im Quellcode."""
    adr: str = adr_text()

    for klausel in (
        "`likert_stufe` steigt mit der Zustimmung",
        "1 ist »Stimme gar nicht zu«",
        "6 ist »Stimme voll zu«",
    ):
        assert klausel in adr


def test_adr_0029_begruendet_den_erledigt_marker_am_itemblock() -> None:
    """Der Marker sitzt am Block; die Antwortzeile bleibt reine Datenspur."""
    adr: str = adr_text()

    for klausel in (
        "Der Erledigt-Marker sitzt am Itemblock",
        "reine Datenspur",
        "ADR-0041",
    ):
        assert klausel in adr


def test_adr_0029_begruendet_die_fehlende_item_historie() -> None:
    """Die Item-Historie bleibt draußen, auch nicht als bloße ID."""
    adr: str = adr_text()

    for klausel in (
        "Die Item-Historie läuft nicht mit",
        "auch nicht als bloße ID",
        "Items werden nicht gezogen",
    ):
        assert klausel in adr


def test_adr_0029_haelt_die_erweiterung_als_rein_additiv_fest() -> None:
    """Bestehende Dateien, Spalten und ihre Reihenfolge bleiben unberührt."""
    adr: str = adr_text()

    for klausel in (
        "ausschließlich hinzugefügt",
        "Keine bestehende Datei, Spalte oder Spaltenreihenfolge ändert sich",
        "bestehende Analyseskripte brechen nicht",
    ):
        assert klausel in adr


def test_adr_0029_verwirft_die_anderen_orte_der_likert_kodierung() -> None:
    """Kommentarzeile und Liesmich-Datei stehen bei den erwogenen Optionen."""
    optionen: str = adr_abschnitt("Erwogene Optionen")

    for klausel in (
        "Kommentarzeile",
        "RFC 4180 kennt keine Kommentare",
        "Liesmich-Datei",
        "nicht maschinenlesbare Artefakt",
    ):
        assert klausel in optionen


def test_readme_beschreibt_die_fragebogen_tabellen_des_downloads() -> None:
    """Der Download-Absatz nennt, was der Fragebogen-Teil beilegt."""
    abschnitt: str = readme_abschnitt("Erhebungen verwalten")

    for klausel in (
        "vollen Wortlaut",
        "Kodierung der Likert-Skala",
        "1 »Stimme gar nicht zu« bis 6 »Stimme voll zu«",
        "Itemblöcke",
    ):
        assert klausel in abschnitt

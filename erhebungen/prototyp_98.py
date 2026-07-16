"""PROTOTYP zu Issue #98 — WEGWERFCODE, nicht produktiv nutzen.

Frage: Wie stellt eine Forschende aus der Item-Bibliothek die Batterie ihrer
Erhebung zusammen? Drei Varianten der Zuordnungs-UI, umschaltbar über
`?variant=A|B|C` auf der bestehenden Erhebungs-Detailseite.

Die App `fragebogen_items` existiert noch nicht (Spec #97 baut sie erst), also
liefert dieses Modul Stub-Daten. Nichts hier wird persistiert; alle Aktionen
laufen clientseitig in Alpine. Nach der Entscheidung: Datei löschen.
"""

from typing import Any

_BIBLIOTHEK: list[dict[str, Any]] = [
    {"pk": 1, "text": "Wie sicher fühlten Sie sich bei Ihrer Diagnose?", "typ": "likert"},
    {"pk": 2, "text": "Was hat Sie an der Reaktion der Schülerin überrascht?", "typ": "freitext"},
    {"pk": 3, "text": "Die Vignette wirkte auf mich realistisch.", "typ": "likert"},
    {"pk": 4, "text": "Ich konnte den zugrunde liegenden Denkfehler klar benennen.", "typ": "likert"},
    {"pk": 5, "text": "Welche weiteren Informationen hätten Sie gebraucht?", "typ": "freitext"},
    {"pk": 6, "text": "In welchem Fachsemester studieren Sie?", "typ": "freitext"},
    {"pk": 7, "text": "Ich habe bereits eigenständig unterrichtet.", "typ": "likert"},
    {"pk": 8, "text": "Die Bedienung der Oberfläche fiel mir leicht.", "typ": "likert"},
    {"pk": 9, "text": "Anmerkungen zur Studie", "typ": "freitext"},
    {"pk": 10, "text": "Ich würde solche Vignetten im Studium weiterempfehlen.", "typ": "likert"},
]

_ZUORDNUNG: list[dict[str, Any]] = [
    {"pk": 1, "andockpunkt": "nach_sitzung", "position": 1},
    {"pk": 3, "andockpunkt": "nach_sitzung", "position": 2},
    {"pk": 4, "andockpunkt": "nach_sitzung", "position": 3},
    {"pk": 6, "andockpunkt": "am_ende", "position": 1},
    {"pk": 7, "andockpunkt": "am_ende", "position": 2},
    {"pk": 9, "andockpunkt": "am_ende", "position": 3},
]

VARIANTEN: dict[str, str] = {
    "A": "Zwei Andockpunkt-Bereiche",
    "B": "Eine Bibliothek, zwei Körbe",
    "C": "Eine Zuordnungstabelle",
}


def kontext(variante: str | None) -> dict[str, Any]:
    """Baut den Prototyp-Kontext; ohne gültige Variante bleibt der Prototyp aus."""

    if variante not in VARIANTEN:
        return {}
    zugeordnet: list[dict[str, Any]] = [
        {**next(item for item in _BIBLIOTHEK if item["pk"] == eintrag["pk"]), **eintrag}
        for eintrag in _ZUORDNUNG
    ]
    zugeordnete_pks: set[int] = {eintrag["pk"] for eintrag in _ZUORDNUNG}
    return {
        "prototyp_variante": variante,
        "prototyp_variantenname": VARIANTEN[variante],
        "prototyp_varianten": list(VARIANTEN),
        "prototyp_bibliothek": [
            item for item in _BIBLIOTHEK if item["pk"] not in zugeordnete_pks
        ],
        "prototyp_zugeordnet": zugeordnet,
    }

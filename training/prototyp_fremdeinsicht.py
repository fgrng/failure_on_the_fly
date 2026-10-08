"""PROTOTYP (#362), Wegwerfcode auf `prototype/fremdeinsicht-ui`, nie nach main.

Plan, je Element eine Zeile:
- Fremdeinsicht-Tabelle: drei Varianten auf `training:kuratieren`, umschaltbar über `?variant=`.
  Runde 3 (G/H/I): Punkte stehen, offen sind Grösse und Tooltip.
- Trainings-Link-Block und Export-Knopf: reisen mit denselben drei Varianten der Kuratierseite.
- Freigabe einer Abschrift: drei Varianten auf `training:abschrift`, umschaltbar über `?variant=`.
- Fester Hinweis zur Fremdeinsicht: zwei Varianten auf `training:detail`.

Alle Daten sind Stubs im Speicher. Sie kommen nur bei `DEBUG` und gesetztem
`?variant=` in den Kontext. Schalter: `leer=1` (leeres Training, nur
Abschriften), `gesperrt=1` (Beitritt gesperrt), `schritt=1` (Freigabe C).
"""

from django.conf import settings
from django.http import HttpRequest

VARIANTEN: dict[str, list[tuple[str, str]]] = {
    # Runde 1 (A/B/C) in f3532dc, Runde 2 (D/E/F) in 59ebe93.
    # Runde 3: Punkte aus F; offen sind Punktgrösse und Tooltip.
    "kuratieren": [
        ("G", "Punkt 1rem, dunkle Pille mit Datum"),
        ("H", "Punkt wächst beim Zeigen, helle Karte mit Nummer"),
        ("I", "Kreis mit Tageszahl, Pille mit vollem Datum"),
    ],
    "abschrift": [
        ("A", "Checkbox-Liste unten"),
        ("B", "Zeile je Training mit Schalter, oben"),
        ("C", "Eigener Schritt aus dem Kopf"),
    ],
    "detail": [
        ("A", "Hinweis als Kasten"),
        ("B", "Hinweis im Seitenkopf"),
    ],
}

SCHALTER: dict[str, list[tuple[str, str]]] = {
    "kuratieren": [("leer", "leeres Training"), ("gesperrt", "Beitritt gesperrt")],
    "abschrift": [("schritt", "Freigabe-Schritt offen (C)")],
    "detail": [],
}

_VIGNETTEN: list[str] = [
    "Bruchrechnen: Erweitern und Kürzen bei ungleichen Nennern",
    "Gleichungen lösen (LU11)",
    "Negative Zahlen am Zahlenstrahl",
    "Prozentrechnung im Alltag: Rabatt und Mehrwertsteuer",
    "Flächeninhalt zusammengesetzter Figuren",
    "Terme vereinfachen",
    "Proportionalität und Dreisatz",
    "Stellenwertsystem: Dezimalzahlen vergleichen",
]

_PERSONEN: list[str] = [
    "Anna-Lena Brändli-Oberholzer",
    "Ben Ackermann",
    "Chiara Della Valle-Schönenberger",
    "David Ivanović",
    "Elif Yılmaz",
    "Fabienne Zürcher-Hollenstein",
    "Gian-Luca Rüegg",
    "Hannah Meier",
    "Ilaria Fontana-Bärtschi",
    "Jonas Keller (Ausbilder)",
    "Kim Nguyen-Schmidhauser",
    "Leonie von Wattenwyl-Graffenried",
]

# (Person, Vignette) -> Anzahl abgeschlossener Sitzungen; fehlt = 0.
_SITZUNGEN: dict[tuple[int, int], int] = {
    (0, 0): 1,
    (0, 1): 2,
    (0, 2): 1,
    (0, 5): 1,
    (1, 0): 4,
    (1, 3): 1,
    (2, 1): 1,
    (2, 4): 1,
    (2, 6): 3,
    (2, 7): 1,
    (3, 0): 1,
    (5, 0): 1,
    (5, 1): 1,
    (5, 2): 1,
    (5, 3): 1,
    (5, 4): 1,
    (5, 5): 1,
    (5, 6): 1,
    (5, 7): 1,
    (6, 2): 2,
    (7, 1): 1,
    (7, 7): 4,
    (8, 3): 1,
    (8, 4): 1,
    (9, 0): 1,
    (9, 1): 1,
    (11, 0): 1,
    (11, 6): 1,
}

_ABSCHRIFTEN: dict[int, list[dict[str, object]]] = {
    2: [
        {
            "erhebungsname": "Diagnostische Gesprächsführung bei Fehlvorstellungen zu Brüchen, Frühjahrssemester 2026, Kohorte Sekundarstufe I",
            "importiert_am": "14.09.2026 10:42",
            "sitzungen": [
                "Brüche addieren mit verschiedenen Nennern",
                "Anteile im Kreisdiagramm",
                "Bruch als Division",
            ],
        }
    ],
    4: [
        {
            "erhebungsname": "Pilotstudie Fehlerdiagnose im Algebraunterricht — Vergleichsgruppe mit Videovignetten (Durchgang 2)",
            "importiert_am": "02.10.2026 16:05",
            "sitzungen": ["Variablen als Unbekannte", "Gleichungen lösen (LU11)"],
        }
    ],
}

_FREIGABE_TRAININGS: list[dict[str, object]] = [
    {
        "name": "Seminar Mathematikdidaktik HS 2026, Gruppe Dienstag",
        "freigegeben": True,
    },
    {
        "name": "Fehler als Lerngelegenheit: Diagnose im Fachgespräch (Blockwoche)",
        "freigegeben": True,
    },
    {"name": "Sammelanlass Erhebungsabschriften Sek I", "freigegeben": False},
    {"name": "Tutorat Algebra", "freigegeben": False},
]


def _zeilen(vignetten: list[str], leer: bool) -> list[dict[str, object]]:
    personen = _PERSONEN[:4] if leer else _PERSONEN
    zeilen: list[dict[str, object]] = []
    for p, name in sorted(enumerate(personen), key=lambda e: e[1]):
        zellen = []
        for v, vignette in enumerate(vignetten):
            anzahl = 0 if leer else _SITZUNGEN.get((p, v), 0)
            zellen.append(
                {
                    "vignette": vignette,
                    "kurz": f"V{v + 1}",
                    "sitzungen": [
                        {
                            "datum": f"{2 + i * 7 + (p + v) % 3:02d}.09.2026",
                            "url": "#",
                        }
                        for i in range(anzahl)
                    ],
                }
            )
        zeilen.append(
            {
                "name": name,
                "zellen": zellen,
                "anzahl": sum(len(z["sitzungen"]) for z in zellen),
                "bearbeitet": sum(1 for z in zellen if z["sitzungen"]),
                "abschriften": _ABSCHRIFTEN.get(p, []),
            }
        )
    return zeilen


def kontext(request: HttpRequest, seite: str) -> dict[str, object]:
    """Liefert Stubs und Variante, oder nichts außerhalb von DEBUG."""

    variante = request.GET.get("variant")
    schluessel = [k for k, _ in VARIANTEN[seite]]
    if not settings.DEBUG or variante not in schluessel:
        return {}
    leer = request.GET.get("leer") == "1"
    vignetten = [] if leer else _VIGNETTEN
    zeilen = _zeilen(vignetten, leer)
    return {
        "prototyp": {
            "seite": seite,
            "variante": variante,
            "template": f"training/prototyp/{seite}_{variante}.html",
            "varianten": VARIANTEN[seite],
            "name": dict(VARIANTEN[seite])[variante],
            "schalter": [
                (k, label, request.GET.get(k) == "1") for k, label in SCHALTER[seite]
            ],
            "leer": leer,
            "gesperrt": request.GET.get("gesperrt") == "1",
            "schritt": request.GET.get("schritt") == "1",
            "link": "https://fotf.phsg.ch/training/beitreten/7f3c2a9e-1b4d-4e8a-9c51-0d2e6f8a3b17/",
            "vignetten": [
                {"name": n, "kurz": f"V{i + 1}"} for i, n in enumerate(vignetten)
            ],
            "zeilen": zeilen,
            "ohne_sitzung": [
                z for z in zeilen if not z["anzahl"] and not z["abschriften"]
            ],
            "mit_abschrift": [z for z in zeilen if z["abschriften"]],
            "trainings": _FREIGABE_TRAININGS,
            "freigegeben": [t for t in _FREIGABE_TRAININGS if t["freigegeben"]],
        }
    }

"""Tests für scripts/evalgespraech.py und scripts/urteile_zaehlen.py (ohne Modellaufruf)."""

import json
from pathlib import Path

import pytest

from scripts.evalgespraech import Eingabefehler, eingaben_bilden, inputs_lesen, kuerzel
from scripts.urteile_zaehlen import ordner_lesen, uebersicht, urteile_sammeln

EVAL: str = """# Eval 9: Test

## name

Test

## kriterien

1. Eins: Erfüllt, wenn … Nicht erfüllt, wenn …

## inputs

### Evalinput A: zwei feste

1. fest: Hallo, wie hast du die erste Aufgabe gelöst?
2. fest: Und warum darf man das so machen? Woher kennst du
   das?

### Evalinput B: gemischt

1. gelenkt: Zeige auf die auffällige Stelle im Heft.
2. fest: Warum bist du da so vorgegangen?

______________________________________________________________________

## Erwartung an den LU11-Vignetten

Nichts.
"""


def test_inputs_lesen_trennt_fest_und_gelenkt_und_fuegt_umbrueche_zusammen() -> None:
    inputs = inputs_lesen(EVAL)
    assert list(inputs) == ["A", "B"]
    assert inputs["A"] == [
        ("fest", "Hallo, wie hast du die erste Aufgabe gelöst?"),
        ("fest", "Und warum darf man das so machen? Woher kennst du das?"),
    ]
    assert inputs["B"][0] == ("gelenkt", "Zeige auf die auffällige Stelle im Heft.")


def test_eingaben_bilden_setzt_gelenkte_der_reihe_nach_ein() -> None:
    schritte = inputs_lesen(EVAL)["B"]
    assert eingaben_bilden(schritte, ["Schau mal auf b)."]) == [
        "Schau mal auf b).",
        "Warum bist du da so vorgegangen?",
    ]
    assert eingaben_bilden(inputs_lesen(EVAL)["A"], None)[0].startswith("Hallo")


def test_eingaben_bilden_verlangt_passende_anzahl() -> None:
    with pytest.raises(Eingabefehler):
        eingaben_bilden(inputs_lesen(EVAL)["B"], None)
    with pytest.raises(Eingabefehler):
        eingaben_bilden(inputs_lesen(EVAL)["B"], ["eins", "zwei"])


def test_kuerzel() -> None:
    assert kuerzel(Path("docs/evals/eval-01-vorgehen-erfragen.md")) == "eval-01"
    assert kuerzel(Path("lu11-03-kehrwert-gliedweise.md")) == "lu11-03"


def test_ordner_lesen() -> None:
    assert ordner_lesen("2026-10-19-eval-01-a-lu11-01-2") == {
        "datum": "2026-10-19",
        "eval": "eval-01",
        "input": "a",
        "vignette": "lu11-01",
        "k": 2,
    }
    assert ordner_lesen("irgendwas") is None


def test_urteile_sammeln_und_uebersicht(tmp_path: Path) -> None:
    for k, erfuellt in ((1, True), (2, False)):
        ordner = tmp_path / f"2026-10-19-eval-01-a-lu11-01-{k}"
        ordner.mkdir()
        (ordner / "kriterium-kein-rollenbruch.txt").write_text("prompt")
        (ordner / "kriterium-e1-schritte.txt").write_text("prompt")
        (ordner / "urteil-kein-rollenbruch.json").write_text(
            json.dumps({"begruendung": "…", "erfuellt": erfuellt})
        )
    (
        tmp_path / "2026-10-19-eval-01-a-lu11-01-1" / "urteil-e1-schritte.json"
    ).write_text("kein json")
    urteile, fehlend = urteile_sammeln(tmp_path)
    assert [u["erfuellt"] for u in urteile] == [True, False]
    assert fehlend[0].startswith(
        "2026-10-19-eval-01-a-lu11-01-1/e1-schritte (kein Urteil-JSON"
    )
    assert fehlend[1] == "2026-10-19-eval-01-a-lu11-01-2/e1-schritte"
    text = uebersicht(urteile)
    assert "eval-01 a lu11-01" in text
    assert "kein-rollenbruch: 1/2  <--" in text

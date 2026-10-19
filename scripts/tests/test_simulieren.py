"""Tests für das Entwicklerwerkzeug scripts/simulieren.py."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import litellm
import pytest

from scripts.simulieren import main

VIGNETTE: str = """# Vignette zum Testen

Einleitung, die nicht zur Vignette gehört.

---

## fehlermuster_beschreibung

Das Gleichheitszeichen heisst «ergibt».

## lernauftrag_text

Setze die passende Zahl ein: 5 + 7 = ___ + 6

## arbeitsheft_text

```
a) 5 + 7 = 12 + 6
```

## schuelerin_name

Elin

## schuelerin_geschlecht

weiblich

## lehrperson_name

Wyss

## lehrperson_geschlecht

männlich

## fach

Mathematik

## thema

Gleichungen

## klassenstufe

9
"""

PROMPT: str = """# Entwurf

Erläuterung mit $nicht_ersetzt.

## System-Prompt-Vorlage

```text
Du bist $schuelerin_name bei $lehrperson_anrede $lehrperson_name.
$arbeitsheft
```

## User-Prompt-Vorlage

Leer.
"""


@pytest.fixture
def dateien(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    vignette: Path = tmp_path / "vignette.md"
    vignette.write_text(VIGNETTE, encoding="utf-8")
    prompt: Path = tmp_path / "prompt.md"
    prompt.write_text(PROMPT, encoding="utf-8")
    monkeypatch.setenv("SIMULIEREN_MODELL", "openai/test")
    monkeypatch.setenv("SIMULIEREN_API_KEY", "geheim")
    monkeypatch.setenv("SIMULIEREN_API_BASE", "https://example.invalid/v1")
    monkeypatch.setenv("SIMULIEREN_PARAMETER", '{"temperature": 0.5}')
    return ["--vignette", str(vignette), "--prompt", str(prompt)]


def _antwort(inhalt: str) -> SimpleNamespace:
    # Baut eine LiteLLM-Antwort mit genau einer Auswahl.

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=inhalt), finish_reason="stop"
            )
        ]
    )


def test_nur_prompt_rendert_die_vorlage_mit_den_vignettenfeldern(
    dateien: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*dateien, "--nur-prompt"]) == 0

    assert capsys.readouterr().out == (
        "Du bist Elin bei Herr Wyss.\n"
        "<arbeitsheft>\n"
        "<arbeitsheft_text>a) 5 + 7 = 12 + 6</arbeitsheft_text>\n"
        "</arbeitsheft>\n"
    )


def test_unbekannte_ueberschrift_bricht_ab(
    dateien: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "vignette.md").write_text(
        VIGNETTE + "\n## Fach\n\nDeutsch\n", encoding="utf-8"
    )

    assert main([*dateien, "--nur-prompt"]) == 2
    assert "## Fach" in capsys.readouterr().err


def test_prompt_datei_ohne_vorlagenabschnitt_ist_ganz_die_vorlage(
    dateien: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "prompt.md").write_text("Hallo $schuelerin_name.", encoding="utf-8")

    main([*dateien, "--nur-prompt"])

    assert capsys.readouterr().out == "Hallo Elin.\n"


def test_schritt_gibt_einen_verlaufseintrag_aus(
    dateien: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        litellm,
        "completion",
        Mock(return_value=_antwort('{"denkspur": "Plan", "aeusserung": "Zwölf."}')),
    )

    assert main([*dateien, "Was steht bei a)?"]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "eingabe": "Was steht bei a)?",
        "denkspur": "Plan",
        "aeusserung": "Zwölf.",
    }


def test_verlauf_geht_mit_denkspur_an_das_modell(
    dateien: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completion: Mock = Mock(
        return_value=_antwort('{"denkspur": "Plan", "aeusserung": "Weil."}')
    )
    monkeypatch.setattr(litellm, "completion", completion)
    verlauf: Path = tmp_path / "verlauf.json"
    verlauf.write_text(
        json.dumps(
            [
                {"eingabe": "Was steht bei a)?", "denkspur": "D", "aeusserung": "12."},
                {"eingabe": "Sicher?", "aeusserung": "Ja."},
            ]
        ),
        encoding="utf-8",
    )

    main([*dateien, "--verlauf", f"@{verlauf}", "Warum?"])

    assert [
        (nachricht["role"], nachricht["content"])
        for nachricht in completion.call_args.kwargs["messages"][1:]
    ] == [
        ("user", "Was steht bei a)?"),
        ("assistant", '{"denkspur": "D", "aeusserung": "12."}'),
        ("user", "Sicher?"),
        ("assistant", '{"denkspur": "", "aeusserung": "Ja."}'),
        ("user", "Warum?"),
    ]


def test_umgebungsvariablen_gehen_an_litellm(
    dateien: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    completion: Mock = Mock(
        return_value=_antwort('{"denkspur": "Plan", "aeusserung": "Zwölf."}')
    )
    monkeypatch.setattr(litellm, "completion", completion)

    main([*dateien, "Was steht bei a)?"])

    aufruf: dict[str, object] = completion.call_args.kwargs
    assert (
        aufruf["model"],
        aufruf["api_key"],
        aufruf["api_base"],
        aufruf["temperature"],
    ) == ("openai/test", "geheim", "https://example.invalid/v1", 0.5)


def test_formatbruch_meldet_die_rohantwort(
    dateien: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(litellm, "completion", Mock(return_value=_antwort("kein JSON")))

    assert main([*dateien, "Was steht bei a)?"]) == 1
    assert "kein JSON" in capsys.readouterr().err


def test_fehlendes_modell_bricht_ab(
    dateien: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SIMULIEREN_MODELL", "")

    assert main([*dateien, "Was steht bei a)?"]) == 2
    assert "SIMULIEREN_MODELL" in capsys.readouterr().err

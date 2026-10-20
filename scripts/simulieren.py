"""Spielt einen Gesprächsschritt mit der simulierten Schüler:in ohne App durch.

Liest eine Vignette und einen System-Prompt aus Markdown-Dateien, rendert den
Prompt wie die App und fragt das Sprachmodell aus den Umgebungsvariablen. Das
Skript ist zustandslos: Den bisherigen Verlauf übergibt `--verlauf`, und die
Ausgabe ist ein Verlaufseintrag, den man für den nächsten Schritt anhängt.

Beispiel:

    uv run scripts/simulieren.py \\
        --vignette docs/vignetten/lu11-01-gleichheitszeichen-als-rechenaufforderung.md \\
        --prompt docs/simulation_prompts/2026-10-20-systemprompt.md \\
        --verlauf @verlauf.json \\
        "Was hast du bei a) gerechnet?"

Aufruf, Formate und Umgebungsvariablen: docs/agents/simulieren.md.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

WURZEL: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from dotenv import load_dotenv  # noqa: E402

from simulation import SPRACHMODELL_FRIST_SEKUNDEN, vorlage_rendern  # noqa: E402
from simulation.sprachmodell import (  # noqa: E402
    SCHUELERIN_SCHEMA,
    Anbieterfehler,
    ContentFilter,
    Formatbruch,
    LiteLLMSprachmodell,
)
from vignetten.prompt import prompt_platzhalter, rahmen_platzhalter  # noqa: E402

# Die Felder einer Vignette, wie sie in der Datenbank heissen.
VIGNETTENFELDER: tuple[str, ...] = (
    "fehlermuster_beschreibung",
    "lernauftrag_text",
    "lernauftrag_bild",
    "lernauftrag_bildbeschreibung",
    "lernauftrag_simulationshinweise",
    "arbeitsheft_text",
    "arbeitsheft_bild",
    "arbeitsheft_bildbeschreibung",
    "arbeitsheft_simulationshinweise",
    "schuelerin_name",
    "schuelerin_geschlecht",
    "lehrperson_name",
    "lehrperson_geschlecht",
    "fach",
    "thema",
    "klassenstufe",
    "referenzdiagnose",
    "budget_typ",
    "budget_wert",
)

_UEBERSCHRIFT: re.Pattern[str] = re.compile(r"^## (.+?)[ \t]*$", re.MULTILINE)
_CODEBLOCK: re.Pattern[str] = re.compile(r"\A```[^\n]*\n(.*)\n```\Z", re.DOTALL)
_SYSTEM_PROMPT_VORLAGE: re.Pattern[str] = re.compile(
    r"^## System-Prompt-Vorlage\s*\n+```text\n(.*?)\n```", re.DOTALL | re.MULTILINE
)


class Eingabefehler(Exception):
    """Eine Datei, ein Argument oder eine Umgebungsvariable passt nicht."""


def vignette_lesen(text: str) -> dict[str, str]:
    """Liest die Felder einer Vignette aus Markdown.

    Jede `##`-Überschrift ist ein Feldname; ihr Abschnitt bis zur nächsten
    Überschrift ist der Wert. Besteht ein Abschnitt nur aus einem Codeblock,
    zählt dessen Inhalt. Fehlende Abschnitte sind leere Felder; Text vor der
    ersten Überschrift ist Einleitung.
    """

    felder: dict[str, str] = dict.fromkeys(VIGNETTENFELDER, "")
    teile: list[str] = _UEBERSCHRIFT.split(text)
    for name, abschnitt in zip(teile[1::2], teile[2::2], strict=True):
        if name not in felder:
            raise Eingabefehler(f"Unbekannte Überschrift in der Vignette: ## {name}")
        wert: str = abschnitt.strip()
        if codeblock := _CODEBLOCK.match(wert):
            wert = codeblock.group(1)
        felder[name] = wert
    return felder


def vorlage_lesen(text: str) -> str:
    """Liest die System-Prompt-Vorlage aus einer Prompt-Datei.

    Steht ein ```` ```text ````-Block unter `## System-Prompt-Vorlage`, ist er
    die Vorlage; sonst die ganze Datei.
    """

    if treffer := _SYSTEM_PROMPT_VORLAGE.search(text):
        return treffer.group(1)
    return text


def system_prompt_rendern(vorlage: str, felder: dict[str, str]) -> str:
    """Setzt die Platzhalter der Vignette in die Vorlage ein."""

    vignette: SimpleNamespace = SimpleNamespace(**felder)
    platzhalter: dict[str, str] = {
        **rahmen_platzhalter(vignette),
        **prompt_platzhalter(vignette),
    }
    try:
        return vorlage_rendern(vorlage, platzhalter)
    except KeyError as exc:
        raise Eingabefehler(f"Unbekannter Platzhalter in der Vorlage: ${exc}") from exc
    except ValueError as exc:
        raise Eingabefehler(f"Ungültiger Platzhalter in der Vorlage: {exc}") from exc


def verlauf_lesen(wert: str) -> list[tuple[str, str]]:
    """Liest den Verlauf als JSON-Liste von Schritten.

    Ein Schritt ist `{"eingabe": …, "denkspur": …, "aeusserung": …}`; die
    Denkspur ist optional. Beginnt der Wert mit `@`, ist der Rest ein
    Dateipfad.
    """

    if wert.startswith("@"):
        wert = Path(wert[1:]).read_text(encoding="utf-8")
    schritte: object = json.loads(wert)
    if not isinstance(schritte, list):
        raise Eingabefehler("--verlauf muss eine JSON-Liste sein.")
    verlauf: list[tuple[str, str]] = []
    for schritt in schritte:
        if not isinstance(schritt, dict) or not {"eingabe", "aeusserung"} <= set(
            schritt
        ):
            raise Eingabefehler(
                "Jeder Verlaufsschritt braucht «eingabe» und «aeusserung»."
            )
        # So, wie die App frühere Antworten dem Modell zeigt (ADR-0064).
        ausgabe: str = json.dumps(
            {
                "denkspur": schritt.get("denkspur", ""),
                "aeusserung": schritt["aeusserung"],
            },
            ensure_ascii=False,
        )
        verlauf.append((schritt["eingabe"], ausgabe))
    return verlauf


def sprachmodell_aus_umgebung() -> LiteLLMSprachmodell:
    """Bildet den LiteLLM-Adapter aus den `SIMULIEREN_*`-Umgebungsvariablen."""

    modell: str = os.environ.get("SIMULIEREN_MODELL", "")
    api_key: str = os.environ.get("SIMULIEREN_API_KEY", "")
    if not modell or not api_key:
        raise Eingabefehler(
            "SIMULIEREN_MODELL und SIMULIEREN_API_KEY müssen gesetzt sein "
            "(in .env oder der Umgebung)."
        )
    parameter: dict[str, Any] = json.loads(
        os.environ.get("SIMULIEREN_PARAMETER", "") or "{}"
    )
    parameter["api_key"] = api_key
    if api_base := os.environ.get("SIMULIEREN_API_BASE", ""):
        parameter["api_base"] = api_base
    return LiteLLMSprachmodell(modell, parameter)


def main(argumente: list[str] | None = None) -> int:
    """Führt einen Gesprächsschritt aus und gibt ihn als JSON aus."""

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Spielt einen Gesprächsschritt mit der simulierten Schüler:in."
    )
    parser.add_argument("--vignette", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument(
        "--verlauf",
        default="[]",
        help="JSON-Liste bisheriger Schritte oder @pfad.json",
    )
    parser.add_argument(
        "--nur-prompt",
        action="store_true",
        help="Gibt nur den gerenderten System-Prompt aus, ohne Modellaufruf.",
    )
    parser.add_argument("eingabe", nargs="?", help="Die Äusserung der Lehrperson.")
    args: argparse.Namespace = parser.parse_args(argumente)

    load_dotenv(WURZEL / ".env")
    try:
        system_prompt: str = system_prompt_rendern(
            vorlage_lesen(args.prompt.read_text(encoding="utf-8")),
            vignette_lesen(args.vignette.read_text(encoding="utf-8")),
        )
        if args.nur_prompt:
            print(system_prompt)
            return 0
        if not args.eingabe:
            raise Eingabefehler("Die Eingabe fehlt.")
        verlauf: list[tuple[str, str]] = verlauf_lesen(args.verlauf)
        sprachmodell: LiteLLMSprachmodell = sprachmodell_aus_umgebung()
    except (Eingabefehler, OSError, json.JSONDecodeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2

    try:
        ausgabe: dict[str, object] = sprachmodell.antworten(
            system_prompt,
            verlauf,
            args.eingabe,
            SCHUELERIN_SCHEMA,
            SPRACHMODELL_FRIST_SEKUNDEN,
        )
    except (Formatbruch, Anbieterfehler, ContentFilter) as exc:
        print(f"{type(exc).__name__}: {exc.__cause__ or ''}", file=sys.stderr)
        if exc.rohantwort:
            print(f"Rohantwort:\n{exc.rohantwort}", file=sys.stderr)
        return 1

    schritt: dict[str, object] = {"eingabe": args.eingabe, **ausgabe}
    print(json.dumps(schritt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Spielt einen Evalinput k-mal mit der simulierten Schüler:in durch, ohne App.

Für das Durchspielen eines Evals ohne App (docs/evals/README.md): Die festen
Inputschritte kommen wörtlich aus der Eval-Datei, die gelenkten aus einer
JSON-Datei mit vorformulierten Äusserungen der Lehrperson je Vignette. Jeder
Schritt geht an das Modell aus den `SIMULIEREN_*`-Umgebungsvariablen
(scripts/simulieren.py); der fertige Verlauf landet als JSON-Liste von
Schritten (`eingabe`, `denkspur`, `aeusserung`) im Zielverzeichnis.

Beispiel:

    uv run scripts/evalgespraech.py \\
        --vignette docs/vignetten/lu11-01-gleichheitszeichen-als-rechenaufforderung.md \\
        --eval docs/evals/eval-01-vorgehen-erfragen.md --input B \\
        --prompt docs/simulation_prompts/2026-10-20-systemprompt.md \\
        --gelenkt docs/evals/probelaeufe/2026-10-19-gelenkte-schritte.json

Schreibt `docs/evals/probelaeufe/<datum>-eval-01-b-lu11-01-<k>.json` für
k = 1 bis 3 und überspringt Dateien, die schon da sind. Die Datei für
`--gelenkt` ist ein Objekt `{"eval-01-b": {"lu11-01": ["…", "…"]}}` mit den
Äusserungen der gelenkten Schritte in ihrer Reihenfolge; Evalinputs ohne
gelenkte Schritte brauchen sie nicht.
"""

import argparse
import datetime
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WURZEL: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from dotenv import load_dotenv  # noqa: E402

from simulation import SPRACHMODELL_FRIST_SEKUNDEN  # noqa: E402
from simulation.sprachmodell import (  # noqa: E402
    SCHUELERIN_SCHEMA,
    Anbieterfehler,
    ContentFilter,
    Formatbruch,
    LiteLLMSprachmodell,
)
from simulieren import (  # noqa: E402
    Eingabefehler,
    sprachmodell_aus_umgebung,
    system_prompt_rendern,
    verlauf_lesen,
    vignette_lesen,
    vorlage_lesen,
)

PROBELAEUFE: Path = WURZEL / "docs" / "evals" / "probelaeufe"

_KUERZEL: re.Pattern[str] = re.compile(r"^([a-z0-9]+-\d+)")


def kuerzel(pfad: Path) -> str:
    """Macht aus `eval-01-vorgehen-erfragen.md` das Kürzel `eval-01`, aus `lu11-01-…` `lu11-01`."""

    treffer: re.Match[str] | None = _KUERZEL.match(pfad.stem)
    if treffer is None:
        raise Eingabefehler(f"Kein Kürzel am Anfang von «{pfad.name}».")
    return treffer.group(1)


def inputs_lesen(text: str) -> dict[str, list[tuple[str, str]]]:
    """Liest `## inputs` als {Buchstabe: [(art, text), …]} mit art `fest` oder `gelenkt`."""

    treffer: re.Match[str] | None = re.search(
        r"^## inputs\s*\n(.*?)(?=^## |^_{3,}|^---|\Z)", text, re.DOTALL | re.MULTILINE
    )
    if treffer is None:
        raise Eingabefehler("Abschnitt «## inputs» fehlt.")
    inputs: dict[str, list[tuple[str, str]]] = {}
    for abschnitt in re.split(r"^### Evalinput ", treffer.group(1), flags=re.MULTILINE)[
        1:
    ]:
        kopf, _, rest = abschnitt.partition("\n")
        buchstabe: str = kopf.split(":", 1)[0].strip().upper()
        schritte: list[tuple[str, str]] = []
        for punkt in re.split(r"\n(?=\d+\. )", rest.strip()):
            satz: str = re.sub(r"\s+", " ", re.sub(r"^\d+\.\s*", "", punkt.strip()))
            if not satz:
                continue
            art, _, inhalt = satz.partition(":")
            if art not in ("fest", "gelenkt"):
                raise Eingabefehler(
                    f"Inputschritt ohne «fest:» oder «gelenkt:»: {satz[:60]}"
                )
            schritte.append((art, inhalt.strip()))
        inputs[buchstabe] = schritte
    return inputs


def eingaben_bilden(
    schritte: list[tuple[str, str]], gelenkte: list[str] | None
) -> list[str]:
    """Setzt feste Texte wörtlich ein und nimmt gelenkte der Reihe nach aus `gelenkte`."""

    noetig: int = sum(1 for art, _ in schritte if art == "gelenkt")
    if noetig and (gelenkte is None or len(gelenkte) != noetig):
        raise Eingabefehler(
            f"{noetig} gelenkte Schritte, aber {len(gelenkte or [])} Äusserungen in --gelenkt."
        )
    rest: list[str] = list(gelenkte or [])
    return [text if art == "fest" else rest.pop(0) for art, text in schritte]


def gespraech_fuehren(
    sprachmodell: LiteLLMSprachmodell, system_prompt: str, eingaben: list[str]
) -> list[dict[str, object]]:
    """Spielt die Eingaben nacheinander durch und gibt den Verlauf zurück."""

    verlauf: list[dict[str, object]] = []
    for eingabe in eingaben:
        ausgabe: dict[str, object] = sprachmodell.antworten(
            system_prompt,
            verlauf_lesen(json.dumps(verlauf, ensure_ascii=False)),
            eingabe,
            SCHUELERIN_SCHEMA,
            SPRACHMODELL_FRIST_SEKUNDEN,
        )
        verlauf.append({"eingabe": eingabe, **ausgabe})
    return verlauf


def main(argumente: list[str] | None = None) -> int:
    """Spielt den Evalinput k-mal durch und schreibt je Wiederholung eine Datei."""

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--vignette", required=True, type=Path)
    parser.add_argument("--eval", required=True, type=Path, dest="eval_pfad")
    parser.add_argument(
        "--input", required=True, help="Buchstabe des Evalinputs, etwa A"
    )
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument(
        "--gelenkt", type=Path, help="JSON mit den gelenkten Äusserungen"
    )
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--ziel", type=Path, default=PROBELAEUFE)
    parser.add_argument("--datum", default=datetime.date.today().isoformat())
    args = parser.parse_args(argumente)

    load_dotenv(WURZEL / ".env")
    try:
        buchstabe: str = args.input.upper()
        inputs = inputs_lesen(args.eval_pfad.read_text(encoding="utf-8"))
        if buchstabe not in inputs:
            raise Eingabefehler(
                f"Evalinput {buchstabe} fehlt; vorhanden: {', '.join(inputs)}."
            )
        name: str = (
            f"{kuerzel(args.eval_pfad)}-{buchstabe.lower()}-{kuerzel(args.vignette)}"
        )
        gelenkte: list[str] | None = None
        if args.gelenkt is not None:
            alle = json.loads(args.gelenkt.read_text(encoding="utf-8"))
            gelenkte = alle.get(
                f"{kuerzel(args.eval_pfad)}-{buchstabe.lower()}", {}
            ).get(kuerzel(args.vignette))
        eingaben: list[str] = eingaben_bilden(inputs[buchstabe], gelenkte)
        system_prompt: str = system_prompt_rendern(
            vorlage_lesen(args.prompt.read_text(encoding="utf-8")),
            vignette_lesen(args.vignette.read_text(encoding="utf-8")),
        )
        sprachmodell: LiteLLMSprachmodell = sprachmodell_aus_umgebung()
    except (Eingabefehler, OSError, json.JSONDecodeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2

    args.ziel.mkdir(parents=True, exist_ok=True)

    def wiederholung(k: int) -> str:
        ziel: Path = args.ziel / f"{args.datum}-{name}-{k}.json"
        if ziel.exists():
            return f"übersprungen {ziel.name}"
        try:
            verlauf = gespraech_fuehren(sprachmodell, system_prompt, eingaben)
        except (Formatbruch, Anbieterfehler, ContentFilter) as exc:
            return f"FEHLER {ziel.name}: {type(exc).__name__}: {exc.__cause__ or ''}"
        ziel.write_text(
            json.dumps(verlauf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return f"fertig {ziel.name}"

    fehler: int = 0
    with ThreadPoolExecutor(max_workers=args.k) as pool:
        for meldung in pool.map(wiederholung, range(1, args.k + 1)):
            print(meldung, flush=True)
            fehler += meldung.startswith("FEHLER")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())

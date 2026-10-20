"""Zählt die Urteile eines Probelaufs aus: je Eval, Input, Vignette und Kriterium erfüllt/n.

Für das Durchspielen eines Evals ohne App (docs/evals/README.md): Unter dem
Bewerter-Verzeichnis liegt je Evalgespräch ein Ordner
`<datum>-<eval>-<input>-<vignette>-<k>` mit den gerenderten Prompts
`kriterium-<kennung>.txt` und den Urteilen `urteil-<kennung>.json`
(`{"begruendung": …, "erfuellt": …}`). Das Skript sammelt alle Urteile in eine
JSON-Liste, druckt eine Übersicht mit pass^k je Kriterium und nennt, welche
Urteile noch fehlen oder kein JSON sind.

Beispiel:

    uv run scripts/urteile_zaehlen.py --bewerter /tmp/bewerter \\
        --ziel docs/evals/probelaeufe/2026-10-19-urteile.json
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_ORDNER: re.Pattern[str] = re.compile(
    r"^(?P<datum>\d{4}-\d{2}-\d{2})-(?P<eval>eval-\d+)-(?P<input>[a-z])-(?P<vignette>.+)-(?P<k>\d+)$"
)


def ordner_lesen(name: str) -> dict[str, object] | None:
    """Zerlegt `2026-10-19-eval-01-a-lu11-01-2` in Datum, Eval, Input, Vignette und k."""

    treffer: re.Match[str] | None = _ORDNER.match(name)
    if treffer is None:
        return None
    felder: dict[str, object] = dict(treffer.groupdict())
    felder["k"] = int(treffer.group("k"))
    return felder


def urteile_sammeln(bewerter: Path) -> tuple[list[dict[str, object]], list[str]]:
    """Liest alle Urteile unter `bewerter`; gibt (Urteile, fehlende Kennungen) zurück."""

    urteile: list[dict[str, object]] = []
    fehlend: list[str] = []
    for ordner in sorted(p for p in bewerter.iterdir() if p.is_dir()):
        kopf = ordner_lesen(ordner.name)
        if kopf is None:
            continue
        for prompt in sorted(ordner.glob("kriterium-*.txt")):
            kennung: str = prompt.stem[len("kriterium-") :]
            urteil: Path = ordner / f"urteil-{kennung}.json"
            if not urteil.exists():
                fehlend.append(f"{ordner.name}/{kennung}")
                continue
            try:
                daten = json.loads(urteil.read_text(encoding="utf-8"))
                erfuellt: bool = bool(daten["erfuellt"])
                begruendung: str = str(daten["begruendung"])
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                fehlend.append(f"{ordner.name}/{kennung} (kein Urteil-JSON: {exc})")
                continue
            urteile.append(
                {
                    **kopf,
                    "kennung": kennung,
                    "erfuellt": erfuellt,
                    "begruendung": begruendung,
                }
            )
    return urteile, fehlend


def uebersicht(urteile: list[dict[str, object]]) -> str:
    """Formatiert erfüllt/n je Eval, Input, Vignette und Kennung; `<--` markiert nicht bestanden."""

    zaehler: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for u in urteile:
        schluessel = (u["eval"], u["input"], u["vignette"], u["kennung"])
        zaehler[schluessel][1] += 1
        zaehler[schluessel][0] += int(bool(u["erfuellt"]))
    zeilen: list[str] = []
    letzter: tuple | None = None
    for (eval_, inp, vignette, kennung), (ja, n) in sorted(zaehler.items()):
        if (eval_, inp, vignette) != letzter:
            zeilen.append(f"\n{eval_} {inp} {vignette}")
            letzter = (eval_, inp, vignette)
        zeilen.append(f"  {kennung}: {ja}/{n}{'' if ja == n else '  <--'}")
    return "\n".join(zeilen).lstrip("\n")


def main(argumente: list[str] | None = None) -> int:
    """Sammelt, zählt und schreibt die Urteile."""

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--bewerter", required=True, type=Path)
    parser.add_argument(
        "--ziel", type=Path, help="Sammel-JSON aller Urteile (optional)"
    )
    args = parser.parse_args(argumente)

    urteile, fehlend = urteile_sammeln(args.bewerter)
    if args.ziel is not None:
        args.ziel.write_text(
            json.dumps(urteile, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    print(uebersicht(urteile))
    print(f"\n{len(urteile)} Urteile, {len(fehlend)} fehlend")
    for eintrag in fehlend:
        print(f"  fehlt: {eintrag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

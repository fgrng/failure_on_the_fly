"""Rendert die Bewerter-Vorlage aus docs/evals/katalog.md je Kriterium (übergreifende Kriterien aus
docs/evals/allgemeine_kriterien.md), ohne Modellaufruf.

Für das Durchspielen eines Evals ohne App (docs/evals/README.md): Der Verlauf
eines Evalgesprächs liegt als JSON-Liste von Schritten aus
`scripts/simulieren.py` vor; dieses Skript rendert daraus je übergreifendem
Kriterium und je Evalkriterium den vollständigen Prompt an den Bewerter, so
wie ihn der Evallauf schicken würde. Die Prompts beurteilt dann ein Mensch
oder ein Agent in der Bewerterrolle.

Beispiel:

    uv run scripts/bewerter_prompt.py \\
        --vignette docs/vignetten/lu11-01-gleichheitszeichen-als-rechenaufforderung.md \\
        --eval docs/evals/eval-02-neue-aufgabe.md \\
        --verlauf verlauf.json \\
        --ziel /tmp/bewerter

Schreibt je Kriterium `kriterium-<kennung>.txt` in das Zielverzeichnis, die
übergreifenden Kriterien zuerst, und listet sie auf stdout. Die Kennung ist der
Name des Kriteriums als Slug, bei Evalkriterien mit `e<N>-` davor; sie bleibt
stabil, wenn Kriterien die Position wechseln.
"""

import argparse
import json
import re
import sys
from pathlib import Path

WURZEL: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from simulieren import system_prompt_rendern, vignette_lesen  # noqa: E402

KATALOG: Path = WURZEL / "docs" / "evals" / "katalog.md"
ALLGEMEINE_KRITERIEN: Path = WURZEL / "docs" / "evals" / "allgemeine_kriterien.md"

_VORLAGE: re.Pattern[str] = re.compile(
    r"^## bewerter_vorlage\s*\n+```text\n(.*?)\n```", re.DOTALL | re.MULTILINE
)


_UMLAUTE: dict[int, str] = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def kennung(name: str) -> str:
    """Macht aus «Kein ungefragtes Verraten» den Slug `kein-ungefragtes-verraten`."""

    return re.sub(r"[^a-z0-9]+", "-", name.lower().translate(_UMLAUTE)).strip("-")


def kriterien_lesen(text: str, feld: str) -> list[tuple[str, str]]:
    """Liest die nummerierte Liste unter `## feld` als (Kennung, Kriterium) je Punkt.

    Der Kurztitel vor dem Doppelpunkt gibt die Kennung `e<N>-<slug>`; die Nummer
    der Liste geht nicht an den Bewerter.
    """

    treffer: re.Match[str] | None = re.search(
        rf"^## {feld}\s*\n(.*?)(?=^## |^---|\Z)", text, re.DOTALL | re.MULTILINE
    )
    if treffer is None:
        raise SystemExit(f"Abschnitt «## {feld}» fehlt.")
    kriterien: list[tuple[str, str]] = []
    for punkt in re.split(r"\n(?=\d+\. )", treffer.group(1).strip()):
        kriterium: str = re.sub(r"^\d+\.\s*", "", re.sub(r"\s+", " ", punkt.strip()))
        if not kriterium:
            continue
        titel: str = kriterium.split(":", 1)[0]
        kriterien.append((f"e{len(kriterien) + 1}-{kennung(titel)}", kriterium))
    return kriterien


def allgemeine_kriterien_lesen(text: str) -> list[tuple[str, str]]:
    """Liest `# Name` mit `## Beschreibung` als (Kennung, «Name: Beschreibung»).

    `## Hintergrund` und alles andere geht nicht an den Bewerter.
    """

    kriterien: list[tuple[str, str]] = []
    for abschnitt in re.split(r"^# (?=\S)", text, flags=re.MULTILINE)[1:]:
        name, _, rest = abschnitt.partition("\n")
        treffer: re.Match[str] | None = re.search(
            r"^## Beschreibung\s*\n(.*?)(?=^## |\Z)", rest, re.DOTALL | re.MULTILINE
        )
        if treffer is None or not treffer.group(1).strip():
            raise SystemExit(f"Kriterium «{name.strip()}» hat keine Beschreibung.")
        kriterien.append(
            (
                kennung(name),
                f"{name.strip()}: {re.sub(r'\s+', ' ', treffer.group(1).strip())}",
            )
        )
    return kriterien


def verlauf_rendern(schritte: list[dict[str, str]]) -> str:
    """Rendert den Verlauf so, wie der Evallauf ihn dem Bewerter zeigt."""

    return "\n".join(
        f"<lehrperson>{schritt['eingabe']}</lehrperson>\n"
        f"<denkspur>{schritt.get('denkspur', '')}</denkspur>\n"
        f"<schuelerin>{schritt['aeusserung']}</schuelerin>"
        for schritt in schritte
    )


def main(argumente: list[str] | None = None) -> int:
    """Rendert je Kriterium eine Datei ins Zielverzeichnis."""

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--vignette", required=True, type=Path)
    parser.add_argument("--eval", required=True, type=Path, dest="eval_pfad")
    parser.add_argument("--verlauf", required=True, type=Path)
    parser.add_argument("--ziel", required=True, type=Path)
    args = parser.parse_args(argumente)

    katalog: str = KATALOG.read_text(encoding="utf-8")
    vorlage_treffer: re.Match[str] | None = _VORLAGE.search(katalog)
    if vorlage_treffer is None:
        raise SystemExit("Die Bewerter-Vorlage fehlt in docs/evals/katalog.md.")
    vorlage: str = vorlage_treffer.group(1)

    kriterien: list[tuple[str, str]] = allgemeine_kriterien_lesen(
        ALLGEMEINE_KRITERIEN.read_text(encoding="utf-8")
    )
    kriterien += kriterien_lesen(
        args.eval_pfad.read_text(encoding="utf-8"), "kriterien"
    )
    felder: dict[str, str] = vignette_lesen(args.vignette.read_text(encoding="utf-8"))
    verlauf: str = verlauf_rendern(json.loads(args.verlauf.read_text(encoding="utf-8")))

    args.ziel.mkdir(parents=True, exist_ok=True)
    for kennung_, kriterium in kriterien:
        # Kriterium und Verlauf sind Werte, keine Vorlagen: Sie werden vor dem
        # Rendern eingesetzt, damit ein «$» darin kein Platzhalter wird.
        text: str = system_prompt_rendern(
            vorlage.replace("$kriterium", kriterium).replace("$verlauf", verlauf),
            felder,
        )
        (args.ziel / f"kriterium-{kennung_}.txt").write_text(text, encoding="utf-8")
        print(f"kriterium-{kennung_}.txt  {kriterium[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Modelle und Abläufe der Simulation."""

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from string import Template
from typing import TYPE_CHECKING

from simulation.sprachmodell import (
    SCHUELERIN_SCHEMA,
    Anbieterfehler,
    ContentFilter,
    FakeSprachmodell,
    Formatbruch,
    LiteLLMSprachmodell,
    Sprachmodell,
)

if TYPE_CHECKING:
    from simulation.models import ModellKonfiguration, Simulationskern


MAX_VERSUCHE: int = 3

# Wie lange ein Gesprächsschritt höchstens auf das Sprachmodell warten darf —
# alle Versuche eines Schritts teilen sich diese Frist, jeder einzelne Aufruf
# bekommt die verbliebene Restzeit als Timeout. Das ist nicht das
# Gesprächsbudget der Vignette (ADR-0012), sondern eine Zusage dieser Naht.
#
# Nach oben begrenzt das Deployment: Das Uberspace-Frontend schließt eine
# Verbindung nach drei Minuten ohne Daten, und gunicorns Thread-Worker bricht
# eine einzelne Anfrage nicht selbst ab (docs/DEPLOYMENT.md, ADR-0050). 90 s
# lassen dazu Luft, auch wenn mehrere Versuche in dieselbe Anfrage fallen und
# der Endpunkt danach noch schreibt. Nach unten begrenzt die Denkspur, die das
# Ausgabeschema vor der Äußerung erzwingt (ADR-0005): Ein Reasoning-Modell
# liefert legitim erst nach 20-60 s. 90 s ist der schlechte Fall, nicht der
# Normalfall.
SPRACHMODELL_FRIST_SEKUNDEN: float = 90.0

# Ein Aufruf, dessen Frist schon aufgebraucht ist, bekommt noch diese Zeit,
# damit er sauber scheitert, statt mit einem Timeout von null zu hängen.
SPRACHMODELL_MINDEST_ANFRAGEFRIST_SEKUNDEN: float = 1.0

# Die datenschutzrechtliche Zusage aus ADR-0026 steht in keiner Konfiguration:
# Ein Tor, das im selben Formular abschaltbar wäre, in dem man den Anbieter
# wählt, ist keins.
OPENROUTER_PROVIDER_FILTER: dict[str, object] = {
    "require_parameters": True,
    "data_collection": "deny",
    "zdr": True,
}


@dataclass(frozen=True)
class Fehlversuch:
    """Ein maschinell verworfener Modellaufruf."""

    grund: str
    rohantwort: str


@dataclass(frozen=True)
class Ausgabeversuch:
    """Wie der Antwortversuch, nur mit dem rohen Objekt eines beliebigen Schemas."""

    # Das geparste Objekt des Ausgabeschemas; leer, wenn kein Versuch glückte.
    ausgabe: dict[str, object] | None
    fehlversuche: list[Fehlversuch]


@dataclass(frozen=True)
class Antwort:
    """Das strukturierte Ergebnis eines geglückten Antwortversuchs."""

    denkspur: str
    aeusserung: str


@dataclass(frozen=True)
class Antwortversuch:
    """Das flüchtige Ergebnis von höchstens drei Modellaufrufen."""

    antwort: Antwort | None
    fehlversuche: list[Fehlversuch]


class Ausfuehrung:
    """Eine zusammenhängende Folge von Modellaufrufen, etwa ein Evallauf.

    Ein Fake mit `skript_fortlesen` liest sein Skript innerhalb einer
    Ausführung über alle Aufrufe derselben Konfiguration fort; eine neue
    Ausführung beginnt wieder vorn.
    """

    def __init__(self) -> None:
        """Beginnt ohne Fortschritt."""

        self._fakes: dict[
            tuple[str, int], tuple["ModellKonfiguration", FakeSprachmodell]
        ] = {}

    def fake(self, modell_konfiguration: "ModellKonfiguration") -> FakeSprachmodell:
        """Liefert den fortlesenden Fake dieser Konfiguration in dieser Ausführung."""

        # Ungespeicherte Konfigurationen unterscheidet ihre Identität; gehalten
        # bleiben sie, damit Python dieselbe Identität nicht neu vergibt.
        schluessel: tuple[str, int] = (
            ("pk", modell_konfiguration.pk)
            if modell_konfiguration.pk is not None
            else ("id", id(modell_konfiguration))
        )
        if schluessel not in self._fakes:
            self._fakes[schluessel] = (
                modell_konfiguration,
                _fake_aus(modell_konfiguration),
            )
        return self._fakes[schluessel][1]


def vorlage_rendern(vorlage_text: str, platzhalter: Mapping[str, str]) -> str:
    """Setzt die in der Vorlage benutzten Platzhalter ein; übrige Werte bleiben unbenutzt."""

    return Template(vorlage_text).substitute(platzhalter)


def antwort_versuchen(
    platzhalter: Mapping[str, str],
    kern: "Simulationskern",
    modell_konfiguration: "ModellKonfiguration",
    verlauf: Sequence[tuple[str, str]],
    eingabe: str,
    ausfuehrung: Ausfuehrung | None = None,
) -> Antwortversuch:
    """Erzeugt schreibfrei eine Antwort der simulierten Schüler:in.

    Die Prompt-Platzhalter (Name → Text) berechnet die Aufruferin aus ihrer
    Vignette; `simulation` kennt keine Vignette (ADR-0016).
    """

    ausgabeversuch: Ausgabeversuch = ausgabe_versuchen(
        vorlage_rendern(kern.system_prompt_vorlage, platzhalter),
        vorlage_rendern(kern.user_prompt_vorlage, platzhalter),
        modell_konfiguration,
        verlauf,
        eingabe,
        SCHUELERIN_SCHEMA,
        ausfuehrung,
    )
    if ausgabeversuch.ausgabe is None:
        return Antwortversuch(None, ausgabeversuch.fehlversuche)
    antwort: Antwort = Antwort(
        denkspur=str(ausgabeversuch.ausgabe["denkspur"]),
        aeusserung=str(ausgabeversuch.ausgabe["aeusserung"]),
    )
    return Antwortversuch(antwort, ausgabeversuch.fehlversuche)


def ausgabe_versuchen(
    system_prompt: str,
    user_prompt: str,
    modell_konfiguration: "ModellKonfiguration",
    verlauf: Sequence[tuple[str, str]],
    eingabe: str,
    ausgabe_schema: Mapping[str, object],
    ausfuehrung: Ausfuehrung | None = None,
) -> Ausgabeversuch:
    """Erzeugt schreibfrei eine Ausgabe nach dem übergebenen Schema.

    Formatbruch, Anbieterfehler und Content-Filter werden zu Fehlversuchen;
    nach `MAX_VERSUCHE` oder abgelaufener Frist bleibt die Ausgabe leer.
    """

    sprachmodell: Sprachmodell = _sprachmodell_aus(modell_konfiguration, ausfuehrung)
    fehlversuche: list[Fehlversuch] = []
    # Die Frist steht einmal je Gesprächsschritt und gilt für alle Versuche
    # zusammen; ein hängender Anbieter frisst sie selbst auf, die Wiederholung
    # entfällt damit von allein.
    frist: float = time.monotonic() + SPRACHMODELL_FRIST_SEKUNDEN

    for _ in range(MAX_VERSUCHE):
        if time.monotonic() >= frist:
            fehlversuche.append(
                Fehlversuch(
                    "Anbieterfehler",
                    "Die Frist des Gesprächsschritts war vor dem Versuch erschöpft.",
                )
            )
            break
        try:
            ausgabe: dict[str, object] = sprachmodell.antworten(
                system_prompt,
                user_prompt,
                verlauf,
                eingabe,
                ausgabe_schema,
                _restzeit(frist),
            )
        except Formatbruch as exc:
            fehlversuche.append(Fehlversuch("Formatbruch", exc.rohantwort))
        except Anbieterfehler as exc:
            fehlversuche.append(Fehlversuch("Anbieterfehler", exc.rohantwort))
        except ContentFilter as exc:
            fehlversuche.append(Fehlversuch("Content-Filter", exc.rohantwort))
        else:
            return Ausgabeversuch(ausgabe, fehlversuche)
    return Ausgabeversuch(None, fehlversuche)


def _restzeit(frist: float) -> float:
    """Begrenzt einen einzelnen Aufruf auf das, was von der Frist übrig ist."""

    return max(frist - time.monotonic(), SPRACHMODELL_MINDEST_ANFRAGEFRIST_SEKUNDEN)


def _fake_aus(modell_konfiguration: "ModellKonfiguration") -> FakeSprachmodell:
    """Bildet den Fake aus Skript und Verzögerung der Konfiguration."""

    verzoegerung: object = modell_konfiguration.parameter.get("verzoegerung", 0)
    # Nur eine echte Zahl wartet; ein getipptes "2" oder true bleibt sofort.
    if isinstance(verzoegerung, bool) or not isinstance(verzoegerung, int | float):
        verzoegerung = 0
    return FakeSprachmodell(
        modell_konfiguration.parameter.get("skript", []), float(verzoegerung)
    )


def _sprachmodell_aus(
    modell_konfiguration: "ModellKonfiguration", ausfuehrung: Ausfuehrung | None
) -> Sprachmodell:
    """Bildet den in der Konfiguration gewählten Adapter."""

    from simulation.models import Anbieter

    if modell_konfiguration.anbieter == Anbieter.FAKE:
        # Nur ein echtes `true` schaltet ein; ein getipptes "false" bliebe sonst wahr.
        if (
            ausfuehrung is not None
            and modell_konfiguration.parameter.get("skript_fortlesen") is True
        ):
            return ausfuehrung.fake(modell_konfiguration)
        return _fake_aus(modell_konfiguration)
    aufrufparameter: dict[str, object] = dict(modell_konfiguration.parameter)
    aufrufparameter["api_key"] = modell_konfiguration.anbieter_token
    if modell_konfiguration.anbieter_basis_url:
        aufrufparameter["api_base"] = modell_konfiguration.anbieter_basis_url
    if modell_konfiguration.anbieter == Anbieter.OPENROUTER:
        aufrufparameter["extra_body"] = {"provider": OPENROUTER_PROVIDER_FILTER}
    return LiteLLMSprachmodell(modell_konfiguration.sprachmodell, aufrufparameter)

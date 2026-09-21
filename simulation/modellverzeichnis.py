"""Naht zu den Modelllisten der Anbieter: Vorschläge, nie Prüfung.

Was hier entsteht, ist ein Vorschlag und keine Gültigkeitsaussage: Die prüfende
Instanz bleibt der Probelauf (ADR-0014), die einzige Prüfung am Modellnamen
seine Anbieterbindung (ADR-0036).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import httpx

from simulation.models import ANBIETER_PROFIL, Anbieter

# Die Modellliste steht vor einem Formular, in dem jemand wartet; sie bekommt
# deshalb eine kurze Frist statt des großzügigen Budgets der Transkription.
MODELLLISTE_BUDGET_SEKUNDEN: float = 10.0

OPENROUTER_MODELLE_URL: str = (
    f"{ANBIETER_PROFIL[Anbieter.OPENROUTER].standard_basis_url}/models"
)

# Die kontoweite Liste Infomaniaks. Sie steht bewusst nicht am Profil: Dessen
# Basis-URL trägt die Produktkennung und ist beim Anlegen einer Fassung noch
# nicht getippt, diese Route dagegen kommt ohne sie aus.
INFOMANIAK_MODELLE_URL: str = "https://api.infomaniak.com/1/ai/models"


class Naht(StrEnum):
    """Die Naht, für die Modelle vorgeschlagen werden."""

    SPRACHMODELL = "sprachmodell"


@dataclass(frozen=True)
class Modellvorschlag:
    """Ein Vorschlag, anbieterfrei: fertiger Wert, roher Name, Klarname."""

    wert: str
    modellname: str
    anzeige: str


class Modellverzeichnisfehler(Exception):
    """Die Vorschlagsliste ließ sich nicht bilden."""


class KeineModellliste(Modellverzeichnisfehler):
    """Für dieses Paar aus Anbieter und Naht gibt es keine Liste."""


class AnbieterNichtErreichbar(Modellverzeichnisfehler):
    """Der Anbieter beantwortet die Anfrage nach seinen Modellen nicht."""


class AnbieterLehntAb(Modellverzeichnisfehler):
    """Der Anbieter weist die Anfrage nach seinen Modellen zurück."""


class AnbieterAntwortetFormwidrig(Modellverzeichnisfehler):
    """Die Antwort des Anbieters trägt keine lesbare Modellliste."""


class Modellverzeichnis(Protocol):
    """Liefert zu einer Naht die Vorschlagsliste eines Anbieters."""

    def vorschlaege(self, naht: str) -> list[Modellvorschlag]:
        """Liefert die alphabetisch sortierten Vorschläge dieser Naht."""


# Welche Abfrage die jeweilige Naht bei OpenRouter beantwortet. Ohne Filter
# stünden an der Sprachmodell-Naht auch Modelle ohne Structured Output.
_OPENROUTER_ABFRAGE: dict[str, dict[str, str]] = {
    Naht.SPRACHMODELL: {"supported_parameters": "structured_outputs"},
}

_OPENROUTER_FORMWIDRIG: str = "OpenRouter hat keine lesbare Modellliste geliefert."


class OpenRouterVerzeichnis:
    """Liest OpenRouters öffentliche Modellliste über den eingesetzten Client."""

    def __init__(self, client: Any) -> None:
        self.client: Any = client

    def vorschlaege(self, naht: str) -> list[Modellvorschlag]:
        """Liefert die Modelle dieser Naht, alphabetisch nach Klarnamen."""

        abfrage: dict[str, str] | None = _OPENROUTER_ABFRAGE.get(naht)
        if abfrage is None:
            raise KeineModellliste("Für diese Naht führt OpenRouter keine Modellliste.")
        return sorted(
            (self._vorschlag(eintrag) for eintrag in self._eintraege(abfrage)),
            key=lambda vorschlag: vorschlag.anzeige.casefold(),
        )

    def _eintraege(self, abfrage: dict[str, str]) -> list[Any]:
        # Holt die Modellliste und schält sie aus ihrem Umschlag.

        try:
            antwort: Any = self.client.get(OPENROUTER_MODELLE_URL, params=abfrage)
            antwort.raise_for_status()
            nutzlast: Any = antwort.json()
        except httpx.TransportError as exc:
            raise AnbieterNichtErreichbar("OpenRouter ist nicht erreichbar.") from exc
        except httpx.HTTPStatusError as exc:
            raise AnbieterLehntAb(
                "OpenRouter hat die Anfrage nach seinen Modellen abgelehnt."
            ) from exc
        except Exception as exc:
            raise AnbieterAntwortetFormwidrig(_OPENROUTER_FORMWIDRIG) from exc
        eintraege: Any = nutzlast.get("data") if isinstance(nutzlast, dict) else None
        if not isinstance(eintraege, list):
            raise AnbieterAntwortetFormwidrig(_OPENROUTER_FORMWIDRIG)
        return eintraege

    @staticmethod
    def _vorschlag(eintrag: Any) -> Modellvorschlag:
        # Bildet den fertigen Wert aus Modell-ID und dem Präfix des Profils.

        modellname: Any = eintrag.get("id") if isinstance(eintrag, dict) else None
        if not isinstance(modellname, str) or not modellname:
            raise AnbieterAntwortetFormwidrig(
                "OpenRouter hat einen Eintrag ohne Modell-ID geliefert."
            )
        anzeige: Any = eintrag.get("name")
        return Modellvorschlag(
            wert=f"{ANBIETER_PROFIL[Anbieter.OPENROUTER].praefix}{modellname}",
            modellname=modellname,
            anzeige=anzeige if isinstance(anzeige, str) and anzeige else modellname,
        )


# Welcher Modelltyp Infomaniaks Liste die jeweilige Naht bedient. Ohne Filter
# stünden an der Sprachmodell-Naht auch Embedding-, Reranker-, Bild- und
# Transkriptionsmodelle. Nach Structured Output lässt sich hier nicht filtern.
_INFOMANIAK_MODELLTYP: dict[str, str] = {
    Naht.SPRACHMODELL: "llm",
}

_INFOMANIAK_FORMWIDRIG: str = "Infomaniak hat keine lesbare Modellliste geliefert."


class InfomaniakVerzeichnis:
    """Liest Infomaniaks kontoweite Modellliste über den eingesetzten Client."""

    def __init__(self, client: Any) -> None:
        self.client: Any = client

    def vorschlaege(self, naht: str) -> list[Modellvorschlag]:
        """Liefert die Modelle dieser Naht, alphabetisch nach Modellnamen."""

        typ: str | None = _INFOMANIAK_MODELLTYP.get(naht)
        if typ is None:
            raise KeineModellliste("Für diese Naht führt Infomaniak keine Modellliste.")
        return sorted(
            (
                self._vorschlag(eintrag)
                for eintrag in self._eintraege()
                if isinstance(eintrag, dict) and eintrag.get("type") == typ
            ),
            key=lambda vorschlag: vorschlag.anzeige.casefold(),
        )

    def _eintraege(self) -> list[Any]:
        # Holt die kontoweite Liste und schält sie aus dem v1-Umschlag.

        try:
            antwort: Any = self.client.get(INFOMANIAK_MODELLE_URL)
            antwort.raise_for_status()
            nutzlast: Any = antwort.json()
        except httpx.TransportError as exc:
            raise AnbieterNichtErreichbar("Infomaniak ist nicht erreichbar.") from exc
        except httpx.HTTPStatusError as exc:
            raise AnbieterLehntAb(
                "Infomaniak hat die Anfrage nach seinen Modellen abgelehnt — "
                "meist liegt das am Token."
            ) from exc
        except Exception as exc:
            raise AnbieterAntwortetFormwidrig(_INFOMANIAK_FORMWIDRIG) from exc
        eintraege: Any = nutzlast.get("data") if isinstance(nutzlast, dict) else None
        if not isinstance(eintraege, list):
            raise AnbieterAntwortetFormwidrig(_INFOMANIAK_FORMWIDRIG)
        return eintraege

    @staticmethod
    def _vorschlag(eintrag: dict[str, Any]) -> Modellvorschlag:
        # Bildet den Vorschlag aus »name«: Die »id« ist eine bedeutungslose
        # Ganzzahl und taucht in keinem Feld des Tripels auf.

        modellname: Any = eintrag.get("name")
        if not isinstance(modellname, str) or not modellname:
            raise AnbieterAntwortetFormwidrig(
                "Infomaniak hat einen Eintrag ohne Modellnamen geliefert."
            )
        return Modellvorschlag(
            wert=f"{ANBIETER_PROFIL[Anbieter.INFOMANIAK].praefix}{modellname}",
            modellname=modellname,
            anzeige=modellname,
        )


def modellverzeichnis(anbieter: str, token: str) -> Modellverzeichnis:
    """Bildet zum Anbieter sein Verzeichnis samt HTTP-Client.

    Der Client entsteht hier und wird hineingereicht; das Verzeichnis selbst
    kennt kein Netz, sondern nur den Client, den es bekommt.
    """

    match anbieter:
        case Anbieter.OPENROUTER:
            # OpenRouters Liste ist öffentlich: Das getippte Token bleibt im
            # Formular, der Client trägt bewusst keinen Authorization-Kopf.
            return OpenRouterVerzeichnis(
                httpx.Client(timeout=MODELLLISTE_BUDGET_SEKUNDEN)
            )
        case Anbieter.INFOMANIAK:
            # Infomaniaks Liste hängt allein am getippten Token: Beim Anlegen
            # einer Fassung gibt es weder ein gespeichertes noch eine Basis-URL.
            return InfomaniakVerzeichnis(
                httpx.Client(
                    timeout=MODELLLISTE_BUDGET_SEKUNDEN,
                    headers={"Authorization": f"Bearer {token}"},
                )
            )
        case _:
            raise KeineModellliste(
                f"Für den Anbieter »{anbieter}« gibt es keine Modellliste."
            )

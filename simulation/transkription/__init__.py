"""Naht zur Audio-Transkription und ihr deterministischer Testadapter."""

from collections.abc import Sequence
from typing import Any, Protocol

from openai import APIConnectionError, OpenAI

from simulation.models import TranskriptionsKonfiguration

PLATZHALTER_TRANSKRIPT: str = "Dies ist ein Platzhalter-Transkript."


class LeeresTranskript(Exception):
    """Der Anbieter lieferte kein verwertbares Transkript."""


class TranskriptionsAnbieterfehler(Exception):
    """Der Anbieter konnte keine Transkription liefern."""


class AnbieterNichtErreichbar(Exception):
    """Der Transkriptions-Anbieter ist nicht erreichbar."""


class Transkription(Protocol):
    """Überführt eine Aufnahme unmittelbar in Text."""

    def transkribieren(self, audio: bytes) -> str:
        """Liefert das Transkript der Aufnahme."""


class FakeTranskription:
    """Spielt konfigurierte Transkripte und Fehler deterministisch ab."""

    def __init__(self, skript: Sequence[str | Exception]) -> None:
        self.skript: list[str | Exception] = list(skript)

    def transkribieren(self, audio: bytes) -> str:
        """Verbraucht genau einen Eintrag des Fake-Skripts."""

        ergebnis: str | Exception = self.skript.pop(0)
        if isinstance(ergebnis, Exception):
            raise ergebnis
        return ergebnis


class OpenAITranskription:
    """Transkribiert Aufnahmen sofort über eine OpenAI-kompatible Route."""

    def __init__(self, client: Any, modell: str, sprache: str) -> None:
        self.client: Any = client
        self.modell: str = modell
        self.sprache: str = sprache

    def transkribieren(self, audio: bytes) -> str:
        """Sendet die Aufnahme an den Anbieter des injizierten Clients.

        Das Zero-Retention-Tor aus ADR-0026 steht im Endpunkt, wo es einen
        sauberen HTTP-Ausgang hat; hier stünde es ein zweites Mal.
        """

        try:
            ergebnis: Any = self.client.audio.transcriptions.create(
                model=self.modell,
                language=self.sprache,
                file=("aufnahme.webm", audio, "audio/webm"),
            )
            text: object = ergebnis.text
        except APIConnectionError as exc:
            raise AnbieterNichtErreichbar from exc
        except Exception as exc:
            raise TranskriptionsAnbieterfehler from exc
        if not isinstance(text, str) or not text.strip():
            raise LeeresTranskript
        return text


def transkriptions_anbieter() -> Transkription:
    """Bildet je Anfrage den in der Datenbank konfigurierten Anbieter.

    Ein gehaltener Adapter überlebte eine rotierte Konfiguration im
    Prozessgedächtnis; deshalb wird hier jedes Mal neu gebildet.
    """

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    if konfiguration.anbieter == TranskriptionsKonfiguration.Anbieter.FAKE:
        # Der deterministische Adapter verbraucht sein Skript; produktiv trägt
        # der frisch gebildete Adapter deshalb genau einen Platzhaltertext.
        return FakeTranskription([PLATZHALTER_TRANSKRIPT])
    if konfiguration.anbieter == TranskriptionsKonfiguration.Anbieter.INFOMANIAK:
        raise TranskriptionsAnbieterfehler(
            "Der Infomaniak-Adapter ist noch nicht gebaut."
        )
    return OpenAITranskription(
        OpenAI(
            # Ohne eigene Endpunktwurzel bleibt die Vorgabe des Clients stehen.
            base_url=konfiguration.anbieter_basis_url or None,
            api_key=konfiguration.anbieter_token,
            timeout=120.0,
        ),
        modell=konfiguration.transkriptionsmodell,
        sprache=konfiguration.sprache,
    )

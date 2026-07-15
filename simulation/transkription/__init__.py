"""Naht zur Audio-Transkription und ihr deterministischer Testadapter."""

from collections.abc import Sequence
from typing import Any, Protocol

from django.conf import settings
from openai import APIConnectionError, OpenAI


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
    """Transkribiert Aufnahmen sofort über den konfigurierten OpenAI-Anbieter."""

    def __init__(self, client: Any | None = None) -> None:
        self.client: Any | None = client

    def transkribieren(self, audio: bytes) -> str:
        """Sendet Audio nur bei zugesicherter Zero-Retention an OpenAI."""

        if not settings.TRANSKRIPTION_ZERO_RETENTION:
            raise TranskriptionsAnbieterfehler(
                "Die Zero-Retention-Zusicherung fehlt."
            )
        if settings.TRANSKRIPTION_ANBIETER != "openai":
            raise TranskriptionsAnbieterfehler("Unbekannter Transkriptions-Anbieter.")
        try:
            client: Any = self.client or OpenAI(timeout=120.0)
            ergebnis: Any = client.audio.transcriptions.create(
                model=settings.TRANSKRIPTION_MODELL,
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

"""Naht zur Audio-Transkription und ihr deterministischer Testadapter."""

import time
from collections.abc import Callable, Sequence
from typing import Any, Protocol

import httpx
from openai import APIConnectionError, OpenAI

from simulation.models import ANBIETER_PROFIL, Anbieter, TranskriptionsKonfiguration

PLATZHALTER_TRANSKRIPT: str = "Dies ist ein Platzhalter-Transkript."

# Wie lange eine Aufnahme höchstens unterwegs sein darf — bei beiden Anbietern
# gleich: als Timeout des synchronen Aufrufs, als Gesamtbudget des Pollings
# einschließlich jeder einzelnen Anfrage darin. Die 120 s lassen 60 s Luft zum
# Worker-Timeout des Deployments (180 s, README), sodass ein hängender Anbieter
# einen sauberen Fehlerstatus erzeugt statt eines getöteten Workers.
TRANSKRIPTION_BUDGET_SEKUNDEN: float = 120.0

# Eine Anfrage, deren Budget schon aufgebraucht ist, bekommt noch diese Frist,
# damit sie sauber scheitert, statt mit einem Timeout von null zu hängen.
MINDEST_ANFRAGEFRIST_SEKUNDEN: float = 1.0

# Abstand zwischen zwei Abfragen des Stapelergebnisses bei Infomaniak.
INFOMANIAK_INTERVALL_SEKUNDEN: float = 2.0

# Infomaniak richtet die Gestalt des Stapelergebnisses nach diesem Parameter des
# Absendens; er ist deshalb bedeutungstragend und nicht kosmetisch. Mit "text"
# ist `data` die schlichte Transkriptzeichenkette, Zeilen durch `\n` getrennt,
# und `file_name` endet auf `.txt`. Ohne ihn stünde dort eine JSON-kodierte
# Zeichenkette der Form {"text": "…"}, die `_transkript` samt Klammern und
# Feldnamen als Transkript durchreichte. Am echten Konto verifiziert (#232);
# ein Test hält die Kopplung fest.
INFOMANIAK_ANTWORTFORMAT: str = "text"

# Infomaniak meldet den Stand eines Stapels als Zeichenkette. Alles, was hier
# nicht steht, gilt als »noch nicht fertig« — ein unbekannter Name läuft damit
# ins Budget statt in ein falsches Ergebnis.
#
# Am echten Konto verifiziert (#232) sind `success` als fertiger und `pending`
# als laufender Zustand; die übrigen Namen stammen aus der Anbieterdokumentation
# und den üblichen Schreibweisen. Der gescheiterte Zustand bleibt unverifiziert:
# Eine unbrauchbare Datei wird schon beim Absenden mit 422 abgewiesen und wird
# nie ein Stapel, ein scheiterender Stapel ließ sich deshalb nicht provozieren.
# Trägt der Anbieter einen anderen Namen, läuft ein gescheiterter Stapel ins
# volle Budget, statt sofort zu scheitern.
INFOMANIAK_FERTIG: frozenset[str] = frozenset({"success", "succeeded", "done"})
INFOMANIAK_GESCHEITERT: frozenset[str] = frozenset({"error", "failed", "canceled"})


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


class InfomaniakTranskription:
    """Transkribiert über Infomaniaks asynchrone Route, hinter synchroner Naht.

    Das Absenden liefert nur eine Stapelkennung; das Ergebnis wird von einer
    zweiten Route abgeholt. Das Warten liegt deshalb hier im Adapter — das
    `Transkription`-Protokoll bleibt synchron und Endpunkt wie Aufrufer bleiben
    unverändert.
    """

    def __init__(self, client: Any, basis_url: str, modell: str, sprache: str) -> None:
        self.client: Any = client
        self.basis_url: str = basis_url.rstrip("/")
        self.modell: str = modell
        self.sprache: str = sprache

    def transkribieren(self, audio: bytes) -> str:
        """Sendet die Aufnahme ab und holt ihr Ergebnis innerhalb des Budgets."""

        frist: float = time.monotonic() + TRANSKRIPTION_BUDGET_SEKUNDEN
        kennung: str = self._absenden(audio, frist)
        while True:
            text: str | None = self._abholen(kennung, frist)
            if text is not None:
                if not text.strip():
                    raise LeeresTranskript
                return text
            if time.monotonic() >= frist:
                raise TranskriptionsAnbieterfehler(
                    "Infomaniak lieferte das Transkript nicht innerhalb des Budgets."
                )
            time.sleep(INFOMANIAK_INTERVALL_SEKUNDEN)

    @staticmethod
    def _restzeit(frist: float) -> float:
        # Begrenzt jede einzelne Anfrage auf das, was vom Budget noch übrig ist,
        # damit auch eine hängende Anfrage das Gesamtbudget nicht sprengt.

        return max(frist - time.monotonic(), MINDEST_ANFRAGEFRIST_SEKUNDEN)

    def _absenden(self, audio: bytes, frist: float) -> str:
        # Liefert die Stapelkennung, unter der das Ergebnis abzuholen ist.

        nutzlast: Any = self._nutzlast(
            lambda: self.client.post(
                f"{self.basis_url}/audio/transcriptions",
                data={
                    "model": self.modell,
                    "language": self.sprache,
                    "response_format": INFOMANIAK_ANTWORTFORMAT,
                },
                files={"file": ("aufnahme.webm", audio, "audio/webm")},
                timeout=self._restzeit(frist),
            )
        )
        kennung: Any = nutzlast.get("batch_id") if isinstance(nutzlast, dict) else None
        if not isinstance(kennung, str) or not kennung:
            raise TranskriptionsAnbieterfehler("Infomaniak nannte keine Stapelkennung.")
        return kennung

    def _abholen(self, kennung: str, frist: float) -> str | None:
        # Liefert das Transkript, oder None, solange der Stapel noch läuft.

        # Die Ergebnisroute liegt neben der OpenAI-kompatiblen Wurzel, nicht
        # unter ihr: .../1/ai/<product_id>/results/<batch_id>.
        wurzel: str = self.basis_url.removesuffix("/openai")
        nutzlast: Any = self._nutzlast(
            lambda: self.client.get(
                f"{wurzel}/results/{kennung}",
                timeout=self._restzeit(frist),
            )
        )
        if not isinstance(nutzlast, dict):
            raise TranskriptionsAnbieterfehler(
                "Infomaniak antwortete nicht mit einem Stapelergebnis."
            )
        gemeldet: Any = nutzlast.get("status")
        # Ein Stand, der keine Zeichenkette ist, zählt wie ein unbekannter Name.
        status: str = gemeldet if isinstance(gemeldet, str) else ""
        if status in INFOMANIAK_GESCHEITERT:
            raise TranskriptionsAnbieterfehler(
                f"Infomaniak meldet den Stapel als gescheitert: {status}."
            )
        if status not in INFOMANIAK_FERTIG:
            return None
        return self._transkript(nutzlast.get("data"))

    @staticmethod
    def _transkript(ergebnis: Any) -> str:
        # Liest den Text aus dem fertigen Stapelergebnis. Weil das Absenden
        # INFOMANIAK_ANTWORTFORMAT mitschickt, ist `data` bereits das rohe
        # Transkript und wird unverändert durchgereicht.

        if not isinstance(ergebnis, str):
            raise TranskriptionsAnbieterfehler(
                "Das fertige Stapelergebnis trug keinen Text."
            )
        return ergebnis

    @staticmethod
    def _nutzlast(anfrage: Callable[[], Any]) -> Any:
        # Führt eine Anfrage aus und schält den Umschlag von der Nutzlast.

        try:
            antwort: Any = anfrage()
            antwort.raise_for_status()
            nutzlast: Any = antwort.json()
        except httpx.TransportError as exc:
            raise AnbieterNichtErreichbar from exc
        except Exception as exc:
            raise TranskriptionsAnbieterfehler from exc
        # Die API der Version 1 umschlägt ihre Nutzlast mit {"result", "data"}.
        # Erkennbar ist der Umschlag nur am Paar: Das Stapelobjekt der
        # Ergebnisroute trägt selbst ein `data`-Feld, aber kein `result` — an
        # `data` allein geschält, gäbe die Heuristik dessen Inhalt statt des
        # Stapels zurück.
        if isinstance(nutzlast, dict) and "result" in nutzlast and "data" in nutzlast:
            return nutzlast["data"]
        return nutzlast


def transkriptions_anbieter() -> Transkription:
    """Bildet je Anfrage den in der Datenbank konfigurierten Anbieter.

    Ein gehaltener Adapter überlebte eine rotierte Konfiguration im
    Prozessgedächtnis; deshalb wird hier jedes Mal neu gebildet.
    """

    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    anbieter: str = konfiguration.anbieter
    if anbieter == Anbieter.FAKE:
        # Der deterministische Adapter verbraucht sein Skript; produktiv trägt
        # der frisch gebildete Adapter deshalb genau einen Platzhaltertext.
        return FakeTranskription([PLATZHALTER_TRANSKRIPT])
    if anbieter == Anbieter.INFOMANIAK:
        return InfomaniakTranskription(
            httpx.Client(
                headers={"Authorization": f"Bearer {konfiguration.anbieter_token}"},
                timeout=TRANSKRIPTION_BUDGET_SEKUNDEN,
            ),
            basis_url=konfiguration.anbieter_basis_url,
            modell=konfiguration.transkriptionsmodell,
            sprache=konfiguration.sprache,
        )
    # OpenRouter spricht die OpenAI-Route.
    return OpenAITranskription(
        OpenAI(
            # Ohne eigene Endpunktwurzel gilt die von OpenRouter — nie die des
            # Clients, sonst ginge das OpenRouter-Token an OpenAI.
            base_url=(
                konfiguration.anbieter_basis_url
                or ANBIETER_PROFIL[Anbieter.OPENROUTER].standard_basis_url
            ),
            # Das Token steht ausschließlich in der Konfiguration; ein leeres
            # fällt bewusst nicht auf OPENAI_API_KEY aus der Umgebung zurück.
            api_key=konfiguration.anbieter_token,
            timeout=TRANSKRIPTION_BUDGET_SEKUNDEN,
        ),
        modell=konfiguration.transkriptionsmodell,
        sprache=konfiguration.sprache,
    )

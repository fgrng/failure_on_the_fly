"""Gemeinsame Testadapter am Fake-Sprachmodell."""

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from unittest import mock

import time_machine

from simulation.sprachmodell import Antwort, FakeSprachmodell, nachrichten_bauen


@contextmanager
def _vor_jedem_aufruf(
    vorher: Callable[[list[dict[str, str]]], None],
) -> Iterator[None]:
    """Reicht im Block die Nachrichten jedes Fake-Aufrufs an ``vorher`` weiter."""

    echte_antworten = FakeSprachmodell.antworten

    def umhuellt(
        sprachmodell: FakeSprachmodell,
        system_prompt: str,
        user_prompt: str,
        verlauf: Sequence[tuple[str, str]],
        eingabe: str,
        ausgabe_schema: Mapping[str, object],
        timeout: float,
    ) -> Antwort:
        # Erst der Testadapter, dann antwortet der echte Fake.
        vorher(nachrichten_bauen(system_prompt, user_prompt, verlauf, eingabe))
        return echte_antworten(
            sprachmodell,
            system_prompt,
            user_prompt,
            verlauf,
            eingabe,
            ausgabe_schema,
            timeout,
        )

    with mock.patch.object(FakeSprachmodell, "antworten", umhuellt):
        yield


@contextmanager
def anfragen_aufzeichnen() -> Iterator[list[list[dict[str, str]]]]:
    """Zeichnet die Nachrichten jedes Fake-Aufrufs im Block in eine frische Liste auf."""

    anfragen: list[list[dict[str, str]]] = []
    with _vor_jedem_aufruf(anfragen.append):
        yield anfragen


@contextmanager
def modellaufrufe_dauern(
    uhr: time_machine.Traveller, sekunden: float
) -> Iterator[None]:
    """Lässt im Block jeden Fake-Aufruf die Uhr um ``sekunden`` vorspulen."""

    # Das Modell rechnet: Die Wanduhr läuft weiter, dann antwortet der Fake.
    with _vor_jedem_aufruf(lambda _nachrichten: uhr.shift(sekunden)):
        yield

"""Gemeinsame Aufzeichnung der Anfragen an das Fake-Sprachmodell."""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from unittest import mock

from simulation.sprachmodell import Antwort, FakeSprachmodell, nachrichten_bauen


@contextmanager
def anfragen_aufzeichnen() -> Iterator[list[list[dict[str, str]]]]:
    """Zeichnet die Nachrichten jedes Fake-Aufrufs im Block in eine frische Liste auf."""

    anfragen: list[list[dict[str, str]]] = []
    echte_antworten = FakeSprachmodell.antworten

    def aufzeichnend(
        sprachmodell: FakeSprachmodell,
        system_prompt: str,
        user_prompt: str,
        verlauf: Sequence[tuple[str, str]],
        eingabe: str,
        ausgabe_schema: Mapping[str, object],
        timeout: float,
    ) -> Antwort:
        anfragen.append(nachrichten_bauen(system_prompt, user_prompt, verlauf, eingabe))
        return echte_antworten(
            sprachmodell,
            system_prompt,
            user_prompt,
            verlauf,
            eingabe,
            ausgabe_schema,
            timeout,
        )

    with mock.patch.object(FakeSprachmodell, "antworten", aufzeichnend):
        yield anfragen

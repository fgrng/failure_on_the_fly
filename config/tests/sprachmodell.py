"""Gemeinsame Testadapter am Fake-Sprachmodell."""

from collections.abc import Callable, Iterator, Mapping, Sequence
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
        # Hält die Nachrichten des Aufrufs fest und antwortet wie der echte Fake.
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


@contextmanager
def modellaufrufe_dauern(
    vorspulen: Callable[[float], object], sekunden: float
) -> Iterator[None]:
    """Lässt im Block jeden Fake-Aufruf die Uhr um ``sekunden`` vorspulen.

    ``vorspulen`` ist das ``shift`` eines laufenden time-machine-Travellers.
    """

    echte_antworten = FakeSprachmodell.antworten

    def dauernd(
        sprachmodell: FakeSprachmodell,
        system_prompt: str,
        user_prompt: str,
        verlauf: Sequence[tuple[str, str]],
        eingabe: str,
        ausgabe_schema: Mapping[str, object],
        timeout: float,
    ) -> Antwort:
        # Das Modell rechnet: Die Wanduhr läuft weiter, dann antwortet der Fake.
        vorspulen(sekunden)
        return echte_antworten(
            sprachmodell,
            system_prompt,
            user_prompt,
            verlauf,
            eingabe,
            ausgabe_schema,
            timeout,
        )

    with mock.patch.object(FakeSprachmodell, "antworten", dauernd):
        yield

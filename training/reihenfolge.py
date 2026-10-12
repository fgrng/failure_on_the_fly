"""Die empfohlene Reihenfolge der Vignetten eines Trainings."""

from collections import Counter
from collections.abc import Iterable


def positionen_in_aufnahmereihenfolge(
    aufnahmen: Iterable[tuple[int, int]],
) -> list[tuple[int, int, int]]:
    """Nummeriert die Vignetten jedes Trainings lückenlos in Aufnahme-Reihenfolge.

    Die Aufnahmen kommen als Paare (Training, Vignette) in der Reihenfolge, in
    der sie aufgenommen wurden; jedes Paar erhält seine Position ab 1.

    >>> positionen_in_aufnahmereihenfolge([(1, 30), (2, 10), (1, 20)])
    [(1, 30, 1), (2, 10, 1), (1, 20, 2)]
    """
    bisher: Counter[int] = Counter()
    positionen: list[tuple[int, int, int]] = []
    for training_id, vignette_id in aufnahmen:
        bisher[training_id] += 1
        positionen.append((training_id, vignette_id, bisher[training_id]))
    return positionen

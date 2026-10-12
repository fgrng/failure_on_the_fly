"""Tests für die Vergabe der Positionen in Aufnahme-Reihenfolge."""

from training.reihenfolge import positionen_in_aufnahmereihenfolge


def test_vergibt_je_training_lueckenlose_positionen_in_aufnahmereihenfolge() -> None:
    """Jedes Training zählt seine Vignetten in der Reihenfolge der Aufnahme ab 1."""

    aufnahmen: list[tuple[int, int]] = [(1, 30), (2, 10), (1, 20), (2, 30), (1, 10)]

    assert positionen_in_aufnahmereihenfolge(aufnahmen) == [
        (1, 30, 1),
        (2, 10, 1),
        (1, 20, 2),
        (2, 30, 2),
        (1, 10, 3),
    ]


def test_ohne_aufnahmen_entstehen_keine_positionen() -> None:
    """Leere Trainings tauchen in der Vergabe nicht auf."""

    assert positionen_in_aufnahmereihenfolge([]) == []

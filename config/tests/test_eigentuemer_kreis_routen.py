"""Die Routen des Eigentümer-Kreises heißen in allen Bestands-Apps gleich (Spec #207).

Der Wächter hält fest, was Ticket #224 hergestellt hat: dieselben zwei
URL-Namen und dasselbe Pfadsegment über alle eigentümer-tragenden Apps hinweg.

Die zu prüfenden Apps kommen wie im Vertragstest der Modelle aus
`bestandsmodelle()` — ein künftiges fünftes Bestandsmodell läuft damit ohne
Zutun mit, statt still aus der Reihe zu fallen. Dass der URL-Namespace einer
Bestands-App ihr `app_label` ist, hält der Test mit: Weicht eine App davon ab,
findet `reverse()` sie nicht.
"""

import pytest
from django.urls import reverse

from konten.eigentuemerschaft import bestandsmodelle

je_bestands_app: pytest.MarkDecorator = pytest.mark.parametrize(
    "namespace",
    [modell._meta.app_label for modell in bestandsmodelle()],
)


@je_bestands_app
def test_hinzufuegen_fuehrt_ueber_das_eigentuemerinnen_segment(namespace: str) -> None:
    """Das Eintragen liegt überall unter demselben Namen und Pfadsegment."""
    pfad: str = reverse(f"{namespace}:eigentuemerin_hinzufuegen", args=[1])

    assert pfad.endswith("/eigentuemerinnen/hinzufuegen/")


@je_bestands_app
def test_entfernen_fuehrt_ueber_das_eigentuemerinnen_segment(namespace: str) -> None:
    """Das Austragen liegt überall unter demselben Namen und Pfadsegment."""
    pfad: str = reverse(f"{namespace}:eigentuemerin_entfernen", args=[1, 2])

    assert pfad.endswith("/eigentuemerinnen/2/entfernen/")

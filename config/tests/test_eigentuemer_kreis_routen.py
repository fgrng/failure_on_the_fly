"""Die Routen des Eigentümer-Kreises heißen in allen vier Apps gleich (Spec #207).

Der Wächter hält fest, was Ticket #224 hergestellt hat: dieselben zwei
URL-Namen und dasselbe Pfadsegment über alle eigentümer-tragenden Apps hinweg.
Ohne ihn fiele eine fünfte App still aus der Reihe.
"""

import pytest
from django.urls import reverse

app_namespaces: pytest.MarkDecorator = pytest.mark.parametrize(
    "namespace",
    ["vignetten", "fragebogen_items", "training", "erhebungen"],
)


@app_namespaces
def test_hinzufuegen_fuehrt_ueber_das_eigentuemerinnen_segment(namespace: str) -> None:
    pfad: str = reverse(f"{namespace}:eigentuemerin_hinzufuegen", args=[1])

    assert pfad.endswith("/eigentuemerinnen/hinzufuegen/")


@app_namespaces
def test_entfernen_fuehrt_ueber_das_eigentuemerinnen_segment(namespace: str) -> None:
    pfad: str = reverse(f"{namespace}:eigentuemerin_entfernen", args=[1, 2])

    assert pfad.endswith("/eigentuemerinnen/2/entfernen/")

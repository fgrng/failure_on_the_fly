"""Gemeinsame Fixtures der Evals-Tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def eigene_sperrdatei(tmp_path: Path) -> Iterator[Path]:
    """Jeder Test sperrt seine eigene Datei; parallele Worker stören sich nicht."""

    sperrdatei: Path = tmp_path / "evallaeufe.lock"
    with override_settings(EVALLAEUFE_SPERRE=sperrdatei):
        yield sperrdatei

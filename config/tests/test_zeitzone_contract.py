"""Vertragstest für die Zeitzone, in der Forschende Zeitpunkte eingeben."""

import os

from django.conf import settings


def test_zeitzone_kommt_aus_der_umgebung_und_faellt_auf_ortszeit_zurueck() -> None:
    """Ohne gesetzte Variable gilt die Zone, in der die Erhebungen stattfinden.

    Die Formularfelder für den Erhebungszeitraum sind `datetime-local` und
    senden nackte Wanduhrzeit. Steht die Zone des Servers auf UTC, liest
    `stichprobe_anlegen` diese Eingabe um den Ortsversatz verschoben — die
    Stichprobe beginnt dann später als eingegeben und verweigert bis dahin
    die Teilnahme.
    """

    erwartet: str = os.environ.get("TIME_ZONE", "Europe/Berlin")

    assert settings.TIME_ZONE == erwartet
    assert settings.USE_TZ is True

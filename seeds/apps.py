"""Django-App-Konfiguration für Seeds.

Sammelt Management-Commands zur Datenbankvorbereitung und -befüllung:
Entwicklungs-Seeds für den manuellen Testlauf ebenso wie künftige
produktive Bootstrap-Schritte (etwa das erste Admin-Konto). Die App
trägt selbst keine Modelle; sie bündelt nur die Commands an einem Ort.
"""

from django.apps import AppConfig


class SeedsConfig(AppConfig):
    """Konfiguriert die Seeds-App."""

    name: str = "seeds"

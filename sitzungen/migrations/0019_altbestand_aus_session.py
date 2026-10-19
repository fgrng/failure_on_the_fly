"""Entfernt Teilnahmezustand, flüchtige Inhalte und Probelauf aus django_session.

Sie liegen seit #510 bis #512 im Cookie und im kurzlebigen Speicher, nie mehr
neben dem Konto. Alle anderen Schlüssel, insbesondere die Anmeldung, bleiben.
Laufende flüchtige Sitzungen enden danach beim nächsten Zugriff als
abgebrochen; deshalb nicht während einer laufenden Stichprobe deployen.
"""

from django.apps.registry import Apps
from django.contrib.sessions.backends.db import SessionStore
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

ALTBESTAND: tuple[str, ...] = (
    "erhebung_teilnahme_tokens",
    "fluechtige_sitzungen",
    "probelauf",
)


def altbestand_entfernen(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Schreibt jede Session ohne die drei Schlüssel zurück, die sie enthält."""

    kodierung = SessionStore()
    for zeile in apps.get_model("sessions", "Session").objects.iterator():
        daten: dict[str, object] = kodierung.decode(zeile.session_data)
        if not any(schluessel in daten for schluessel in ALTBESTAND):
            continue
        for schluessel in ALTBESTAND:
            daten.pop(schluessel, None)
        zeile.session_data = kodierung.encode(daten)
        zeile.save(update_fields=["session_data"])


class Migration(migrations.Migration):
    """Räumt den Altbestand aus django_session; rückwärts ein No-op."""

    dependencies = [
        ("sessions", "0001_initial"),
        ("sitzungen", "0018_laufende_sitzungen_pinnen"),
    ]

    operations = [
        migrations.RunPython(altbestand_entfernen, migrations.RunPython.noop),
    ]

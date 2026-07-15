"""Führt die parallelen Erhebungs-Migrationen zusammen."""

from django.db import migrations


class Migration(migrations.Migration):
    """Markiert beide unabhängigen Schema-Erweiterungen als angewendet."""

    dependencies = [
        ("erhebungen", "0002_erhebung_modell_konfiguration"),
        ("erhebungen", "0002_erhebungsbindung_teilnahme_link"),
    ]

    operations = []

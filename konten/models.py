"""Datenmodelle für Nutzerkonten."""

from django.contrib.auth.models import AbstractUser


class Konto(AbstractUser):
    """Das Nutzerkonto der Anwendung mit Djangos Standard-Anmeldefeldern."""

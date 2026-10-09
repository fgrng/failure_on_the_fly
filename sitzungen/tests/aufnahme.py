"""Eine Audioaufnahme für die Tests des Transkriptionsendpunkts."""

from django.core.files.uploadedfile import SimpleUploadedFile


def audioaufnahme() -> SimpleUploadedFile:
    """Erzeugt für jede Anfrage eine frische Datei, weil Django sie einliest."""

    return SimpleUploadedFile("aufnahme.webm", b"audio", "audio/webm")

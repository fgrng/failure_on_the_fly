"""URLs für die Systemansicht des Simulationskerns."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "simulation"

urlpatterns: list[URLPattern] = [
    path("kern/", views.kern, name="kern"),
    path("kern/verwalten/", views.kern_verwalten, name="kern_verwalten"),
    path(
        "kern/anlegen/",
        views.kern_anlegen,
        {"mit_vorlage": False},
        name="kern_anlegen",
    ),
    path(
        "kern/anlegen/standard/",
        views.kern_anlegen,
        {"mit_vorlage": True},
        name="kern_anlegen_standard",
    ),
    path("kern/<int:pk>/bearbeiten/", views.kern_bearbeiten, name="kern_bearbeiten"),
    path("kern/<int:pk>/neue-fassung/", views.neue_fassung, name="neue_fassung"),
    path("kern/<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"),
    path("kern/<int:pk>/verwerfen/", views.verwerfen, name="verwerfen"),
    path(
        "modell-konfiguration/",
        views.modell_konfiguration,
        name="modell_konfiguration",
    ),
    path(
        "modellvorschlaege/",
        views.modellvorschlaege,
        name="modellvorschlaege",
    ),
    path(
        "modell-konfiguration/<int:pk>/aktivieren/",
        views.modell_konfiguration_aktivieren,
        name="modell_konfiguration_aktivieren",
    ),
    path(
        "transkription/",
        views.transkriptions_konfiguration,
        name="transkriptions_konfiguration",
    ),
]

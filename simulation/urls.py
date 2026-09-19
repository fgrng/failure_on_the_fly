"""URLs für die Systemansicht des Simulationskerns."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "simulation"

urlpatterns: list[URLPattern] = [
    path("kern/", views.kern, name="kern"),
    path("kern/verwalten/", views.kern_verwalten, name="kern_verwalten"),
    path("kern/<int:pk>/neue-fassung/", views.neue_fassung, name="neue_fassung"),
    path("kern/<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"),
    path("kern/<int:pk>/verwerfen/", views.verwerfen, name="verwerfen"),
]

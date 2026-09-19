"""URLs für die Systemansicht des Simulationskerns."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "simulation"

urlpatterns: list[URLPattern] = [
    path("kern/", views.kern, name="kern"),
    path("kern/verwalten/", views.kern_verwalten, name="kern_verwalten"),
]

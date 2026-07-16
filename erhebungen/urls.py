"""Öffentliche URLs für pseudonyme Erhebungsteilnahmen."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "erhebungen"

urlpatterns: list[URLPattern] = [
    path("eigene/", views.liste, name="liste"),
    path("eigene/anlegen/", views.anlegen, name="anlegen"),
    path("eigene/<int:pk>/", views.detail, name="detail"),
    path(
        "eigene/<int:pk>/vignetten/<int:vignette_pk>/hinzufuegen/",
        views.vignette_hinzufuegen,
        name="vignette_hinzufuegen",
    ),
    path(
        "eigene/<int:pk>/vignetten/<int:vignette_pk>/entfernen/",
        views.vignette_entfernen,
        name="vignette_entfernen",
    ),
    path(
        "eigene/<int:pk>/konfiguration/",
        views.konfiguration_speichern,
        name="konfiguration_speichern",
    ),
    path("eigene/<int:pk>/loeschen/", views.loeschen, name="loeschen"),
    path("teilnahme/<uuid:teilnahme_link>/", views.teilnehmen, name="teilnehmen"),
    path(
        "teilnahme/<uuid:teilnahme_link>/einwilligung/",
        views.einwilligung,
        name="einwilligung",
    ),
    path(
        "teilnahme/<uuid:teilnahme_link>/instruktion/",
        views.instruktion,
        name="instruktion",
    ),
]

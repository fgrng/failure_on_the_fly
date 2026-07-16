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
    path(
        "eigene/<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"
    ),
    path(
        "eigene/<int:pk>/zurueckziehen/", views.zurueckziehen, name="zurueckziehen"
    ),
    path(
        "eigene/<int:pk>/stichproben/anlegen/",
        views.stichprobe_anlegen,
        name="stichprobe_anlegen",
    ),
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
    path("teilnahme/<uuid:teilnahme_link>/spielen/", views.spielen, name="spielen"),
    path("teilnahme/<uuid:teilnahme_link>/abschluss/", views.abschluss, name="abschluss"),
    path("teilnahme/token/<str:token>/gespraech/", views.gespraech, name="gespraech"),
    path(
        "teilnahme/token/<str:token>/gespraech/beenden/",
        views.gespraech_beenden,
        name="gespraech_beenden",
    ),
    path(
        "teilnahme/token/<str:token>/abbrechen/",
        views.abbrechen,
        name="abbrechen",
    ),
    path("teilnahme/token/<str:token>/debrief/", views.debrief, name="debrief"),
]

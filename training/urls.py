"""URLs für Trainingskatalog und Ausbilder-UI."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "training"

urlpatterns: list[URLPattern] = [
    path("", views.katalog, name="katalog"),
    path("eigene/", views.liste, name="liste"),
    path("anlegen/", views.anlegen, name="anlegen"),
    path("eigene/<int:pk>/", views.kuratieren, name="kuratieren"),
    path(
        "eigene/<int:pk>/veroeffentlichen/",
        views.veroeffentlichen,
        name="veroeffentlichen",
    ),
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
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:training_pk>/vignetten/<int:vignette_pk>/", views.wahl, name="wahl"),
]

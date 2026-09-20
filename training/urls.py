"""URLs für Trainingskatalog und Ausbilder-UI."""

from django.urls import path
from django.urls.resolvers import URLPattern

from simulation.transkription import transkriptions_anbieter
from sitzungen.views import transkriptions_endpunkt

from . import views

app_name: str = "training"

urlpatterns: list[URLPattern] = [
    path("", views.katalog, name="katalog"),
    path("eigene/", views.liste, name="liste"),
    path("historie/", views.historie, name="historie"),
    path("anlegen/", views.anlegen, name="anlegen"),
    path("eigene/<int:pk>/", views.kuratieren, name="kuratieren"),
    path(
        "eigene/<int:pk>/veroeffentlichen/",
        views.veroeffentlichen,
        name="veroeffentlichen",
    ),
    path(
        "eigene/<int:pk>/koautorinnen/hinzufuegen/",
        views.koautorin_hinzufuegen,
        name="koautorin_hinzufuegen",
    ),
    path(
        "eigene/<int:pk>/koautorinnen/<int:konto_pk>/entfernen/",
        views.koautorin_entfernen,
        name="koautorin_entfernen",
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
    path(
        "<int:training_pk>/vignetten/<int:vignette_pk>/einwilligung/",
        views.einwilligung,
        name="einwilligung",
    ),
    path("<int:training_pk>/vignetten/<int:vignette_pk>/", views.wahl, name="wahl"),
    path("sitzung/gespraech/", views.gespraech, name="gespraech"),
    path(
        "sitzung/gespraech/beenden/",
        views.gespraech_beenden,
        name="gespraech_beenden",
    ),
    path("sitzung/abbrechen/", views.abbrechen, name="abbrechen"),
    path("sitzung/debrief/", views.debrief, name="debrief"),
    path("sitzung/<int:pk>/ansehen/", views.sitzung_ansehen, name="sitzung_ansehen"),
    path(
        "sitzung/transkription/",
        transkriptions_endpunkt(transkriptions_anbieter(), views.training_sitzung),
        name="transkription",
    ),
]

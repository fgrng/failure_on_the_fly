"""URLs für schreibfreie Sitzungsabläufe."""

from django.urls import path
from django.urls.resolvers import URLPattern

from simulation.transkription import OpenAITranskription

from . import views

app_name: str = "sitzungen"

urlpatterns: list[URLPattern] = [
    path("probelauf/", views.probelauf_auswahl, name="probelauf_auswahl"),
    path(
        "probelauf/administratorin/",
        views.administratorin_probelauf_auswahl,
        name="administratorin_probelauf_auswahl",
    ),
    path(
        "probelauf/administratorin/starten/",
        views.administratorin_probelauf_starten,
        name="administratorin_probelauf_starten",
    ),
    path(
        "probelauf/<int:pk>/starten/",
        views.probelauf_starten,
        name="probelauf_starten",
    ),
    path("probelauf/gespraech/", views.probelauf_gespraech, name="probelauf_gespraech"),
    path("probelauf/beenden/", views.probelauf_beenden, name="probelauf_beenden"),
    path("probelauf/debrief/", views.probelauf_debrief, name="probelauf_debrief"),
    path(
        "transkription/",
        views.transkriptions_endpunkt(OpenAITranskription()),
        name="transkription",
    ),
    path("training/gespraech/", views.training_gespraech, name="training_gespraech"),
    path("training/beenden/", views.training_beenden, name="training_beenden"),
    path("training/abbrechen/", views.training_abbrechen, name="training_abbrechen"),
    path("training/debrief/", views.training_debrief, name="training_debrief"),
    path(
        "training/sitzung/<int:pk>/ansehen/",
        views.training_sitzung_ansehen,
        name="training_sitzung_ansehen",
    ),
]

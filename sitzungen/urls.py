"""URLs für schreibfreie Sitzungsabläufe."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "sitzungen"

urlpatterns: list[URLPattern] = [
    path("probelauf/", views.probelauf_auswahl, name="probelauf_auswahl"),
    path(
        "probelauf/<int:pk>/starten/",
        views.probelauf_starten,
        name="probelauf_starten",
    ),
]

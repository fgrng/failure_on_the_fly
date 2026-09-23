"""URLs der Markdown-Vorschau."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "texte"

urlpatterns: list[URLPattern] = [
    path("vorschau/", views.vorschau, name="vorschau"),
]

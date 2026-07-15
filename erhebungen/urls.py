"""Öffentliche URLs für pseudonyme Erhebungsteilnahmen."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "erhebungen"

urlpatterns: list[URLPattern] = [
    path("teilnahme/<uuid:teilnahme_link>/", views.teilnehmen, name="teilnehmen"),
]

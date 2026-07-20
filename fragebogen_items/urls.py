"""URLs des Fragebogen-Item-Editors."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "fragebogen_items"

urlpatterns: list[URLPattern] = [
    path("", views.liste, name="liste"),
    path("anlegen/", views.anlegen, name="anlegen"),
    path("<int:pk>/", views.detail, name="detail"),
]

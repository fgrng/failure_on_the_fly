"""URLs des Vignetten-Editors."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "vignetten"

urlpatterns: list[URLPattern] = [
    path("", views.liste, name="liste"),
    path("anlegen/", views.anlegen, name="anlegen"),
    path("<int:pk>/bearbeiten/", views.bearbeiten, name="bearbeiten"),
    path("<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"),
    path("<int:pk>/reversionieren/", views.reversionieren, name="reversionieren"),
    path("<int:pk>/", views.detail, name="detail"),
]

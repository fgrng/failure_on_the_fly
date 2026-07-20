"""URLs des Fragebogen-Item-Editors."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "fragebogen_items"

urlpatterns: list[URLPattern] = [
    path("", views.liste, name="liste"),
    path("anlegen/", views.anlegen, name="anlegen"),
    path("<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"),
    path(
        "<int:pk>/koautorinnen/hinzufuegen/",
        views.koautorin_hinzufuegen,
        name="koautorin_hinzufuegen",
    ),
    path(
        "<int:pk>/koautorinnen/<int:konto_pk>/entfernen/",
        views.koautorin_entfernen,
        name="koautorin_entfernen",
    ),
    path("<int:pk>/", views.detail, name="detail"),
]

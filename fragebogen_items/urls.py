"""URLs des Fragebogen-Item-Editors."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "fragebogen_items"

urlpatterns: list[URLPattern] = [
    path("", views.liste, name="liste"),
    path("anlegen/", views.anlegen, name="anlegen"),
    path("<int:pk>/bearbeiten/", views.bearbeiten, name="bearbeiten"),
    path("<int:pk>/neue-fassung/", views.neue_fassung, name="neue_fassung"),
    path("<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"),
    path("<int:pk>/archivieren/", views.archivieren, name="archivieren"),
    path(
        "<int:pk>/entarchivieren/", views.entarchivieren, name="entarchivieren"
    ),
    path("<int:pk>/loeschen/", views.loeschen, name="loeschen"),
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

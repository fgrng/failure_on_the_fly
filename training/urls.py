"""URLs für den offenen Trainingskatalog."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "training"

urlpatterns: list[URLPattern] = [
    path("", views.katalog, name="katalog"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:training_pk>/vignetten/<int:vignette_pk>/", views.wahl, name="wahl"),
]

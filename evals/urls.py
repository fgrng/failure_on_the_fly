"""URLs der Evalläufe."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "evals"

urlpatterns: list[URLPattern] = [
    path("vignette/<int:pk>/", views.evallauf, name="evallauf"),
    path("vignette/<int:pk>/starten/", views.starten, name="starten"),
]

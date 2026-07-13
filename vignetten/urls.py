"""URLs des Vignetten-Editors."""

from django.urls import path

from . import views

app_name = "vignetten"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("anlegen/", views.anlegen, name="anlegen"),
    path("<int:pk>/", views.detail, name="detail"),
]

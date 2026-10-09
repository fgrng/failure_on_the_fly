"""URLs für die Systemansichten von Simulationskern, Evalkatalog und Konfigurationen."""

from django.urls import path
from django.urls.resolvers import URLPattern

from . import views

app_name: str = "simulation"

urlpatterns: list[URLPattern] = [
    path("kern/", views.kern, name="kern"),
    path("kern/verwalten/", views.kern_verwalten, name="kern_verwalten"),
    path(
        "kern/anlegen/",
        views.kern_anlegen,
        {"mit_vorlage": False},
        name="kern_anlegen",
    ),
    path(
        "kern/anlegen/standard/",
        views.kern_anlegen,
        {"mit_vorlage": True},
        name="kern_anlegen_standard",
    ),
    path("kern/<int:pk>/bearbeiten/", views.kern_bearbeiten, name="kern_bearbeiten"),
    path("kern/<int:pk>/neue-fassung/", views.neue_fassung, name="neue_fassung"),
    path("kern/<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"),
    path("kern/<int:pk>/verwerfen/", views.verwerfen, name="verwerfen"),
    path("evalkatalog/", views.evalkatalog, name="evalkatalog"),
    path(
        "evalkatalog/anlegen/",
        views.evalkatalog_anlegen,
        name="evalkatalog_anlegen",
    ),
    path(
        "evalkatalog/<int:pk>/",
        views.evalkatalog_editor,
        name="evalkatalog_editor",
    ),
    path(
        "evalkatalog/<int:pk>/kriterien/",
        views.evalkatalog_kriterien,
        name="evalkatalog_kriterien",
    ),
    path(
        "evalkatalog/<int:pk>/kriterien/anlegen/",
        views.evalkatalog_kriterium_anlegen,
        name="evalkatalog_kriterium_anlegen",
    ),
    path(
        "evalkatalog/<int:pk>/kriterien/<int:kriterium_pk>/loeschen/",
        views.evalkatalog_kriterium_loeschen,
        name="evalkatalog_kriterium_loeschen",
    ),
    path(
        "evalkatalog/<int:pk>/kriterien/<int:kriterium_pk>/<str:richtung>/",
        views.evalkatalog_kriterium_verschieben,
        name="evalkatalog_kriterium_verschieben",
    ),
    path(
        "evalkatalog/<int:pk>/evals/anlegen/",
        views.evalkatalog_eval_anlegen,
        name="evalkatalog_eval_anlegen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/",
        views.evalkatalog_eval,
        name="evalkatalog_eval",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/loeschen/",
        views.evalkatalog_eval_loeschen,
        name="evalkatalog_eval_loeschen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/<str:richtung>/",
        views.evalkatalog_eval_verschieben,
        name="evalkatalog_eval_verschieben",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/kriterien/anlegen/",
        views.evalkatalog_evalkriterium_anlegen,
        name="evalkatalog_evalkriterium_anlegen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/kriterien/<int:kriterium_pk>/loeschen/",
        views.evalkatalog_evalkriterium_loeschen,
        name="evalkatalog_evalkriterium_loeschen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/kriterien/<int:kriterium_pk>/<str:richtung>/",
        views.evalkatalog_evalkriterium_verschieben,
        name="evalkatalog_evalkriterium_verschieben",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/inputs/anlegen/",
        views.evalkatalog_evalinput_anlegen,
        name="evalkatalog_evalinput_anlegen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/inputs/<int:input_pk>/",
        views.evalkatalog_evalinput,
        name="evalkatalog_evalinput",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/inputs/<int:input_pk>/loeschen/",
        views.evalkatalog_evalinput_loeschen,
        name="evalkatalog_evalinput_loeschen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/inputs/<int:input_pk>/schritte/anlegen/",
        views.evalkatalog_inputschritt_anlegen,
        name="evalkatalog_inputschritt_anlegen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/inputs/<int:input_pk>/schritte/<int:schritt_pk>/loeschen/",
        views.evalkatalog_inputschritt_loeschen,
        name="evalkatalog_inputschritt_loeschen",
    ),
    path(
        "evalkatalog/<int:pk>/evals/<int:eval_pk>/inputs/<int:input_pk>/schritte/<int:schritt_pk>/<str:richtung>/",
        views.evalkatalog_inputschritt_verschieben,
        name="evalkatalog_inputschritt_verschieben",
    ),
    path(
        "evalkatalog/<int:pk>/finalisieren/",
        views.evalkatalog_finalisieren,
        name="evalkatalog_finalisieren",
    ),
    path(
        "evalkatalog/<int:pk>/neue-fassung/",
        views.evalkatalog_neue_fassung,
        name="evalkatalog_neue_fassung",
    ),
    path(
        "evalkatalog/<int:pk>/verwerfen/",
        views.evalkatalog_verwerfen,
        name="evalkatalog_verwerfen",
    ),
    path(
        "modell-konfiguration/",
        views.modell_konfiguration,
        name="modell_konfiguration",
    ),
    path(
        "modell-konfiguration/neu/",
        views.modell_konfiguration_neu,
        name="modell_konfiguration_neu",
    ),
    path(
        "modellvorschlaege/",
        views.modellvorschlaege,
        name="modellvorschlaege",
    ),
    path(
        "modell-konfiguration/<int:pk>/aktivieren/<str:verwendung>/",
        views.modell_konfiguration_aktivieren,
        name="modell_konfiguration_aktivieren",
    ),
    path(
        "transkription/",
        views.transkriptions_konfiguration,
        name="transkriptions_konfiguration",
    ),
]

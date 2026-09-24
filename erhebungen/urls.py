"""Öffentliche URLs für pseudonyme Erhebungsteilnahmen."""

from django.urls import path
from django.urls.resolvers import URLPattern

from simulation.transkription import transkriptions_anbieter
from sitzungen.views import transkriptions_endpunkt

from . import views

app_name: str = "erhebungen"

urlpatterns: list[URLPattern] = [
    path(
        "prototype/itemseite/",
        views.itemseite_prototype,
        name="itemseite_prototype",
    ),
    # PROTOTYPE #290 – nur mit DEBUG, siehe erhebungen/PROTOTYPE_LANGE_TEXTE.md.
    path(
        "prototype/lange-texte/",
        views.lange_texte_prototype,
        name="lange_texte_prototype",
    ),
    # PROTOTYPE #287 (Namensfeld) – nur mit DEBUG, siehe erhebungen/PROTOTYPE_NAMENSFELD.md.
    path(
        "prototype/namensfeld/",
        views.namensfeld_prototype,
        name="namensfeld_prototype",
    ),
    path("eigene/", views.liste, name="liste"),
    path("eigene/anlegen/", views.anlegen, name="anlegen"),
    path("eigene/<int:pk>/", views.detail, name="detail"),
    path(
        "eigene/<int:pk>/eigentuemerinnen/hinzufuegen/",
        views.eigentuemerin_hinzufuegen,
        name="eigentuemerin_hinzufuegen",
    ),
    path(
        "eigene/<int:pk>/eigentuemerinnen/<int:konto_pk>/entfernen/",
        views.eigentuemerin_entfernen,
        name="eigentuemerin_entfernen",
    ),
    path("eigene/<int:pk>/export/", views.export, name="export"),
    path(
        "eigene/<int:pk>/vignetten/<int:vignette_pk>/hinzufuegen/",
        views.vignette_hinzufuegen,
        name="vignette_hinzufuegen",
    ),
    path(
        "eigene/<int:pk>/vignetten/<int:vignette_pk>/entfernen/",
        views.vignette_entfernen,
        name="vignette_entfernen",
    ),
    path(
        "eigene/<int:pk>/vignetten/<int:vignette_pk>/verschieben/",
        views.vignette_verschieben,
        name="vignette_verschieben",
    ),
    path(
        "eigene/<int:pk>/reihenfolge/",
        views.reihenfolge_umschalten,
        name="reihenfolge_umschalten",
    ),
    path(
        "eigene/<int:pk>/items/<int:item_pk>/<str:andockpunkt>/hinzufuegen/",
        views.item_hinzufuegen,
        name="item_hinzufuegen",
    ),
    path(
        "eigene/<int:pk>/items/<int:zugehoerigkeit_pk>/entfernen/",
        views.item_entfernen,
        name="item_entfernen",
    ),
    path(
        "eigene/<int:pk>/items/<int:zugehoerigkeit_pk>/verschieben/",
        views.item_verschieben,
        name="item_verschieben",
    ),
    path(
        "eigene/<int:pk>/items/<int:zugehoerigkeit_pk>/umhaengen/",
        views.item_umhaengen,
        name="item_umhaengen",
    ),
    path(
        "eigene/<int:pk>/konfiguration/",
        views.konfiguration_speichern,
        name="konfiguration_speichern",
    ),
    path("eigene/<int:pk>/loeschen/", views.loeschen, name="loeschen"),
    path("eigene/<int:pk>/finalisieren/", views.finalisieren, name="finalisieren"),
    path("eigene/<int:pk>/zurueckziehen/", views.zurueckziehen, name="zurueckziehen"),
    path("eigene/<int:pk>/archivieren/", views.archivieren, name="archivieren"),
    path(
        "eigene/<int:pk>/entarchivieren/",
        views.entarchivieren,
        name="entarchivieren",
    ),
    path(
        "eigene/<int:pk>/stichproben/anlegen/",
        views.stichprobe_anlegen,
        name="stichprobe_anlegen",
    ),
    path(
        "eigene/<int:pk>/stichproben/<int:stichprobe_pk>/archivieren/",
        views.stichprobe_archivieren,
        name="stichprobe_archivieren",
    ),
    path("teilnahme/<uuid:teilnahme_link>/", views.teilnehmen, name="teilnehmen"),
    path(
        "teilnahme/<uuid:teilnahme_link>/einwilligung/",
        views.einwilligung,
        name="einwilligung",
    ),
    path(
        "teilnahme/<uuid:teilnahme_link>/instruktion/",
        views.instruktion,
        name="instruktion",
    ),
    path("teilnahme/<uuid:teilnahme_link>/spielen/", views.spielen, name="spielen"),
    path(
        "teilnahme/<uuid:teilnahme_link>/abschluss/", views.abschluss, name="abschluss"
    ),
    path("teilnahme/token/<str:token>/items/", views.itemblock, name="itemblock"),
    path("teilnahme/token/<str:token>/gespraech/", views.gespraech, name="gespraech"),
    path(
        "teilnahme/token/<str:token>/gespraech/beenden/",
        views.gespraech_beenden,
        name="gespraech_beenden",
    ),
    path(
        "teilnahme/token/<str:token>/abbrechen/",
        views.abbrechen,
        name="abbrechen",
    ),
    path("teilnahme/token/<str:token>/debrief/", views.debrief, name="debrief"),
    path(
        "teilnahme/transkription/",
        transkriptions_endpunkt(
            transkriptions_anbieter, views.sitzung_fuer_transkription
        ),
        name="transkription",
    ),
]

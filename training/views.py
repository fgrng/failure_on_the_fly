"""Views für Trainingskatalog und Ausbilder-UI."""

from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from config.downloads import zip_download
from konten.eigentuemer_views import eigentuemer_views
from konten.models import Konto
from konten.navigation import (
    AUSBILDERIN_GRUPPE,
    rolle_erforderlich,
    rolle_oder_administration,
)

from .forms import TrainingForm
from simulation.models import ModellKonfiguration, Simulationskern, Verwendung
from sitzungen.durchlauf import (
    Sitzungsnavigation,
    sitzung_abbrechen,
    sitzung_anzeigen,
    sitzung_beenden,
    sitzung_starten,
)
from sitzungen.models import Eingabemodus, Sitzung
from sitzungen.sink import DBSink
from sitzungen.views import (
    persistierten_debrief_anzeigen,
    persistierten_fehler_anzeigen,
    persistiertes_gespraech,
)

from vignetten.models import Vignette

from .abschriften import abschrift_freigeben, abschrift_holen, abschrift_loeschen
from .export import trainingsexport_zip
from .models import Abschrift, Training, Trainingsbindung


_ausbilderin_oder_administratorin = rolle_oder_administration(AUSBILDERIN_GRUPPE)
_ausbilderin_erforderlich = rolle_erforderlich(_ausbilderin_oder_administratorin)


def _eigene_finalen_vignetten(request: HttpRequest) -> QuerySet[Vignette]:
    """Liefert einbindbare Fassungen aus dem Eigentümer-Kreis."""

    return Vignette.objects.einbindbar().sichtbar_fuer(request.user)


def _zustand_badge(training: Training) -> str:
    """Ordnet Modellzustände den gemeinsamen Badge-Klassen zu."""

    return {
        Training.Zustand.ENTWURF: "draft",
        Training.Zustand.VEROEFFENTLICHT: "final",
    }[training.zustand]


def _sitzung_status_badge(status: str) -> str:
    """Ordnet Sitzungszustände den gemeinsamen Badge-Klassen zu."""

    if status == Sitzung.Status.ABGESCHLOSSEN:
        return "final"
    if status == Sitzung.Status.LAUFEND:
        return "draft"
    return "archived"


def _sichtbares_training(request: HttpRequest, pk: int) -> Training:
    """Lädt ein für die eingeloggte Person sichtbares Training."""

    return get_object_or_404(Training.objects.sichtbar_fuer(request.user), pk=pk)


def _fremd_einsehbare_sitzungen(konto: Konto) -> QuerySet[Sitzung]:
    """Liefert die Sitzungen, die das Konto fremd einsehen darf (ADR-0049)."""
    return Sitzung.objects.fremd_einsehbar(Training.objects.sichtbar_fuer(konto))


def _zugaengliches_training(request: HttpRequest, pk: int) -> Training:
    """Lädt ein veröffentlichtes Training, das die Person betreten darf."""
    return get_object_or_404(
        Training.objects.veroeffentlicht().zugaenglich_fuer(request.user), pk=pk
    )


def _zugaengliches_training_mit_finaler_vignette(
    request: HttpRequest, training_pk: int, vignette_pk: int
) -> tuple[Training, Vignette]:
    """Lädt eine finale Vignette aus einem zugänglichen Training."""
    training: Training = _zugaengliches_training(request, training_pk)
    vignette: Vignette = get_object_or_404(
        training.vignetten.filter(zustand=Vignette.Zustand.FINAL), pk=vignette_pk
    )
    return training, vignette


@login_required
def katalog(request: HttpRequest) -> HttpResponse:
    """Zeigt beigetretene Trainings und dem Kreis zusätzlich seine eigenen Entwürfe."""
    ist_ausbilderin: bool = _ausbilderin_oder_administratorin(request.user)
    trainingsabfrage: QuerySet[Training] = (
        Training.objects.veroeffentlicht().zugaenglich_fuer(request.user)
    )
    sichtbare_pks: set[int] = set()
    eigene_trainings_pks: set[int] = set(
        Training.objects.filter(eigentuemerinnen=request.user).values_list(
            "pk", flat=True
        )
    )
    if ist_ausbilderin:
        sichtbare_trainings: QuerySet[Training] = Training.objects.sichtbar_fuer(
            request.user
        )
        trainingsabfrage = trainingsabfrage | sichtbare_trainings
        sichtbare_pks = set(sichtbare_trainings.values_list("pk", flat=True))

    trainings: list[dict[str, object]] = []
    for training in trainingsabfrage.distinct():
        ist_kuratierbar: bool = training.pk in sichtbare_pks
        url: str = reverse(
            "training:kuratieren" if ist_kuratierbar else "training:detail",
            args=[training.pk],
        )
        trainings.append(
            {
                "name": training.name,
                "zustand": training.get_zustand_display(),
                "zustand_badge": _zustand_badge(training),
                "is_own": training.pk in eigene_trainings_pks,
                "url": url,
                "action_label": "Kuratieren" if ist_kuratierbar else "Öffnen",
            }
        )
    return render(
        request,
        "training/katalog.html",
        {
            "trainings": trainings,
            "ist_ausbilderin": ist_ausbilderin,
        },
    )


@login_required
def historie(request: HttpRequest) -> HttpResponse:
    """Zeigt die Historie der durchgeführten Trainings aus Teilnehmer:innen-Sicht."""
    bindungen: QuerySet[Trainingsbindung] = Trainingsbindung.objects.filter(
        konto=request.user
    ).select_related("training", "teilnahme")

    trainings: list[dict[str, object]] = []
    for bindung in bindungen:
        training: Training = bindung.training
        vignetten_gesamt: int = training.vignetten.filter(
            zustand=Vignette.Zustand.FINAL
        ).count()
        abgeschlossene_vignetten: int = (
            Sitzung.objects.filter(
                teilnahme=bindung.teilnahme,
                status=Sitzung.Status.ABGESCHLOSSEN,
            )
            .values("vignette_id")
            .distinct()
            .count()
        )

        sitzungen_counts = (
            Sitzung.objects.filter(teilnahme=bindung.teilnahme)
            .values("status")
            .annotate(count=Count("id"))
        )
        sitzungen_nach_status = {
            "laufend": 0,
            "abgeschlossen": 0,
            "abgebrochen": 0,
            "gescheitert": 0,
        }
        for row in sitzungen_counts:
            sitzungen_nach_status[row["status"]] = row["count"]

        trainings.append(
            {
                "name": training.name,
                "url": reverse("training:detail", args=[training.pk]),
                "fortschritt": f"{abgeschlossene_vignetten} / {vignetten_gesamt}",
                "sort_progress": abgeschlossene_vignetten
                / (vignetten_gesamt if vignetten_gesamt else 1),
                "sitzungen_nach_status": sitzungen_nach_status,
            }
        )

    return render(
        request,
        "training/historie.html",
        {"trainings": trainings},
    )


@login_required
def abschriften(request: HttpRequest) -> HttpResponse:
    """Nimmt ein Teilnahme-Token entgegen und listet die geholten Abschriften."""

    if request.method == "POST":
        try:
            abschrift_holen(request.user, request.POST.get("token", ""))
        except ValidationError as ablehnung:
            messages.error(request, ablehnung.message)
        return redirect("training:abschriften")
    eigene: QuerySet[Abschrift] = Abschrift.objects.filter(konto=request.user).order_by(
        "-importiert_am"
    )
    return render(request, "training/abschriften.html", {"abschriften": eigene})


def _eigene_abschrift(request: HttpRequest, pk: int) -> Abschrift:
    """Lädt eine Abschrift des eingeloggten Kontos; jede fremde ist unbekannt."""

    return get_object_or_404(
        Abschrift.objects.filter(konto=request.user).select_related("teilnahme"), pk=pk
    )


def _gelesene_sitzungen(abschrift: Abschrift) -> list[dict[str, object]]:
    # Bereitet die kopierten Sitzungen zum Lesen auf. Die gespielte Folge steht
    # in der Vignettenposition; eine Sitzung ohne Position — die der Import
    # zulässt — hängt sich hinten an. Die Gesprächsschritte gehen vollständig in
    # den Kontext, Denkspur eingeschlossen: Die Sichtbarkeitszusage aus ADR-0005
    # hängt am Template, das die Denkspur nicht ausgibt.

    gespielte_folge: QuerySet[Sitzung] = (
        Sitzung.objects.filter(teilnahme=abschrift.teilnahme)
        .select_related("vignette__historie", "diagnose")
        .in_gespielter_folge()
    )
    return [
        {
            "vignette": sitzung.vignette,
            "status": sitzung.get_status_display(),
            "gespraechsschritte": sitzung.gespraechsschritte,
            # Eine Sitzung ohne Diagnose hat die Rückwärts-1:1 nicht; ihr
            # Zugriff wirft AttributeError.
            "diagnose": getattr(sitzung, "diagnose", None),
        }
        for sitzung in gespielte_folge
    ]


@login_required
def abschrift_ansehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine eigene Abschrift lesend in der gespielten Reihenfolge.

    Der Pfad ist ein eigener: Die Trainings-Sitzungsansichten laden über die
    Trainingsbindung und kennen Abschriften darum nicht.
    """

    abschrift: Abschrift = _eigene_abschrift(request, pk)
    freigegeben: list[Training] = list(abschrift.freigegeben_fuer.order_by("name"))
    return render(
        request,
        "training/abschrift.html",
        {
            "abschrift": abschrift,
            "sitzungen": _gelesene_sitzungen(abschrift),
            "freigegeben": [training.name for training in freigegeben],
            "freigegebene_pks": {training.pk for training in freigegeben},
            "beigetretene_trainings": Training.objects.beigetreten_von(
                request.user
            ).order_by("name"),
        },
    )


@login_required
def abschrift_freigaben(request: HttpRequest, pk: int) -> HttpResponse:
    """Speichert, für welche beigetretenen Trainings die Abschrift freigegeben ist.

    Ein Training ohne eigene Bindung ist für das Konto unbekannt.
    """

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    abschrift: Abschrift = _eigene_abschrift(request, pk)
    try:
        auswahl: list[int] = [int(wert) for wert in request.POST.getlist("training")]
    except ValueError:
        raise Http404
    try:
        abschrift_freigeben(abschrift, auswahl)
    except ValidationError:
        raise Http404
    return redirect("training:abschrift", pk=abschrift.pk)


@login_required
def abschrift_entfernen(request: HttpRequest, pk: int) -> HttpResponse:
    """Löscht eine eigene Abschrift mit ihrer Teilnahme und den Kopien."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    abschrift_loeschen(_eigene_abschrift(request, pk))
    return redirect("training:abschriften")


@login_required
@_ausbilderin_erforderlich
def liste(request: HttpRequest) -> HttpResponse:
    """Listet die für die eingeloggte Person sichtbaren Trainings."""
    trainings: list[dict[str, object]] = []
    for training in Training.objects.sichtbar_fuer(request.user):
        trainings.append(
            {
                "name": training.name,
                "zustand": training.get_zustand_display(),
                "zustand_badge": _zustand_badge(training),
                "url": reverse("training:kuratieren", args=[training.pk]),
            }
        )
    return render(
        request,
        "training/liste.html",
        {"trainings": trainings},
    )


@login_required
@_ausbilderin_erforderlich
def anlegen(request: HttpRequest) -> HttpResponse:
    """Legt ein Training für die eingeloggte Person an."""
    form: TrainingForm = TrainingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        training: Training = Training.objects.anlegen(request.user, **form.cleaned_data)
        return redirect("training:kuratieren", pk=training.pk)
    return render(request, "training/anlegen.html", {"form": form})


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt die Vignetten eines zugänglichen Trainings inkl. eigener Sitzungen."""
    training: Training = _zugaengliches_training(request, pk)
    vignetten: QuerySet[Vignette] = training.vignetten.filter(
        zustand=Vignette.Zustand.FINAL
    )
    sitzungen_nach_vignette: dict[int, list[Sitzung]] = {}
    bindung: Trainingsbindung | None = Trainingsbindung.objects.filter(
        training=training, konto=request.user
    ).first()
    if bindung is not None:
        sitzungen: QuerySet[Sitzung] = Sitzung.objects.filter(
            teilnahme=bindung.teilnahme
        ).order_by("-id")
        for sitzung in sitzungen:
            sitzungen_nach_vignette.setdefault(sitzung.vignette_id, []).append(sitzung)

    vignetten_daten: list[dict[str, object]] = []
    for vignette in vignetten:
        sitzungen = sitzungen_nach_vignette.get(vignette.pk, [])
        sitzungen_nach_status: dict[str, list[dict[str, object]]] = {
            "laufend": [],
            "abgeschlossen": [],
            "abgebrochen": [],
            "gescheitert": [],
        }
        for sitzung in sitzungen:
            sitzungen_nach_status[sitzung.status].append(
                {
                    "id": sitzung.pk,
                    "status": sitzung.get_status_display(),
                    "status_badge": _sitzung_status_badge(sitzung.status),
                    "url": reverse("training:sitzung_ansehen", args=[sitzung.pk]),
                }
            )

        vignetten_daten.append(
            {
                "name": vignette.historie.name or vignette.fach,
                "sitzungen_nach_status": sitzungen_nach_status,
                "url": reverse("training:wahl", args=[training.pk, vignette.pk]),
            }
        )

    return render(
        request,
        "training/detail.html",
        {"training": training, "vignetten_daten": vignetten_daten},
    )


@login_required
@_ausbilderin_erforderlich
def kuratieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt ein sichtbares Training zur Kuratierung."""
    training: Training = _sichtbares_training(request, pk)
    return render(
        request,
        "training/kuratieren.html",
        {
            "training": training,
            "zustand_badge": _zustand_badge(training),
            "trainings_link_url": request.build_absolute_uri(
                reverse("training:beitreten", args=[training.trainings_link])
            ),
            "beigetretene": training.trainingsbindung_set.count(),
            "fremdeinsicht": _fremdeinsicht(request.user, training),
            "freigegebene_abschriften": _freigegebene_abschriften(
                request.user, training
            ),
            "verfuegbare_vignetten": _eigene_finalen_vignetten(request).exclude(
                pk__in=training.vignetten.values("pk")
            ),
        },
    )


def _fremdeinsicht(konto: Konto, training: Training) -> dict[str, object]:
    # Baut die Tabelle der Fremdeinsicht: die Vignetten in Kuratierreihenfolge
    # als Spalten, alle Beigetretenen nach Namen als Zeilen. Eine Zelle hält die
    # abgeschlossenen Sitzungen der Person zu der Vignette, nummeriert je Zelle.

    vignetten: list[Vignette] = [
        eintrag.vignette
        for eintrag in Training.vignetten.through.objects.filter(training=training)
        .select_related("vignette__historie")
        .order_by("pk")
    ]
    sitzungen_nach_zelle: dict[tuple[int, int], list[Sitzung]] = {}
    for sitzung in (
        _fremd_einsehbare_sitzungen(konto)
        .filter(teilnahme__trainingsbindung__training=training)
        .order_by("erstellt_am", "pk")
    ):
        sitzungen_nach_zelle.setdefault(
            (sitzung.teilnahme_id, sitzung.vignette_id), []
        ).append(sitzung)

    zeilen: list[dict[str, object]] = []
    for bindung in training.trainingsbindung_set.select_related("konto"):
        zellen: list[list[dict[str, object]]] = [
            [
                {
                    "nummer": nummer,
                    "datum": sitzung.erstellt_am,
                    "url": reverse("training:sitzung_ansehen", args=[sitzung.pk]),
                }
                for nummer, sitzung in enumerate(
                    sitzungen_nach_zelle.get((bindung.teilnahme_id, vignette.pk), []),
                    start=1,
                )
            ]
            for vignette in vignetten
        ]
        zeilen.append(
            {
                "name": _kontoname(bindung.konto),
                "zellen": zellen,
                "ohne_sitzung": not any(zellen),
            }
        )
    zeilen.sort(key=lambda zeile: str(zeile["name"]).casefold())
    return {"vignetten": vignetten, "zeilen": zeilen}


def _kontoname(konto: Konto) -> str:
    """Der Name, unter dem die Fremdeinsicht eine Person zeigt."""
    return konto.get_full_name() or konto.username


def _freigegebene_abschriften(
    konto: Konto, training: Training
) -> list[dict[str, object]]:
    # Listet die für das Training freigegebenen Abschriften nach Namen, mit
    # Erhebungsname, Importzeitpunkt und ihren einsehbaren Sitzungen. Die
    # Sitzungen kommen aus derselben Regel wie die Tabelle.

    sitzungen_nach_teilnahme: dict[int, list[Sitzung]] = {}
    for sitzung in (
        _fremd_einsehbare_sitzungen(konto)
        .filter(teilnahme__abschrift__freigegeben_fuer=training)
        .select_related("vignette__historie")
        .in_gespielter_folge()
    ):
        sitzungen_nach_teilnahme.setdefault(sitzung.teilnahme_id, []).append(sitzung)

    abschriften: list[dict[str, object]] = [
        {
            "name": _kontoname(abschrift.konto),
            "erhebungsname": abschrift.erhebungsname,
            "importiert_am": abschrift.importiert_am,
            "sitzungen": [
                {
                    "name": sitzung.vignette.anzeigename,
                    "url": reverse("training:sitzung_ansehen", args=[sitzung.pk]),
                }
                for sitzung in sitzungen_nach_teilnahme.get(abschrift.teilnahme_id, [])
            ],
        }
        for abschrift in training.freigegebene_abschriften.select_related(
            "konto"
        ).order_by("importiert_am", "pk")
    ]
    abschriften.sort(key=lambda abschrift: str(abschrift["name"]).casefold())
    return abschriften


@login_required
@_ausbilderin_erforderlich
def trainingsexport(request: HttpRequest, pk: int) -> HttpResponse:
    """Lädt den Trainingsexport eines sichtbaren Trainings herunter."""
    training: Training = _sichtbares_training(request, pk)
    return zip_download(
        "training", training.pk, training.name, trainingsexport_zip(training)
    )


def _kreis_des_trainings(request: HttpRequest, pk: int) -> tuple[Training, str]:
    """Liefert das sichtbare Training als Kreis und seine Kuratierseite."""
    training: Training = _sichtbares_training(request, pk)
    return training, reverse("training:kuratieren", args=[training.pk])


eigentuemerin_hinzufuegen, eigentuemerin_entfernen = eigentuemer_views(
    rolle_erforderlich=_ausbilderin_erforderlich,
    aufloesen=_kreis_des_trainings,
    liste="training:liste",
)


@login_required
@_ausbilderin_erforderlich
def vignette_hinzufuegen(
    request: HttpRequest, pk: int, vignette_pk: int
) -> HttpResponse:
    """Nimmt eine eigene finale Vignette in ein sichtbares Training auf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    vignette: Vignette = get_object_or_404(
        _eigene_finalen_vignetten(request), pk=vignette_pk
    )
    training.vignetten.add(vignette)
    return redirect("training:kuratieren", pk=training.pk)


@login_required
@_ausbilderin_erforderlich
def vignette_entfernen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
    """Entfernt eine gebundene Vignette aus einem sichtbaren Training."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    vignette: Vignette = get_object_or_404(training.vignetten, pk=vignette_pk)
    training.vignetten.remove(vignette)
    return redirect("training:kuratieren", pk=training.pk)


@login_required
@_ausbilderin_erforderlich
def veroeffentlichen(request: HttpRequest, pk: int) -> HttpResponse:
    """Veröffentlicht einen sichtbaren Trainingsentwurf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    training.veroeffentlichen()
    return redirect("training:kuratieren", pk=training.pk)


@login_required
@_ausbilderin_erforderlich
def beitritt_sperren(request: HttpRequest, pk: int) -> HttpResponse:
    """Sperrt den Beitritt über den Trainings-Link."""
    return _beitritt_schalten(request, pk, gesperrt=True)


@login_required
@_ausbilderin_erforderlich
def beitritt_oeffnen(request: HttpRequest, pk: int) -> HttpResponse:
    """Öffnet einen gesperrten Beitritt wieder."""
    return _beitritt_schalten(request, pk, gesperrt=False)


def _beitritt_schalten(request: HttpRequest, pk: int, gesperrt: bool) -> HttpResponse:
    """Setzt die Beitrittssperre eines sichtbaren Trainings."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    training.beitritt_gesperrt = gesperrt
    training.save(update_fields=["beitritt_gesperrt"])
    return redirect("training:kuratieren", pk=training.pk)


@login_required
def beitreten(request: HttpRequest, trainings_link: UUID) -> HttpResponse:
    """Tritt einem veröffentlichten Training über seinen Trainings-Link bei.

    Wer schon dabei ist, landet auch bei gesperrtem Beitritt im Training.
    Kreis und Administration sehen das Training ohnehin und landen darin,
    offen wie gesperrt, ohne beizutreten; binden darf erst der Sitzungsstart.
    """
    training: Training = get_object_or_404(
        Training.objects.veroeffentlicht(), trainings_link=trainings_link
    )
    if Training.objects.sichtbar_fuer(request.user).filter(pk=training.pk).exists():
        return redirect("training:detail", pk=training.pk)
    if not training.beitreten(request.user):
        return render(
            request,
            "training/beitritt_gesperrt.html",
            {"training": training},
            status=403,
        )
    return redirect("training:detail", pk=training.pk)


@login_required
def wahl(request: HttpRequest, training_pk: int, vignette_pk: int) -> HttpResponse:
    """Bestätigt oder startet die Wahl einer Vignette aus einem Training."""
    training, vignette = _zugaengliches_training_mit_finaler_vignette(
        request, training_pk, vignette_pk
    )
    if request.method == "POST":
        bindung: Trainingsbindung = training.bindung_fuer(request.user)
        if bindung.teilnahme.audioverarbeitung_eingewilligt is None:
            return render(
                request,
                "training/einwilligung.html",
                {"training": training, "vignette": vignette},
            )
        return _sitzung_starten(request, bindung, vignette)
    return render(
        request,
        "training/wahl.html",
        {"training": training, "vignette": vignette},
    )


@login_required
def einwilligung(
    request: HttpRequest, training_pk: int, vignette_pk: int
) -> HttpResponse:
    """Hält die Entscheidung zur externen Audioverarbeitung an der Teilnahme fest."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training, vignette = _zugaengliches_training_mit_finaler_vignette(
        request, training_pk, vignette_pk
    )
    bindung: Trainingsbindung = training.bindung_fuer(request.user)
    if bindung.teilnahme.audioverarbeitung_eingewilligt is not None:
        return HttpResponseBadRequest("Die Einwilligung wurde bereits festgehalten.")
    entscheidung: str | None = request.POST.get("audioverarbeitung_eingewilligt")
    if entscheidung not in {"ja", "nein"}:
        return HttpResponseBadRequest("Bitte stimmen Sie zu oder lehnen Sie ab.")
    bindung.teilnahme.audioverarbeitung_eingewilligt = entscheidung == "ja"
    bindung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])
    return _sitzung_starten(request, bindung, vignette)


def _sitzungsnavigation() -> Sitzungsnavigation:
    # Bündelt die modusspezifischen Routen für die Trainingssitzungsansicht.

    return Sitzungsnavigation(
        bezeichnung="Training",
        gespraech_url=reverse("training:gespraech"),
        beenden_url=reverse("training:gespraech_beenden"),
        debrief_url=reverse("training:debrief"),
        abbrechen_url=reverse("training:abbrechen"),
        transkription_url=reverse("training:transkription"),
    )


def training_sitzung(request: HttpRequest) -> Sitzung:
    """Lädt die aktuelle Sitzung nur für das zugehörige Trainingskonto."""

    sitzung_pk: int | None = request.session.get("training_sitzung_pk")
    if sitzung_pk is None:
        raise PermissionDenied
    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme"),
        pk=sitzung_pk,
    )
    get_object_or_404(
        Trainingsbindung.objects.filter(konto=request.user), teilnahme=sitzung.teilnahme
    )
    return sitzung


def _zur_auswahl_zurueckkehren(request: HttpRequest, sitzung: Sitzung) -> HttpResponse:
    """Löst die aktive Sitzung und kehrt zur Auswahl ihres Trainings zurück."""

    training_pk: int = get_object_or_404(
        Trainingsbindung, teilnahme=sitzung.teilnahme
    ).training_id
    request.session.pop("training_sitzung_pk", None)
    return redirect("training:detail", pk=training_pk)


def _sitzung_starten(
    request: HttpRequest, bindung: Trainingsbindung, vignette: Vignette
) -> HttpResponse:
    """Bindet das Konto atomar und startet die Sitzung über den DB-Sink."""

    with transaction.atomic():
        sink: DBSink = DBSink(bindung.teilnahme)
        sitzung_starten(
            sink,
            vignette,
            ModellKonfiguration.objects.belegte(Verwendung.SCHUELERIN),
        )
        kern: Simulationskern = sink.sitzung.simulationskern
    request.session["training_sitzung_pk"] = sink.sitzung.pk
    return sitzung_anzeigen(
        request,
        vignette=vignette,
        kern=kern,
        gespraechsschritte=[],
        ist_probelauf=False,
        navigation=_sitzungsnavigation(),
        spracheingabe_verfuegbar=bindung.teilnahme.hat_in_audioverarbeitung_eingewilligt,
        sitzung_pk=sink.sitzung.pk,
    )


@login_required
def gespraech(request: HttpRequest) -> HttpResponse:
    """Führt den nächsten persistierten Gesprächsschritt einer Trainingssitzung aus."""

    return persistiertes_gespraech(
        request, training_sitzung(request), _sitzungsnavigation()
    )


@login_required
def gespraech_beenden(request: HttpRequest) -> HttpResponse:
    """Beendet das Diagnosegespräch vorzeitig und zeigt seinen Debrief."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = training_sitzung(request)
    navigation: Sitzungsnavigation = _sitzungsnavigation()
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return persistierten_fehler_anzeigen(request, sitzung, navigation)
    sink: DBSink = DBSink.fuer_sitzung(sitzung)
    sitzung_beenden(sink)
    return persistierten_debrief_anzeigen(request, sitzung, navigation)


@login_required
def abbrechen(request: HttpRequest) -> HttpResponse:
    """Bricht eine Trainingssitzung ohne Diagnose gewollt ab."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = training_sitzung(request)
    navigation: Sitzungsnavigation = _sitzungsnavigation()
    if sitzung.status == Sitzung.Status.GESCHEITERT:
        return persistierten_fehler_anzeigen(request, sitzung, navigation)
    if sitzung.status == Sitzung.Status.ABGESCHLOSSEN:
        return persistierten_debrief_anzeigen(request, sitzung, navigation)
    if sitzung.status == Sitzung.Status.ABGEBROCHEN:
        return _zur_auswahl_zurueckkehren(request, sitzung)
    sink: DBSink = DBSink.fuer_sitzung(sitzung)
    sitzung_abbrechen(sink)
    return _zur_auswahl_zurueckkehren(request, sitzung)


@login_required
def debrief(request: HttpRequest) -> HttpResponse:
    """Speichert die Diagnose und kehrt zur freien Trainingswahl zurück."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    sitzung: Sitzung = training_sitzung(request)
    with transaction.atomic():
        sitzung = Sitzung.objects.select_for_update().get(pk=sitzung.pk)
        if sitzung.status == Sitzung.Status.GESCHEITERT:
            return persistierten_fehler_anzeigen(
                request, sitzung, _sitzungsnavigation()
            )
        if sitzung.status != Sitzung.Status.LAUFEND:
            return _zur_auswahl_zurueckkehren(request, sitzung)
        DBSink.fuer_sitzung(sitzung).diagnose_setzen(
            request.POST["diagnose"],
            eingabemodus=Eingabemodus.aus_formular(request.POST.get("eingabemodus")),
        )
    return _zur_auswahl_zurueckkehren(request, sitzung)


@login_required
def sitzung_ansehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine Trainingssitzung schreibgeschützt an.

    Die eigene Sitzung in jedem Status (Selbsteinsicht), eine fremde nur über
    die Fremdeinsicht; alles andere ist unbekannt.
    """

    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.filter(
            Q(teilnahme__trainingsbindung__konto=request.user)
            | Q(pk__in=_fremd_einsehbare_sitzungen(request.user).values("pk"))
        ).select_related("vignette", "simulationskern", "teilnahme"),
        pk=pk,
    )

    return sitzung_anzeigen(
        request,
        vignette=sitzung.vignette,
        kern=sitzung.simulationskern,
        gespraechsschritte=sitzung.gespraechsschritte,
        ist_probelauf=False,
        navigation=_sitzungsnavigation(),
        zeigt_debrief=(sitzung.status == Sitzung.Status.ABGESCHLOSSEN),
        ist_lesend=True,
        abgegebene_diagnose=DBSink.fuer_sitzung(sitzung).abgegebene_diagnose,
    )

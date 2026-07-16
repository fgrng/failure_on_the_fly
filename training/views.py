"""Views für Trainingskatalog und Ausbilder-UI."""

from functools import wraps
from typing import TYPE_CHECKING, Callable, Concatenate, ParamSpec

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import TrainingForm
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.models import Sitzung
from sitzungen.orchestrierung import sitzung_starten
from sitzungen.rahmen import rahmen_rendern
from sitzungen.sink import DBSink
from sitzungen.views import sitzungsnavigation

from vignetten.models import Vignette, Vignettenhistorie

from .models import Training, Trainingsbindung

if TYPE_CHECKING:
    from konten.models import Konto


_AUSBILDERIN_GRUPPE: str = "Ausbilder:in"
_ADMINISTRATORIN_GRUPPE: str = "Administrator:in"
P = ParamSpec("P")


def _ausbilderin_oder_administratorin(konto: "Konto") -> bool:
    """Prüft, ob ein Konto die Ausbilder-UI erreichen darf."""

    return konto.groups.filter(
        name__in=[_AUSBILDERIN_GRUPPE, _ADMINISTRATORIN_GRUPPE]
    ).exists()


def _ausbilderin_erforderlich(
    view: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """Schützt eine View der Ausbilder-UI mit der Rollenprüfung."""

    @wraps(view)
    def geschuetzte_view(
        request: HttpRequest,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> HttpResponse:
        if not _ausbilderin_oder_administratorin(request.user):
            return HttpResponse(status=403)
        return view(request, *args, **kwargs)

    return geschuetzte_view


def _eigene_finalen_vignetten(request: HttpRequest) -> QuerySet[Vignette]:
    """Liefert einbindbare Fassungen aus dem Eigentümer-Kreis."""

    return Vignette.objects.einbindbar().filter(
        historie__in=Vignettenhistorie.objects.sichtbar_fuer(request.user)
    )


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


def _veroeffentlichtes_training(pk: int) -> Training:
    """Lädt ein Training, das im offenen Katalog sichtbar ist."""
    return get_object_or_404(Training.objects.veroeffentlicht(), pk=pk)


def _veroeffentlichtes_training_mit_finaler_vignette(
    training_pk: int, vignette_pk: int
) -> tuple[Training, Vignette]:
    """Lädt eine finale Vignette aus einem veröffentlichten Training."""
    training: Training = _veroeffentlichtes_training(training_pk)
    vignette: Vignette = get_object_or_404(
        training.vignetten.filter(zustand=Vignette.Zustand.FINAL), pk=vignette_pk
    )
    return training, vignette


@login_required
def katalog(request: HttpRequest) -> HttpResponse:
    """Zeigt allen eingeloggten Konten veröffentlichte Trainings und ggf. eigene Entwürfe."""
    ist_ausbilderin: bool = _ausbilderin_oder_administratorin(request.user)
    trainingsabfrage: QuerySet[Training] = Training.objects.veroeffentlicht()
    sichtbare_pks: set[int] = set()
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
                "is_own": training.eigentuemerin_id == request.user.id,
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
        abgeschlossene_vignetten: int = Sitzung.objects.filter(
            teilnahme=bindung.teilnahme,
            status=Sitzung.Status.ABGESCHLOSSEN,
        ).values("vignette_id").distinct().count()
        
        sitzungen_counts = Sitzung.objects.filter(
            teilnahme=bindung.teilnahme
        ).values("status").annotate(count=Count("id"))
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
        training: Training = form.save(commit=False)
        training.eigentuemerin = request.user
        training.save()
        return redirect("training:kuratieren", pk=training.pk)
    return render(request, "training/anlegen.html", {"form": form})


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt die frei wählbaren Vignetten eines veröffentlichten Trainings inkl. eigener Sitzungen."""
    training: Training = _veroeffentlichtes_training(pk)
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
                    "url": reverse(
                        "sitzungen:training_sitzung_ansehen", args=[sitzung.pk]
                    ),
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
            "verfuegbare_vignetten": _eigene_finalen_vignetten(request).exclude(
                pk__in=training.vignetten.values("pk")
            ),
        },
    )


@login_required
@_ausbilderin_erforderlich
def vignette_hinzufuegen(request: HttpRequest, pk: int, vignette_pk: int) -> HttpResponse:
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
def wahl(request: HttpRequest, training_pk: int, vignette_pk: int) -> HttpResponse:
    """Bestätigt oder startet die Wahl einer Vignette aus einem Training."""
    training, vignette = _veroeffentlichtes_training_mit_finaler_vignette(
        training_pk, vignette_pk
    )
    if request.method == "POST":
        bindung: Trainingsbindung = _trainingsbindung_laden_oder_anlegen(
            request, training
        )
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
    training, vignette = _veroeffentlichtes_training_mit_finaler_vignette(
        training_pk, vignette_pk
    )
    bindung: Trainingsbindung = _trainingsbindung_laden_oder_anlegen(request, training)
    if bindung.teilnahme.audioverarbeitung_eingewilligt is not None:
        return HttpResponseBadRequest("Die Einwilligung wurde bereits festgehalten.")
    entscheidung: str | None = request.POST.get("audioverarbeitung_eingewilligt")
    if entscheidung not in {"ja", "nein"}:
        return HttpResponseBadRequest("Bitte stimmen Sie zu oder lehnen Sie ab.")
    bindung.teilnahme.audioverarbeitung_eingewilligt = entscheidung == "ja"
    bindung.teilnahme.save(update_fields=["audioverarbeitung_eingewilligt"])
    return _sitzung_starten(request, bindung, vignette)


def _trainingsbindung_laden_oder_anlegen(
    request: HttpRequest, training: Training
) -> Trainingsbindung:
    """Lädt oder erzeugt die eine Trainingsbindung der teilnehmenden Person."""
    with transaction.atomic():
        bindung: Trainingsbindung | None = Trainingsbindung.objects.filter(
            training=training, konto=request.user
        ).select_related("teilnahme").first()
        if bindung is None:
            from sitzungen.models import Teilnahme

            try:
                with transaction.atomic():
                    bindung = Trainingsbindung.objects.create(
                        teilnahme=Teilnahme.objects.create(),
                        training=training,
                        konto=request.user,
                    )
            except IntegrityError:
                bindung = Trainingsbindung.objects.select_related("teilnahme").get(
                    training=training, konto=request.user
                )
    return bindung


def _sitzung_starten(
    request: HttpRequest, bindung: Trainingsbindung, vignette: Vignette
) -> HttpResponse:
    """Bindet das Konto atomar und startet die Sitzung über den DB-Sink."""

    with transaction.atomic():
        kern: Simulationskern | None = vignette.gepinnter_kern
        if kern is None:
            raise RuntimeError("Trainingsvignetten brauchen einen gepinnten Simulationskern.")
        sink: DBSink = DBSink(bindung.teilnahme)
        sitzung_starten(
            sink,
            vignette,
            kern,
            ModellKonfiguration.objects.aktive(),
        )
    request.session["training_sitzung_pk"] = sink.sitzung.pk
    return render(
        request,
        "sitzungen/sitzung.html",
        {
            "vignette": vignette,
            "einleitung": rahmen_rendern(kern.rahmenhandlung_einleitung, vignette),
            "gespraechseinleitung": rahmen_rendern(
                kern.rahmenhandlung_gespraechseinleitung, vignette
            ),
            "gespraechsschritte": [],
            "ist_probelauf": False,
            "navigation": sitzungsnavigation(ist_probelauf=False),
            "spracheingabe_verfuegbar": bindung.teilnahme.hat_in_audioverarbeitung_eingewilligt,
            "zeigt_debrief": False,
            "ist_lesend": False,
        },
    )

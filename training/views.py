"""Views für Trainingskatalog und Ausbilder-UI."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count, QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from konten.models import Konto
from konten.navigation import (
    AUSBILDERIN_GRUPPE,
    rolle_erforderlich,
    rolle_oder_administration,
)

from .forms import TrainingForm
from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.durchlauf import (
    Sitzungsnavigation,
    sitzung_abbrechen,
    sitzung_anzeigen,
    sitzung_beenden,
    sitzung_starten,
)
from sitzungen.models import Sitzung
from sitzungen.sink import DBSink
from sitzungen.views import (
    persistierten_debrief_anzeigen,
    persistierten_fehler_anzeigen,
    persistiertes_gespraech,
)

from vignetten.models import Vignette

from .models import Training, Trainingsbindung


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
    eigentuemerinnen: list[Konto] = list(training.eigentuemerinnen.all())
    return render(
        request,
        "training/kuratieren.html",
        {
            "training": training,
            "zustand_badge": _zustand_badge(training),
            "eigentuemerinnen": eigentuemerinnen,
            "hat_mehrere_eigentuemerinnen": len(eigentuemerinnen) > 1,
            "moegliche_koautorinnen": training.moegliche_ergaenzungen(),
            "verfuegbare_vignetten": _eigene_finalen_vignetten(request).exclude(
                pk__in=training.vignetten.values("pk")
            ),
        },
    )


@login_required
@_ausbilderin_erforderlich
def koautorin_hinzufuegen(request: HttpRequest, pk: int) -> HttpResponse:
    """Nimmt eine weitere Ko-Autorin in den Eigentümer-Kreis auf."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    konto: Konto = get_object_or_404(
        training.moegliche_ergaenzungen(), pk=request.POST.get("konto")
    )
    training.eigentuemerinnen.add(konto)
    return redirect("training:kuratieren", pk=training.pk)


@login_required
@_ausbilderin_erforderlich
def koautorin_entfernen(request: HttpRequest, pk: int, konto_pk: int) -> HttpResponse:
    """Trägt eine Eigentümerin aus dem Kreis des Trainings aus.

    Wer sich selbst austrägt, landet auf der Trainingsliste; scheitert der
    Austritt an der Invariante, bleibt es bei der Kuratierseite.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    training: Training = _sichtbares_training(request, pk)
    if training.austreten(konto_pk) and konto_pk == request.user.pk:
        return redirect("training:liste")
    return redirect("training:kuratieren", pk=training.pk)


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
        bindung: Trainingsbindung | None = (
            Trainingsbindung.objects.filter(training=training, konto=request.user)
            .select_related("teilnahme")
            .first()
        )
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
        kern: Simulationskern | None = vignette.gepinnter_kern
        if kern is None:
            raise RuntimeError(
                "Trainingsvignetten brauchen einen gepinnten Simulationskern."
            )
        sink: DBSink = DBSink(bindung.teilnahme)
        sitzung_starten(
            sink,
            vignette,
            kern,
            ModellKonfiguration.objects.aktive(),
        )
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
    sink: DBSink = DBSink.fuer_sitzung(sitzung, session=request.session)
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
    sink: DBSink = DBSink.fuer_sitzung(sitzung, session=request.session)
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
        DBSink.fuer_sitzung(sitzung).diagnose_setzen(request.POST["diagnose"])
    return _zur_auswahl_zurueckkehren(request, sitzung)


@login_required
def sitzung_ansehen(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt eine vergangene Trainingssitzung schreibgeschützt an."""

    sitzung: Sitzung = get_object_or_404(
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme"),
        pk=pk,
    )
    get_object_or_404(
        Trainingsbindung.objects.filter(konto=request.user), teilnahme=sitzung.teilnahme
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
    )

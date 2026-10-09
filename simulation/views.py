"""Ansichten für den Simulationskern."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from konten.navigation import administratorin_erforderlich, autorin_erforderlich


from .forms import (
    EvalkatalogDurchlaufForm,
    ModellKonfigurationForm,
    SimulationskernForm,
    TranskriptionsKonfigurationForm,
)
from .lebenszyklus import VersionierteFassung
from .modellverzeichnis import (
    Modellverzeichnis,
    Modellverzeichnisfehler,
    Modellvorschlag,
    Naht,
    modellverzeichnis,
)
from .models import (
    PROMPT_PLATZHALTER_MIT_UMGEBUNG,
    VERTRAG_PROMPT,
    VERTRAG_BEWERTER,
    VERTRAG_LEHRPERSON,
    VERTRAG_RAHMEN,
    Eval,
    Evalinput,
    Evalkatalog,
    Evalkriterium,
    Inputschritt,
    Katalogteil,
    ModellKonfiguration,
    Simulationskern,
    TranskriptionsKonfiguration,
    UebergreifendesKriterium,
    Verwendung,
)
from .standardkern import STANDARDKERN_VORLAGEN


def _archivierte_fassungen[F: VersionierteFassung](modell: type[F]) -> QuerySet[F]:
    # Liefert die überholten Fassungen einer Linie, die zuletzt überholte zuerst.

    return modell.objects.filter(zustand=modell.Zustand.ARCHIVIERT).order_by(
        "-finalisiert_am", "-pk"
    )


def _kern_kontext() -> dict[str, object]:
    """Liefert die gemeinsame Anzeige-Referenz für Kern-Ansichten."""
    return {
        "modell_konfiguration": ModellKonfiguration.objects.aktive(
            Verwendung.SCHUELERIN
        ),
        "prompt_platzhalter": sorted(VERTRAG_PROMPT),
        "prompt_platzhalter_mit_umgebung": PROMPT_PLATZHALTER_MIT_UMGEBUNG,
        "rahmen_platzhalter": sorted(VERTRAG_RAHMEN),
    }


def _fassung_im_zustand_laden(
    request: HttpRequest,
    pk: int,
    zustand: Simulationskern.Zustand,
) -> Simulationskern | None:
    # Lädt eine Fassung im erwarteten Zustand oder erklärt die Ablehnung.

    simulationskern: Simulationskern = get_object_or_404(Simulationskern, pk=pk)
    if simulationskern.zustand != zustand:
        messages.error(request, "Diese Kern-Fassung hat nicht den erwarteten Zustand.")
        return None
    return simulationskern


def _lebenszyklus_aktion_ausfuehren(
    request: HttpRequest,
    pk: int,
    zustand: Simulationskern.Zustand,
    aktion: Callable[[Simulationskern], object],
) -> HttpResponse:
    # Führt eine zustandsgebundene Aktion aus und zeigt Modellfehler an.

    simulationskern: Simulationskern | None = _fassung_im_zustand_laden(
        request, pk, zustand
    )
    if simulationskern is None:
        return redirect("simulation:kern_verwalten")
    try:
        aktion(simulationskern)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect("simulation:kern_verwalten")


@login_required
@autorin_erforderlich
def kern(request: HttpRequest) -> HttpResponse:
    """Zeigt die finale Kern-Fassung und die aktive Modell-Konfiguration."""
    simulationskern: Simulationskern | None = Simulationskern.objects.finale_fassung()
    return render(
        request,
        "simulation/kern.html",
        {
            "simulationskern": simulationskern,
            **_kern_kontext(),
        },
    )


@administratorin_erforderlich
def kern_verwalten(request: HttpRequest) -> HttpResponse:
    """Zeigt alle Kern-Fassungen für die Administration."""
    return render(
        request,
        "simulation/kern_verwalten.html",
        {
            "entwurf": Simulationskern.objects.filter(
                zustand=Simulationskern.Zustand.ENTWURF
            ).first(),
            "finale_fassung": Simulationskern.objects.finale_fassung(),
            "archivierte_fassungen": _archivierte_fassungen(Simulationskern),
            # Dieselbe Bedingung, die die Anlege-Naht prüft: Nur solange die
            # Historie leer ist, nimmt sie eine erste Fassung an.
            "kern_fehlt": not Simulationskern.objects.exists(),
            **_kern_kontext(),
        },
    )


@administratorin_erforderlich
@require_POST
def kern_anlegen(request: HttpRequest, *, mit_vorlage: bool) -> HttpResponse:
    """Legt die erste Kern-Fassung als Entwurf an — leer oder aus dem Standardkern.

    Welcher Inhalt entsteht, entscheidet die Route und nicht die Anfrage. Die
    Naht selbst lehnt jede zweite erste Fassung ab; die Ablehnung erreicht die
    Administratorin als Meldung auf der Übersicht.
    """
    try:
        Simulationskern.objects.anlegen(
            **(STANDARDKERN_VORLAGEN if mit_vorlage else {})
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect("simulation:kern_verwalten")


@administratorin_erforderlich
def kern_bearbeiten(request: HttpRequest, pk: int) -> HttpResponse:
    """Bearbeitet die Inhaltsfelder eines Kern-Entwurfs."""
    simulationskern: Simulationskern = get_object_or_404(
        Simulationskern.objects.filter(zustand=Simulationskern.Zustand.ENTWURF),
        pk=pk,
    )
    form: SimulationskernForm
    if request.method == "POST":
        form = SimulationskernForm(request.POST, instance=simulationskern)
        if form.is_valid():
            form.save()
            return redirect("simulation:kern_verwalten")
    else:
        form = SimulationskernForm(instance=simulationskern)
    return render(
        request,
        "simulation/kern_bearbeiten.html",
        {"form": form, "simulationskern": simulationskern, **_kern_kontext()},
    )


@administratorin_erforderlich
@require_POST
def neue_fassung(request: HttpRequest, pk: int) -> HttpResponse:
    """Zieht aus einer finalen Kern-Fassung einen Entwurf."""
    return _lebenszyklus_aktion_ausfuehren(
        request,
        pk,
        Simulationskern.Zustand.FINAL,
        Simulationskern.bearbeiten,
    )


@administratorin_erforderlich
@require_POST
def finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert einen Kern-Entwurf."""
    return _lebenszyklus_aktion_ausfuehren(
        request,
        pk,
        Simulationskern.Zustand.ENTWURF,
        Simulationskern.finalisieren,
    )


@administratorin_erforderlich
@require_POST
def verwerfen(request: HttpRequest, pk: int) -> HttpResponse:
    """Verwirft einen Kern-Entwurf."""
    return _lebenszyklus_aktion_ausfuehren(
        request,
        pk,
        Simulationskern.Zustand.ENTWURF,
        Simulationskern.delete,
    )


@administratorin_erforderlich
def evalkatalog(request: HttpRequest) -> HttpResponse:
    """Zeigt den Stand des Evalkatalogs; ohne Katalog bietet die Seite das Anlegen an."""
    return render(
        request,
        "simulation/evalkatalog.html",
        {
            "entwurf": Evalkatalog.objects.filter(
                zustand=Evalkatalog.Zustand.ENTWURF
            ).first(),
            "finale_fassung": Evalkatalog.objects.finale_fassung(),
            "ueberholte_fassungen": _archivierte_fassungen(Evalkatalog),
            # Dieselbe Bedingung, die die Anlege-Naht prüft.
            "katalog_fehlt": not Evalkatalog.objects.exists(),
        },
    )


@administratorin_erforderlich
@require_POST
def evalkatalog_anlegen(request: HttpRequest) -> HttpResponse:
    """Legt den ersten Evalkatalog als leeren Entwurf an und öffnet den Editor."""
    try:
        katalog: Evalkatalog = Evalkatalog.objects.anlegen()
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("simulation:evalkatalog")
    return redirect("simulation:evalkatalog_editor", pk=katalog.pk)


@dataclass(frozen=True)
class _Platzhalterknopf:
    # Ein Platzhalter unter einer Vorlage; eigen heißt: nur diese Vorlage kennt ihn.

    name: str
    eigen: bool


def _platzhalterknoepfe(
    vertrag: frozenset[str], gegenstueck: frozenset[str]
) -> list[_Platzhalterknopf]:
    # Vorlageneigen ist, was das Gegenstück nicht kennt; es steht vorn, die
    # übrigen alphabetisch.

    return [
        _Platzhalterknopf(name, name not in gegenstueck)
        for name in sorted(vertrag, key=lambda name: (name in gegenstueck, name))
    ]


def _fassung(request: HttpRequest, pk: int) -> Evalkatalog:
    # Liefert die Katalog-Fassung der Anfrage. Nur ein POST schreibt und
    # erreicht deshalb nur Entwürfe; lesend öffnen sich auch finale und
    # überholte Fassungen.

    fassungen: QuerySet[Evalkatalog] = Evalkatalog.objects.all()
    if request.method == "POST":
        fassungen = fassungen.filter(zustand=Evalkatalog.Zustand.ENTWURF)
    return get_object_or_404(fassungen, pk=pk)


def _editor_kontext(katalog: Evalkatalog, knoten: str) -> dict[str, object]:
    # Was jeder Knoten braucht; außerhalb von Entwürfen sind die Felder
    # gesperrt und die Bearbeitungsknöpfe fehlen.

    return {
        "katalog": katalog,
        "knoten": knoten,
        "gesperrt": katalog.zustand != Evalkatalog.Zustand.ENTWURF,
        "neue_fassung_moeglich": katalog.zustand == Evalkatalog.Zustand.FINAL
        and not Evalkatalog.objects.filter(
            zustand=Evalkatalog.Zustand.ENTWURF
        ).exists(),
    }


@administratorin_erforderlich
def evalkatalog_editor(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt den Knoten Durchlauf und Vorlagen; speichert nur in Entwürfe."""
    katalog: Evalkatalog = _fassung(request, pk)
    form: EvalkatalogDurchlaufForm
    if request.method == "POST":
        form = EvalkatalogDurchlaufForm(request.POST, instance=katalog)
        if form.is_valid():
            form.save()
            messages.success(request, "Durchlauf und Vorlagen gespeichert.")
            return redirect("simulation:evalkatalog_editor", pk=katalog.pk)
    else:
        form = EvalkatalogDurchlaufForm(instance=katalog)
    kontext: dict[str, object] = _editor_kontext(katalog, "durchlauf")
    if kontext["gesperrt"]:
        for feld in form.fields.values():
            feld.disabled = True
    return render(
        request,
        "simulation/evalkatalog_editor.html",
        {
            **kontext,
            "form": form,
            "vorlagen": [
                (
                    form["lehrperson_vorlage"],
                    _platzhalterknoepfe(VERTRAG_LEHRPERSON, VERTRAG_BEWERTER),
                ),
                (
                    form["bewerter_vorlage"],
                    _platzhalterknoepfe(VERTRAG_BEWERTER, VERTRAG_LEHRPERSON),
                ),
            ],
        },
    )


def _eingaben_uebernehmen(katalog: Evalkatalog, request: HttpRequest) -> bool:
    # Jede Geste im Editor sendet das ganze Formular; so gehen getippte Werte
    # beim Hinzufügen, Löschen oder Umordnen nicht verloren, egal an welchem
    # Knoten sie stehen. Ein ungültiger Wert des Durchlaufs bleibt
    # ungespeichert und wird gemeldet; dann ist das Ergebnis False.

    uebernommen: bool = True
    if "k" in request.POST:
        form: EvalkatalogDurchlaufForm = EvalkatalogDurchlaufForm(
            request.POST, instance=katalog
        )
        if form.is_valid():
            form.save()
        else:
            # Nur gültige Felder stehen in cleaned_data und sind schon
            # in die Instanz übernommen.
            katalog.save(update_fields=list(form.cleaned_data))
            for feld, meldungen in form.errors.items():
                for meldung in meldungen:
                    messages.error(request, f"{form[feld].label}: {meldung}")
            uebernommen = False
    schritte: QuerySet[Inputschritt] = Inputschritt.objects.filter(
        evalinput__eval__katalog=katalog
    )
    teile: tuple[tuple[QuerySet[Katalogteil], str, str], ...] = (
        (katalog.uebergreifende_kriterien.all(), "kriterium", "text"),
        (katalog.evals.all(), "eval", "name"),
        (Evalkriterium.objects.filter(eval__katalog=katalog), "evalkriterium", "text"),
        (schritte, "inputschritt", "text"),
        (schritte, "inputschritt-art", "art"),
    )
    for queryset, praefix, feld in teile:
        for teil in queryset:
            wert: str | None = request.POST.get(f"{praefix}-{teil.pk}")
            if wert is None or wert == getattr(teil, feld):
                continue
            # Wie bei „Durchlauf und Vorlagen“ bleibt ein ungültiger Wert
            # ungespeichert, etwa ein Name über der Feldlänge.
            try:
                teil._meta.get_field(feld).clean(wert, teil)
            except ValidationError:
                continue
            setattr(teil, feld, wert)
            teil.save(update_fields=[feld])
    return uebernommen


@dataclass(frozen=True)
class _Listenzeile:
    # Eine Zeile einer Kriterien- oder Schrittliste samt den Zielen ihrer Gesten.

    feld: str
    text: str
    hoch: str
    runter: str
    loeschen: str


def _listenzeilen(
    teile: QuerySet[Katalogteil], praefix: str, route: str, *args: int
) -> list[_Listenzeile]:
    # Baut die Zeilen einer Kriterien- oder Schrittliste; `route` ist der
    # Namensstamm der Gesten.

    return [
        _Listenzeile(
            feld=f"{praefix}-{teil.pk}",
            text=teil.text,
            hoch=reverse(f"{route}_verschieben", args=[*args, teil.pk, "hoch"]),
            runter=reverse(f"{route}_verschieben", args=[*args, teil.pk, "runter"]),
            loeschen=reverse(f"{route}_loeschen", args=[*args, teil.pk]),
        )
        for teil in teile
    ]


@administratorin_erforderlich
def evalkatalog_kriterien(request: HttpRequest, pk: int) -> HttpResponse:
    """Zeigt den Knoten Übergreifende Kriterien; speichert nur in Entwürfe."""
    if request.method == "POST":
        with transaction.atomic():
            katalog: Evalkatalog = _fassung(request, pk)
            if _eingaben_uebernehmen(katalog, request):
                messages.success(request, "Übergreifende Kriterien gespeichert.")
        return redirect("simulation:evalkatalog_kriterien", pk=katalog.pk)
    katalog: Evalkatalog = _fassung(request, pk)
    return render(
        request,
        "simulation/evalkatalog_editor.html",
        {
            **_editor_kontext(katalog, "kriterien"),
            "zeilen": _listenzeilen(
                katalog.uebergreifende_kriterien.all(),
                "kriterium",
                "simulation:evalkatalog_kriterium",
                katalog.pk,
            ),
        },
    )


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_kriterium_anlegen(request: HttpRequest, pk: int) -> HttpResponse:
    """Hängt ein leeres übergreifendes Kriterium ans Ende der Liste."""
    katalog: Evalkatalog = _fassung(request, pk)
    _eingaben_uebernehmen(katalog, request)
    katalog.kriterium_anlegen()
    return redirect("simulation:evalkatalog_kriterien", pk=katalog.pk)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_kriterium_loeschen(
    request: HttpRequest, pk: int, kriterium_pk: int
) -> HttpResponse:
    """Löscht ein übergreifendes Kriterium des Entwurfs."""
    katalog: Evalkatalog = _fassung(request, pk)
    kriterium: UebergreifendesKriterium = get_object_or_404(
        katalog.uebergreifende_kriterien, pk=kriterium_pk
    )
    _eingaben_uebernehmen(katalog, request)
    kriterium.delete()
    messages.success(request, "Das Kriterium wurde gelöscht.")
    return redirect("simulation:evalkatalog_kriterien", pk=katalog.pk)


_RICHTUNGEN: dict[str, int] = {"hoch": -1, "runter": 1}


def _versatz(richtung: str) -> int:
    # Hoch ist -1, runter +1; andere Richtungen gibt es nicht.

    if richtung not in _RICHTUNGEN:
        raise Http404
    return _RICHTUNGEN[richtung]


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_kriterium_verschieben(
    request: HttpRequest, pk: int, kriterium_pk: int, richtung: str
) -> HttpResponse:
    """Rückt ein übergreifendes Kriterium eine Zeile hoch oder runter."""
    versatz: int = _versatz(richtung)
    katalog: Evalkatalog = _fassung(request, pk)
    kriterium: UebergreifendesKriterium = get_object_or_404(
        katalog.uebergreifende_kriterien, pk=kriterium_pk
    )
    _eingaben_uebernehmen(katalog, request)
    kriterium.verschieben(versatz)
    return redirect("simulation:evalkatalog_kriterien", pk=katalog.pk)


def _eval_der_fassung(
    request: HttpRequest, pk: int, eval_pk: int
) -> tuple[Evalkatalog, Eval]:
    # Das Eval muss zur genannten Fassung gehören (siehe _fassung).

    katalog: Evalkatalog = _fassung(request, pk)
    return katalog, get_object_or_404(katalog.evals, pk=eval_pk)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_eval_anlegen(request: HttpRequest, pk: int) -> HttpResponse:
    """Hängt ein Eval ans Ende des Katalogs und öffnet seinen Knoten."""
    katalog: Evalkatalog = _fassung(request, pk)
    _eingaben_uebernehmen(katalog, request)
    eval_: Eval = katalog.eval_anlegen("Neues Eval")
    return redirect("simulation:evalkatalog_eval", pk=katalog.pk, eval_pk=eval_.pk)


@administratorin_erforderlich
def evalkatalog_eval(request: HttpRequest, pk: int, eval_pk: int) -> HttpResponse:
    """Zeigt den Knoten eines Evals samt Evalkriterien; speichert nur in Entwürfe."""
    if request.method == "POST":
        with transaction.atomic():
            katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
            if _eingaben_uebernehmen(katalog, request):
                messages.success(request, "Das Eval wurde gespeichert.")
        return redirect("simulation:evalkatalog_eval", pk=katalog.pk, eval_pk=eval_.pk)
    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    evals: list[Eval] = list(katalog.evals.all())
    return render(
        request,
        "simulation/evalkatalog_editor.html",
        {
            **_editor_kontext(katalog, "eval"),
            "eval": eval_,
            "eval_erstes": eval_ == evals[0],
            "eval_letztes": eval_ == evals[-1],
            "zeilen": _listenzeilen(
                eval_.kriterien.all(),
                "evalkriterium",
                "simulation:evalkatalog_evalkriterium",
                katalog.pk,
                eval_.pk,
            ),
        },
    )


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_eval_loeschen(
    request: HttpRequest, pk: int, eval_pk: int
) -> HttpResponse:
    """Löscht ein Eval samt seiner Evalkriterien und Evalinputs."""
    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    _eingaben_uebernehmen(katalog, request)
    eval_.delete()
    messages.success(request, "Das Eval wurde gelöscht.")
    return redirect("simulation:evalkatalog_editor", pk=katalog.pk)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_eval_verschieben(
    request: HttpRequest, pk: int, eval_pk: int, richtung: str
) -> HttpResponse:
    """Rückt ein Eval im Katalog eine Stelle hoch oder runter."""
    versatz: int = _versatz(richtung)
    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    _eingaben_uebernehmen(katalog, request)
    eval_.verschieben(versatz)
    return redirect("simulation:evalkatalog_eval", pk=katalog.pk, eval_pk=eval_.pk)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_evalkriterium_anlegen(
    request: HttpRequest, pk: int, eval_pk: int
) -> HttpResponse:
    """Hängt ein leeres Evalkriterium ans Ende der Liste des Evals."""
    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    _eingaben_uebernehmen(katalog, request)
    eval_.kriterium_anlegen()
    return redirect("simulation:evalkatalog_eval", pk=katalog.pk, eval_pk=eval_.pk)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_evalkriterium_loeschen(
    request: HttpRequest, pk: int, eval_pk: int, kriterium_pk: int
) -> HttpResponse:
    """Löscht ein Evalkriterium des Evals."""
    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    kriterium: Evalkriterium = get_object_or_404(eval_.kriterien, pk=kriterium_pk)
    _eingaben_uebernehmen(katalog, request)
    kriterium.delete()
    messages.success(request, "Das Kriterium wurde gelöscht.")
    return redirect("simulation:evalkatalog_eval", pk=katalog.pk, eval_pk=eval_.pk)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_evalkriterium_verschieben(
    request: HttpRequest, pk: int, eval_pk: int, kriterium_pk: int, richtung: str
) -> HttpResponse:
    """Rückt ein Evalkriterium eine Zeile hoch oder runter."""
    versatz: int = _versatz(richtung)
    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    kriterium: Evalkriterium = get_object_or_404(eval_.kriterien, pk=kriterium_pk)
    _eingaben_uebernehmen(katalog, request)
    kriterium.verschieben(versatz)
    return redirect("simulation:evalkatalog_eval", pk=katalog.pk, eval_pk=eval_.pk)


def _evalinput_der_fassung(
    request: HttpRequest, pk: int, eval_pk: int, input_pk: int
) -> tuple[Evalkatalog, Eval, Evalinput]:
    # Der Evalinput muss zum genannten Eval der Fassung gehören (siehe _fassung).

    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    return katalog, eval_, get_object_or_404(eval_.inputs, pk=input_pk)


def _zum_evalinput(evalinput: Evalinput) -> HttpResponse:
    # Zurück an den Knoten des Evalinputs.

    return redirect(
        "simulation:evalkatalog_evalinput",
        pk=evalinput.eval.katalog_id,
        eval_pk=evalinput.eval_id,
        input_pk=evalinput.pk,
    )


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_evalinput_anlegen(
    request: HttpRequest, pk: int, eval_pk: int
) -> HttpResponse:
    """Hängt einen Evalinput mit drei leeren Schritten an und öffnet seinen Knoten."""
    katalog, eval_ = _eval_der_fassung(request, pk, eval_pk)
    _eingaben_uebernehmen(katalog, request)
    evalinput: Evalinput = eval_.input_anlegen()
    return _zum_evalinput(evalinput)


@administratorin_erforderlich
def evalkatalog_evalinput(
    request: HttpRequest, pk: int, eval_pk: int, input_pk: int
) -> HttpResponse:
    """Zeigt einen Evalinput als Drehbuch; speichert nur in Entwürfe."""
    if request.method == "POST":
        with transaction.atomic():
            katalog, eval_, evalinput = _evalinput_der_fassung(
                request, pk, eval_pk, input_pk
            )
            if _eingaben_uebernehmen(katalog, request):
                messages.success(request, "Der Evalinput wurde gespeichert.")
        return _zum_evalinput(evalinput)
    katalog, eval_, evalinput = _evalinput_der_fassung(request, pk, eval_pk, input_pk)
    schritte: list[Inputschritt] = list(evalinput.schritte.all())
    return render(
        request,
        "simulation/evalkatalog_editor.html",
        {
            **_editor_kontext(katalog, "evalinput"),
            "eval": eval_,
            "evalinput": evalinput,
            "nummer": list(eval_.inputs.all()).index(evalinput) + 1,
            "schrittzeilen": zip(
                schritte,
                _listenzeilen(
                    schritte,
                    "inputschritt",
                    "simulation:evalkatalog_inputschritt",
                    katalog.pk,
                    eval_.pk,
                    evalinput.pk,
                ),
            ),
            "arten": Inputschritt.Art.choices,
        },
    )


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_evalinput_loeschen(
    request: HttpRequest, pk: int, eval_pk: int, input_pk: int
) -> HttpResponse:
    """Löscht einen Evalinput samt seiner Inputschritte."""
    katalog, eval_, evalinput = _evalinput_der_fassung(request, pk, eval_pk, input_pk)
    _eingaben_uebernehmen(katalog, request)
    evalinput.delete()
    messages.success(request, "Der Evalinput wurde gelöscht.")
    return redirect("simulation:evalkatalog_eval", pk=katalog.pk, eval_pk=eval_.pk)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_inputschritt_anlegen(
    request: HttpRequest, pk: int, eval_pk: int, input_pk: int
) -> HttpResponse:
    """Hängt einen leeren, festen Inputschritt ans Ende des Drehbuchs."""
    katalog, _, evalinput = _evalinput_der_fassung(request, pk, eval_pk, input_pk)
    _eingaben_uebernehmen(katalog, request)
    evalinput.schritt_anlegen()
    return _zum_evalinput(evalinput)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_inputschritt_loeschen(
    request: HttpRequest, pk: int, eval_pk: int, input_pk: int, schritt_pk: int
) -> HttpResponse:
    """Entfernt einen Inputschritt aus dem Drehbuch."""
    katalog, _, evalinput = _evalinput_der_fassung(request, pk, eval_pk, input_pk)
    schritt: Inputschritt = get_object_or_404(evalinput.schritte, pk=schritt_pk)
    _eingaben_uebernehmen(katalog, request)
    schritt.delete()
    messages.success(request, "Der Inputschritt wurde entfernt.")
    return _zum_evalinput(evalinput)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_inputschritt_verschieben(
    request: HttpRequest,
    pk: int,
    eval_pk: int,
    input_pk: int,
    schritt_pk: int,
    richtung: str,
) -> HttpResponse:
    """Rückt einen Inputschritt eine Zeile hoch oder runter."""
    versatz: int = _versatz(richtung)
    katalog, _, evalinput = _evalinput_der_fassung(request, pk, eval_pk, input_pk)
    schritt: Inputschritt = get_object_or_404(evalinput.schritte, pk=schritt_pk)
    _eingaben_uebernehmen(katalog, request)
    schritt.verschieben(versatz)
    return _zum_evalinput(evalinput)


@administratorin_erforderlich
@require_POST
@transaction.atomic
def evalkatalog_finalisieren(request: HttpRequest, pk: int) -> HttpResponse:
    """Finalisiert den Entwurf samt getippter Eingaben oder nennt seine Lücken."""
    katalog: Evalkatalog = _fassung(request, pk)
    if not _eingaben_uebernehmen(katalog, request):
        return redirect("simulation:evalkatalog_editor", pk=katalog.pk)
    try:
        katalog.finalisieren()
    except ValidationError as fehler:
        for meldung in fehler.messages:
            messages.error(request, meldung)
        return redirect("simulation:evalkatalog_editor", pk=katalog.pk)
    messages.success(
        request, "Der Evalkatalog ist final. Jeder Evallauf prüft ab jetzt gegen ihn."
    )
    return redirect("simulation:evalkatalog")


@administratorin_erforderlich
@require_POST
def evalkatalog_neue_fassung(request: HttpRequest, pk: int) -> HttpResponse:
    """Leitet aus der finalen Fassung einen Entwurf ab und öffnet seinen Editor."""
    katalog: Evalkatalog = get_object_or_404(
        Evalkatalog.objects.filter(zustand=Evalkatalog.Zustand.FINAL), pk=pk
    )
    try:
        entwurf: Evalkatalog = katalog.bearbeiten()
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("simulation:evalkatalog")
    return redirect("simulation:evalkatalog_editor", pk=entwurf.pk)


@administratorin_erforderlich
@require_POST
def evalkatalog_verwerfen(request: HttpRequest, pk: int) -> HttpResponse:
    """Verwirft den Katalog-Entwurf."""
    _fassung(request, pk).delete()
    messages.success(request, "Der Evalkatalog-Entwurf wurde verworfen.")
    return redirect("simulation:evalkatalog")


@dataclass(frozen=True)
class _Konfigurationszeile:
    # Eine Zeile der Liste; das Token trägt sie nur maskiert.

    pk: int
    bezeichnung: str
    angelegt_am: datetime | None
    anbieter: str
    sprachmodell: str
    anbieter_basis_url: str
    anbieter_token_maskiert: str
    parameter: object
    verwendungen: tuple[Verwendung, ...]


@dataclass(frozen=True)
class _Schalter:
    # Je Verwendung: schon aktiv für die gewählte Zeile, oder wen sie ablöst.

    verwendung: Verwendung
    ist_aktiv: bool
    statt: str


def _konfigurationszeilen() -> list[_Konfigurationszeile]:
    # Baut die Liste so, dass der Klartext des Tokens die Vorlage nie erreicht.

    aktive: dict[str, int] = ModellKonfiguration.objects.aktive_je_verwendung()
    return [
        _Konfigurationszeile(
            pk=konfiguration.pk,
            bezeichnung=konfiguration.bezeichnung,
            angelegt_am=konfiguration.angelegt_am,
            anbieter=konfiguration.get_anbieter_display(),
            sprachmodell=konfiguration.sprachmodell,
            anbieter_basis_url=konfiguration.anbieter_basis_url,
            anbieter_token_maskiert=konfiguration.anbieter_token_maskiert,
            parameter=konfiguration.parameter,
            verwendungen=tuple(
                verwendung
                for verwendung in Verwendung
                if aktive.get(verwendung) == konfiguration.pk
            ),
        )
        for konfiguration in ModellKonfiguration.objects.order_by("-pk")
    ]


def _aktive_zeile(
    zeilen: list[_Konfigurationszeile], verwendung: Verwendung
) -> _Konfigurationszeile | None:
    # Die Zeile, die gerade für die Verwendung aktiv ist; keine, solange unbelegt.

    return next((zeile for zeile in zeilen if verwendung in zeile.verwendungen), None)


def _gewaehlte_zeile(
    request: HttpRequest, zeilen: list[_Konfigurationszeile]
) -> _Konfigurationszeile | None:
    # Die genannte Zeile, sonst die der Schüler:in, sonst die neueste.

    genannt: str = request.GET.get("konfiguration", "")
    if genannt.isdigit():
        for zeile in zeilen:
            if zeile.pk == int(genannt):
                return zeile
    return _aktive_zeile(zeilen, Verwendung.SCHUELERIN) or (
        zeilen[0] if zeilen else None
    )


def _schalter(
    gewaehlt: _Konfigurationszeile, zeilen: list[_Konfigurationszeile]
) -> list[_Schalter]:
    # Je Verwendung ein Schalter für die gewählte Zeile.

    schalter: list[_Schalter] = []
    for verwendung in Verwendung:
        aktiv: _Konfigurationszeile | None = _aktive_zeile(zeilen, verwendung)
        schalter.append(
            _Schalter(
                verwendung=verwendung,
                ist_aktiv=aktiv is not None and aktiv.pk == gewaehlt.pk,
                statt=aktiv.bezeichnung if aktiv else "",
            )
        )
    return schalter


def _zur_konfiguration(konfiguration: ModellKonfiguration) -> HttpResponse:
    # Führt zurück zur Liste, die Konfiguration im Detail.

    return redirect(
        f"{reverse('simulation:modell_konfiguration')}?konfiguration={konfiguration.pk}"
    )


@administratorin_erforderlich
def modell_konfiguration(request: HttpRequest) -> HttpResponse:
    """Listet alle Modell-Konfigurationen, das Detail der gewählten daneben."""
    zeilen: list[_Konfigurationszeile] = _konfigurationszeilen()
    gewaehlt: _Konfigurationszeile | None = _gewaehlte_zeile(request, zeilen)
    return render(
        request,
        "simulation/modell_konfiguration.html",
        {
            "konfigurationen": zeilen,
            "gewaehlt": gewaehlt,
            "schalter": _schalter(gewaehlt, zeilen) if gewaehlt else [],
        },
    )


def _vorlage(request: HttpRequest) -> ModellKonfiguration | None:
    # Die unter ?vorlage= genannte Konfiguration; eine unbekannte ergibt 404.

    genannt: str = request.GET.get("vorlage", "")
    if not genannt:
        return None
    if not genannt.isdigit():
        raise Http404("Unbekannte Vorlage.")
    return get_object_or_404(ModellKonfiguration, pk=int(genannt))


@administratorin_erforderlich
def modell_konfiguration_neu(request: HttpRequest) -> HttpResponse:
    """Legt eine neue Konfiguration an, auf Wunsch aus einer Vorlage.

    Die Vorlage füllt alles vor außer dem Token: Das bleibt write-only und wird
    für jede neue Konfiguration neu eingegeben. Aktiviert wird allein in der
    Liste.
    """
    vorlage: ModellKonfiguration | None = _vorlage(request)
    form: ModellKonfigurationForm
    if request.method == "POST":
        form = ModellKonfigurationForm(request.POST)
        if form.is_valid():
            konfiguration: ModellKonfiguration = form.save()
            messages.success(
                request,
                f"Die Konfiguration »{konfiguration.bezeichnung}« ist angelegt.",
            )
            return _zur_konfiguration(konfiguration)
    elif vorlage:
        form = ModellKonfigurationForm(
            initial={
                "bezeichnung": f"{vorlage.bezeichnung} (Kopie)",
                "anbieter": vorlage.anbieter,
                "anbieter_basis_url": vorlage.anbieter_basis_url,
                "sprachmodell": vorlage.sprachmodell,
                "parameter": vorlage.parameter,
            }
        )
    else:
        form = ModellKonfigurationForm()
    # Nur Nummer und Bezeichnung, damit der Klartext des Tokens die Seite nie erreicht.
    vorlage_kopf: dict[str, object] | None = (
        {"pk": vorlage.pk, "bezeichnung": vorlage.bezeichnung} if vorlage else None
    )
    return render(
        request,
        "simulation/modell_konfiguration_neu.html",
        {"form": form, "vorlage": vorlage_kopf},
    )


# Welches Formularfeld ein gewählter Vorschlag füllt. Die Naht entscheidet es,
# nicht die Anfrage: Ein von außen genannter Feldname stünde in der Antwort.
_FELD_JE_NAHT: dict[str, str] = {
    Naht.SPRACHMODELL: "id_sprachmodell",
    Naht.TRANSKRIPTION: "id_transkriptionsmodell",
}

# Das Feld der Basis-URL heißt auf beiden Seiten gleich; es hängt an der
# Anbieter-Feldgruppe und nicht an der Naht.
_FELD_BASIS_URL: str = "id_anbieter_basis_url"


def _abgeleitete_wurzel(
    verzeichnis: Modellverzeichnis, naht: str, getippte: str
) -> str:
    # Die abgeleitete Endpunktwurzel ergänzt ein leeres Feld und überschreibt
    # nie eine getippte Angabe. Scheitert allein diese Abfrage, bleiben die
    # Modellvorschläge stehen: Der eine Teil reißt den anderen nicht mit.

    if getippte:
        return ""
    try:
        return verzeichnis.basis_url(naht)
    except Modellverzeichnisfehler:
        return ""


@administratorin_erforderlich
@require_POST
def modellvorschlaege(request: HttpRequest) -> HttpResponse:
    """Liefert Vorschlagsliste und abgeleitete Wurzel zu Anbieter und Naht.

    Das Token kommt aus dem Formular, geht an das Verzeichnis und sonst
    nirgendwohin: Es steht weder in der Antwort noch in einem Protokoll. Eine
    Geste der Administrator:in, zwei Felder — und wo die Wurzel ausbleibt,
    bleiben die Vorschläge trotzdem.
    """
    naht: str = request.POST.get("naht", "")
    verzeichnis: Modellverzeichnis
    vorschlaege: list[Modellvorschlag]
    fehler: str
    wurzel: str = ""
    try:
        verzeichnis = modellverzeichnis(
            request.POST.get("anbieter", ""),
            request.POST.get("anbieter_token", ""),
        )
        vorschlaege = verzeichnis.vorschlaege(naht)
        fehler = ""
        wurzel = _abgeleitete_wurzel(
            verzeichnis, naht, request.POST.get("anbieter_basis_url", "")
        )
    except Modellverzeichnisfehler as modellfehler:
        vorschlaege = []
        fehler = str(modellfehler)
    return render(
        request,
        "simulation/includes/modellvorschlaege.html",
        {
            "vorschlaege": vorschlaege,
            "fehler": fehler,
            "feld": _FELD_JE_NAHT.get(naht, ""),
            "wurzel": wurzel,
            "wurzelfeld": _FELD_BASIS_URL,
        },
    )


@administratorin_erforderlich
@require_POST
def modell_konfiguration_aktivieren(
    request: HttpRequest, pk: int, verwendung: str
) -> HttpResponse:
    """Richtet den Zeiger einer Verwendung auf eine bestehende Konfiguration."""
    if verwendung not in Verwendung.values:
        raise Http404("Unbekannte Verwendung.")
    konfiguration: ModellKonfiguration = get_object_or_404(ModellKonfiguration, pk=pk)
    ModellKonfiguration.objects.aktivieren(konfiguration, Verwendung(verwendung))
    return _zur_konfiguration(konfiguration)


@administratorin_erforderlich
def transkriptions_konfiguration(request: HttpRequest) -> HttpResponse:
    """Bearbeitet den einen Anbieterzugang der Transkription."""
    konfiguration: TranskriptionsKonfiguration = (
        TranskriptionsKonfiguration.objects.aktuelle()
    )
    form: TranskriptionsKonfigurationForm
    if request.method == "POST":
        form = TranskriptionsKonfigurationForm(request.POST, instance=konfiguration)
        if form.is_valid():
            form.save()
            messages.success(request, "Die Transkription ist neu eingestellt.")
            # Der Umweg über die Umleitung hält das gespeicherte Token
            # aus dem Antwortkörper heraus.
            return redirect("simulation:transkriptions_konfiguration")
    else:
        form = TranskriptionsKonfigurationForm(instance=konfiguration)
    return render(
        request,
        "simulation/transkriptions_konfiguration.html",
        {"form": form, "konfiguration": konfiguration},
    )

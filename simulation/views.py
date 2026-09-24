"""Ansichten für den Simulationskern."""

from collections.abc import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from konten.navigation import administratorin_erforderlich, autorin_erforderlich


from .forms import (
    ModellKonfigurationForm,
    SimulationskernForm,
    TranskriptionsKonfigurationForm,
)
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
    VERTRAG_RAHMEN,
    ModellKonfiguration,
    Simulationskern,
    TranskriptionsKonfiguration,
    Verwendung,
)
from .standardkern import STANDARDKERN_VORLAGEN


def _finale_fassung() -> Simulationskern | None:
    # Liefert die eine finale Fassung, die der Kern trägt, sobald es sie gibt.

    return Simulationskern.objects.filter(zustand=Simulationskern.Zustand.FINAL).first()


def _archivierte_fassungen() -> QuerySet[Simulationskern]:
    # Liefert die überholten Fassungen, die zuletzt überholte zuerst.

    return Simulationskern.objects.filter(
        zustand=Simulationskern.Zustand.ARCHIVIERT
    ).order_by("-finalisiert_am", "-pk")


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
    except (RuntimeError, ValueError, ValidationError) as error:
        if isinstance(error, ValidationError):
            messages.error(request, "; ".join(error.messages))
        else:
            messages.error(request, str(error))
    return redirect("simulation:kern_verwalten")


@login_required
@autorin_erforderlich
def kern(request: HttpRequest) -> HttpResponse:
    """Zeigt die finale Kern-Fassung und die aktive Modell-Konfiguration."""
    simulationskern: Simulationskern | None = _finale_fassung()
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
            "finale_fassung": _finale_fassung(),
            "archivierte_fassungen": _archivierte_fassungen(),
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
    except ValueError as error:
        messages.error(request, str(error))
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


def _konfigurationszeilen(aktive: dict[str, int]) -> list[dict[str, object]]:
    # Baut die Liste so, dass der Klartext des Tokens die Vorlage nie erreicht.

    return [
        {
            "pk": konfiguration.pk,
            "bezeichnung": konfiguration.bezeichnung,
            "angelegt_am": konfiguration.angelegt_am,
            "anbieter": konfiguration.anbieter,
            "sprachmodell": konfiguration.sprachmodell,
            "anbieter_basis_url": konfiguration.anbieter_basis_url,
            "anbieter_token_maskiert": konfiguration.anbieter_token_maskiert,
            "parameter": konfiguration.parameter,
            "verwendungen": [
                {
                    "label": verwendung.label,
                    "ist_aktiv": aktive.get(verwendung) == konfiguration.pk,
                }
                for verwendung in Verwendung
            ],
        }
        for konfiguration in ModellKonfiguration.objects.order_by("-pk")
    ]


def _gewaehlte_zeile(
    request: HttpRequest, zeilen: list[dict[str, object]], aktive: dict[str, int]
) -> dict[str, object] | None:
    # Die genannte Zeile, sonst die der Schüler:in, sonst die neueste.

    je_pk: dict[object, dict[str, object]] = {zeile["pk"]: zeile for zeile in zeilen}
    genannt: str = request.GET.get("konfiguration", "")
    if genannt.isdigit() and int(genannt) in je_pk:
        return je_pk[int(genannt)]
    if aktive.get(Verwendung.SCHUELERIN) in je_pk:
        return je_pk[aktive[Verwendung.SCHUELERIN]]
    return zeilen[0] if zeilen else None


def _schalter(
    gewaehlt: dict[str, object], zeilen: list[dict[str, object]], aktive: dict[str, int]
) -> list[dict[str, object]]:
    # Je Verwendung: aktiv für die gewählte Zeile, oder wen ein Umschalten ablöst.

    bezeichnung_je_pk: dict[object, object] = {
        zeile["pk"]: zeile["bezeichnung"] for zeile in zeilen
    }
    return [
        {
            "wert": verwendung.value,
            "label": verwendung.label,
            "ist_aktiv": aktive.get(verwendung) == gewaehlt["pk"],
            "abgeloest": bezeichnung_je_pk.get(aktive.get(verwendung), ""),
        }
        for verwendung in Verwendung
    ]


@administratorin_erforderlich
def modell_konfiguration(request: HttpRequest) -> HttpResponse:
    """Listet alle Modell-Konfigurationen, das Detail der gewählten daneben."""
    aktive: dict[str, int] = ModellKonfiguration.objects.aktive_je_verwendung()
    zeilen: list[dict[str, object]] = _konfigurationszeilen(aktive)
    gewaehlt: dict[str, object] | None = _gewaehlte_zeile(request, zeilen, aktive)
    return render(
        request,
        "simulation/modell_konfiguration.html",
        {
            "konfigurationen": zeilen,
            "gewaehlt": gewaehlt,
            "schalter": _schalter(gewaehlt, zeilen, aktive) if gewaehlt else [],
        },
    )


def _zur_konfiguration(konfiguration: ModellKonfiguration) -> HttpResponse:
    # Zurück zur Liste, die eben berührte Konfiguration im Detail.

    return redirect(
        f"{reverse('simulation:modell_konfiguration')}?konfiguration={konfiguration.pk}"
    )


@administratorin_erforderlich
def modell_konfiguration_neu(request: HttpRequest) -> HttpResponse:
    """Legt eine neue Konfiguration an, auf Wunsch aus einer Vorlage.

    Die Vorlage füllt alles vor außer dem Token: Das bleibt write-only und wird
    für jede neue Konfiguration neu eingegeben.
    """
    vorlage: ModellKonfiguration | None = None
    if request.GET.get("vorlage"):
        vorlage = get_object_or_404(ModellKonfiguration, pk=request.GET["vorlage"])
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
    return render(
        request,
        "simulation/modell_konfiguration_neu.html",
        {"form": form, "vorlage": vorlage},
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
    messages.success(
        request,
        f"»{konfiguration.bezeichnung}« ist jetzt für "
        f"{Verwendung(verwendung).label} aktiv.",
    )
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

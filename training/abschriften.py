"""Holt eine abgeschlossene Erhebungsteilnahme als Abschrift ins eigene Konto.

Die Kante zeigt von `training` nach `erhebungen` und nie umgekehrt: `erhebungen`
darf nach ADR-0006 nichts von Konten wissen. Gelesen wird dort nur; es entsteht
weder ein Fremdschlüssel noch ein gespeichertes Token noch ein Merker an der
Erhebungsbindung.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from erhebungen.models import Erhebung, Erhebungsbindung
from konten.models import Konto
from sitzungen.models import (
    Diagnose,
    Fehlversuch,
    Gespraechsschritt,
    Sitzung,
    Teilnahme,
    Vignettenposition,
)

from .models import Abschrift

ABLEHNUNG: str = "Zu diesem Teilnahme-Token lässt sich keine Abschrift holen."
"""Die eine Meldung jeder Ablehnung: Der Import ist kein Orakel über Tokens."""


@transaction.atomic
def abschrift_holen(konto: Konto, token: str) -> Abschrift:
    """Kopiert die Sitzungen einer abgeschlossenen Erhebungsteilnahme ins Konto.

    Der Import ist beliebig oft wiederholbar: Jeder Aufruf legt eine weitere,
    eigenständige Abschrift an. Eine Deduplizierung verlangte, dass sich das
    System merkt, welches Token in welches Konto ging — genau die verbotene
    Verknüpfung.
    """

    bindung: Erhebungsbindung = _holbare_bindung(token)
    abschrift: Abschrift = Abschrift.objects.create(
        teilnahme=Teilnahme.objects.create(),
        konto=konto,
        erhebungsname=bindung.stichprobe.erhebung.name,
    )
    _sitzungen_kopieren(bindung.teilnahme, abschrift.teilnahme)
    return abschrift


def _holbare_bindung(token: str) -> Erhebungsbindung:
    # Löst das Token auf, solange die Teilnahme abgeschlossen und nichts
    # archiviert ist. Jeder andere Ausgang ist dieselbe Ablehnung.

    bindung: Erhebungsbindung | None = (
        Erhebungsbindung.objects.filter(
            token=token.strip().upper(),
            abgeschlossen_am__isnull=False,
            stichprobe__archiviert=False,
        )
        .exclude(stichprobe__erhebung__status=Erhebung.Status.ARCHIVIERT)
        .select_related("stichprobe__erhebung", "teilnahme")
        .first()
    )
    if bindung is None:
        raise ValidationError(ABLEHNUNG)
    return bindung


def _sitzungen_kopieren(quelle: Teilnahme, ziel: Teilnahme) -> None:
    # Kopiert Sitzungen samt Transkript, Fehlversuchen, Diagnosen und Positionen.
    # Die Zeitstempel der Kopien entstehen neu (`auto_now_add`): Die Abschrift
    # führt die Importzeit, nicht die Spielzeit der Erhebung.

    positionen: dict[int, int] = {
        position.sitzung_id: position.position
        for position in quelle.vignettenpositionen.all()
    }
    for sitzung in quelle.sitzung_set.order_by("pk"):
        kopie: Sitzung = Sitzung.objects.create(
            teilnahme=ziel,
            vignette_id=sitzung.vignette_id,
            simulationskern_id=sitzung.simulationskern_id,
            modell_konfiguration_id=sitzung.modell_konfiguration_id,
            status=sitzung.status,
            verbrauchte_zeit=sitzung.verbrauchte_zeit,
        )
        for schritt in sitzung.gespraechsschritte:
            _schritt_kopieren(schritt, kopie)
        diagnose: Diagnose | None = Diagnose.objects.filter(sitzung=sitzung).first()
        if diagnose is not None:
            Diagnose.objects.create(
                sitzung=kopie, text=diagnose.text, eingabemodus=diagnose.eingabemodus
            )
        if sitzung.pk in positionen:
            Vignettenposition.objects.create(
                teilnahme=ziel,
                sitzung=kopie,
                vignette_id=kopie.vignette_id,
                position=positionen[sitzung.pk],
            )


def _schritt_kopieren(schritt: Gespraechsschritt, sitzung: Sitzung) -> None:
    # Kopiert einen Gesprächsschritt einschließlich Denkspur: Der CheckConstraint
    # lässt Äußerung ohne Denkspur nicht zu, die Sichtbarkeitszusage aus ADR-0005
    # sitzt im Rendering.

    kopie: Gespraechsschritt = Gespraechsschritt.objects.create(
        sitzung=sitzung,
        eingabe=schritt.eingabe,
        denkspur=schritt.denkspur,
        aeusserung=schritt.aeusserung,
        reihenfolge=schritt.reihenfolge,
        eingabemodus=schritt.eingabemodus,
    )
    Fehlversuch.objects.bulk_create(
        [
            Fehlversuch(
                gespraechsschritt=kopie,
                grund=fehlversuch.grund,
                rohantwort=fehlversuch.rohantwort,
            )
            for fehlversuch in schritt.fehlversuch_set.all()
        ]
    )

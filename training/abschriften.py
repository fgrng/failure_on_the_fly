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


@transaction.atomic
def abschrift_loeschen(abschrift: Abschrift) -> None:
    """Entfernt eine Abschrift samt ihrer Teilnahme und allem Kopierten.

    Gelöscht wird über die Teilnahme: Ihre Kaskade nimmt Sitzungen,
    Gesprächsschritte, Diagnosen, Positionen und die Abschrift selbst mit. Nur
    die Fehlversuche hängen geschützt an ihrem Schritt und gehen voraus. Die
    Erhebungsdaten kennt dieser Weg nicht und rührt sie darum nicht an.
    """

    Fehlversuch.objects.filter(
        gespraechsschritt__sitzung__teilnahme=abschrift.teilnahme
    ).delete()
    abschrift.teilnahme.delete()


def _holbare_bindung(token: str) -> Erhebungsbindung:
    # Löst das normalisierte Token auf, solange die Teilnahme abgeschlossen und
    # nichts archiviert ist. Jeder andere Ausgang ist dieselbe Ablehnung.

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
    # Kopiert die Sitzungen in ihrer Anlagereihenfolge. Die gespielte Reihenfolge
    # steht in der Vignettenposition und wird je Sitzung mitgegeben — eine
    # Sitzung ohne Position bekommt auch in der Abschrift keine.

    positionen: dict[int, int] = {
        position.sitzung_id: position.position
        for position in quelle.vignettenpositionen.all()
    }
    for sitzung in quelle.sitzung_set.order_by("pk"):
        _sitzung_kopieren(sitzung, ziel, positionen.get(sitzung.pk))


def _sitzung_kopieren(quelle: Sitzung, ziel: Teilnahme, position: int | None) -> None:
    # Kopiert eine Sitzung samt Transkript, Fehlversuchen und Diagnose. Die
    # Zeitstempel der Kopien entstehen neu (`auto_now_add`): Die Abschrift führt
    # die Importzeit, nicht die Spielzeit der Erhebung.

    kopie: Sitzung = Sitzung.objects.create(
        teilnahme=ziel,
        vignette_id=quelle.vignette_id,
        simulationskern_id=quelle.simulationskern_id,
        modell_konfiguration_id=quelle.modell_konfiguration_id,
        status=quelle.status,
        verbrauchte_zeit=quelle.verbrauchte_zeit,
    )
    for schritt in quelle.gespraechsschritte:
        _schritt_kopieren(schritt, kopie)
    diagnose: Diagnose | None = Diagnose.objects.filter(sitzung=quelle).first()
    if diagnose is not None:
        Diagnose.objects.create(
            sitzung=kopie, text=diagnose.text, eingabemodus=diagnose.eingabemodus
        )
    if position is not None:
        Vignettenposition.objects.create(
            teilnahme=ziel,
            sitzung=kopie,
            vignette_id=kopie.vignette_id,
            position=position,
        )


def _schritt_kopieren(schritt: Gespraechsschritt, ziel: Sitzung) -> None:
    # Kopiert einen Gesprächsschritt einschließlich Denkspur: Der CheckConstraint
    # lässt Äußerung ohne Denkspur nicht zu, die Sichtbarkeitszusage aus ADR-0005
    # sitzt im Rendering.

    kopie: Gespraechsschritt = Gespraechsschritt.objects.create(
        sitzung=ziel,
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

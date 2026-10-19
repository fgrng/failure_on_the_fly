"""Holt eine abgeschlossene Erhebungsteilnahme als Abschrift ins eigene Konto.

Die Kante zeigt von `training` nach `erhebungen` und nie umgekehrt: `erhebungen`
darf nach ADR-0006 nichts von Konten wissen. Gelesen wird dort nur; es entsteht
weder ein Fremdschlüssel noch ein gespeichertes Token noch ein Merker an der
Erhebungsbindung.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet

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
from sitzungen.sink import GespraechsschrittDaten, Sitzungsinhalte, sitzungsinhalte

from .models import Abschrift, Training

ABLEHNUNG: str = "Zu diesem Teilnahme-Token lässt sich keine Abschrift holen."
"""Die eine Meldung jeder Ablehnung: Der Import ist kein Orakel über Tokens."""

FREIGABE_ABGEWIESEN: str = "Freigeben lässt sich nur für beigetretene Trainings."
"""Die Ablehnung einer Freigabe für ein Training ohne eigene Trainingsbindung."""


@transaction.atomic
def abschrift_holen(konto: Konto, token: str) -> Abschrift:
    """Kopiert die Sitzungen einer abgeschlossenen Erhebungsteilnahme ins Konto.

    Der Import ist beliebig oft wiederholbar: Jeder Aufruf legt eine weitere,
    eigenständige Abschrift an. Eine Deduplizierung verlangte, dass sich das
    System merkt, welches Token in welches Konto ging — genau die verbotene
    Verknüpfung.

    Eine flüchtige Teilnahme liefert ihre Inhalte, solange sie vorgehalten
    werden; danach gilt das Token als unbrauchbar. Der Import liest nur und
    verschiebt die Frist nicht.
    """

    bindung: Erhebungsbindung = _holbare_bindung(token)
    inhalte: list[tuple[Sitzung, Sitzungsinhalte]] = _inhalte_lesen(bindung.teilnahme)
    abschrift: Abschrift = Abschrift.objects.create(
        teilnahme=Teilnahme.objects.create(),
        konto=konto,
        erhebungsname=bindung.stichprobe.erhebung.name,
    )
    _sitzungen_kopieren(bindung.teilnahme, inhalte, abschrift.teilnahme)
    return abschrift


@transaction.atomic
def abschrift_loeschen(abschrift: Abschrift) -> None:
    """Entfernt eine Abschrift samt ihrer Teilnahme und allem Kopierten.

    Gelöscht wird die Abschrift; ihre Teilnahme nimmt das `post_delete`-Signal
    in `training.models` mit. Über dasselbe Signal räumt auch die Kaskade einer
    Konto-Löschung auf, die diesen Einstiegspunkt nicht durchläuft.
    """

    abschrift.delete()


def abschrift_freigeben(abschrift: Abschrift, trainings: list[int]) -> None:
    """Gibt die ganze Abschrift genau für diese Trainings frei (ADR-0049).

    Freigeben lässt sie sich nur für Trainings, denen ihr Konto aktiv
    beigetreten ist; die Vignetten des Trainings spielen keine Rolle. Was nicht
    genannt ist, ist widerrufen; ruhende Freigaben für Trainings nach dem Austritt
    bleiben unberührt. Nennt die Auswahl ein anderes Training, bleibt alles,
    wie es war.
    """

    gewaehlt: QuerySet[Training] = Training.objects.beigetreten_von(
        abschrift.konto
    ).filter(pk__in=trainings)
    if gewaehlt.count() != len(set(trainings)):
        raise ValidationError(FREIGABE_ABGEWIESEN)
    abschrift.freigegeben_fuer.set([*gewaehlt, *ruhende_freigaben(abschrift)])


def wirksame_freigaben(abschrift: Abschrift) -> QuerySet[Training]:
    """Die Freigaben für Trainings, denen das Konto aktiv angehört."""

    return abschrift.freigegeben_fuer.filter(
        pk__in=Abschrift.wirksame_freigaben()
        .filter(abschrift=abschrift)
        .values("training")
    )


def ruhende_freigaben(abschrift: Abschrift) -> QuerySet[Training]:
    """Die Freigaben für Trainings, aus denen das Konto ausgetreten ist.

    Sie wirken nicht, bleiben aber bestehen, bis sie widerrufen werden oder ein
    Wiederbeitritt sie weckt (ADR-0049).
    """

    return abschrift.freigegeben_fuer.exclude(
        pk__in=wirksame_freigaben(abschrift).values("pk")
    )


def teilnahme_einer_abschrift_raeumen(teilnahme: Teilnahme) -> None:
    """Löscht die Teilnahme einer entfernten Abschrift mit allem Kopierten.

    Die Kaskade der Teilnahme nimmt Sitzungen, Gesprächsschritte, Diagnosen und
    Positionen mit. Nur die Fehlversuche hängen mit `PROTECT` an ihrem Schritt
    und gehen voraus. Die Erhebungsdaten kennt dieser Weg nicht und rührt sie
    darum nicht an.
    """

    Fehlversuch.objects.filter(gespraechsschritt__sitzung__teilnahme=teilnahme).delete()
    teilnahme.delete()


def _holbare_bindung(token: str) -> Erhebungsbindung:
    # Löst das normalisierte Token auf, solange die Teilnahme abgeschlossen
    # und nichts archiviert ist. Jeder andere Ausgang ist dieselbe Ablehnung.

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


def _inhalte_lesen(teilnahme: Teilnahme) -> list[tuple[Sitzung, Sitzungsinhalte]]:
    # Liest die Inhalte aller Sitzungen in ihrer Anlagereihenfolge. Fehlt auch
    # nur eine, sind die flüchtigen Inhalte abgelaufen: dieselbe Ablehnung.

    gelesen: list[tuple[Sitzung, Sitzungsinhalte]] = []
    for sitzung in teilnahme.sitzung_set.select_related("teilnahme").order_by("pk"):
        inhalte: Sitzungsinhalte | None = sitzungsinhalte(sitzung)
        if inhalte is None:
            raise ValidationError(ABLEHNUNG)
        gelesen.append((sitzung, inhalte))
    return gelesen


def _sitzungen_kopieren(
    quelle: Teilnahme,
    inhalte: list[tuple[Sitzung, Sitzungsinhalte]],
    ziel: Teilnahme,
) -> None:
    # Kopiert die Sitzungen samt ihren Inhalten. Die gespielte Reihenfolge
    # steht in der Vignettenposition und wird je Sitzung mitgegeben — eine
    # Sitzung ohne Position bekommt auch in der Abschrift keine.

    positionen: dict[int, int] = {
        position.sitzung_id: position.position
        for position in quelle.vignettenpositionen.all()
    }
    for sitzung, sitzung_inhalte in inhalte:
        _sitzung_kopieren(sitzung, sitzung_inhalte, ziel, positionen.get(sitzung.pk))


def _sitzung_kopieren(
    quelle: Sitzung, inhalte: Sitzungsinhalte, ziel: Teilnahme, position: int | None
) -> None:
    # Kopiert eine Sitzung samt Transkript, Fehlversuchen und Diagnose. Die
    # Zeitstempel der Kopien entstehen neu (`auto_now_add`): Die Abschrift führt
    # die Importzeit, nicht die Spielzeit der Erhebung.

    kopie: Sitzung = Sitzung.objects.create(
        teilnahme=ziel,
        vignette_id=quelle.vignette_id,
        simulationskern_id=quelle.simulationskern_id,
        modell_konfiguration_id=quelle.modell_konfiguration_id,
        transkriptions_konfiguration_id=quelle.transkriptions_konfiguration_id,
        status=quelle.status,
        verbrauchte_zeit=quelle.verbrauchte_zeit,
    )
    for schritt in inhalte.gespraechsschritte:
        _schritt_kopieren(schritt, kopie)
    if inhalte.diagnose is not None:
        Diagnose.objects.create(
            sitzung=kopie,
            text=inhalte.diagnose["text"],
            eingabemodus=inhalte.diagnose["eingabemodus"],
        )
    if position is not None:
        Vignettenposition.objects.create(
            teilnahme=ziel,
            sitzung=kopie,
            vignette_id=kopie.vignette_id,
            position=position,
        )


def _schritt_kopieren(schritt: GespraechsschrittDaten, ziel: Sitzung) -> None:
    # Kopiert einen Gesprächsschritt einschließlich Denkspur: Der CheckConstraint
    # lässt Äußerung ohne Denkspur nicht zu, die Sichtbarkeitszusage aus ADR-0064
    # sitzt im Rendering.

    kopie: Gespraechsschritt = Gespraechsschritt.objects.create(
        sitzung=ziel,
        eingabe=schritt["eingabe"],
        denkspur=schritt["denkspur"],
        aeusserung=schritt["aeusserung"],
        reihenfolge=schritt["reihenfolge"],
        eingabemodus=schritt["eingabemodus"],
    )
    Fehlversuch.objects.bulk_create(
        [
            Fehlversuch(
                gespraechsschritt=kopie,
                grund=fehlversuch["grund"],
                rohantwort=fehlversuch["rohantwort"],
            )
            for fehlversuch in schritt["fehlversuche"]
        ]
    )

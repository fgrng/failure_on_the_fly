"""Beantwortet, wo eine Erhebungsbindung steht, und schreibt ihren Fortschritt."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from simulation.models import ModellKonfiguration, Simulationskern
from sitzungen.durchlauf import sitzung_starten
from sitzungen.models import Sitzung
from sitzungen.sink import DBSink
from vignetten.models import Vignette

from .models import (
    Erhebungsbindung,
    Erhebungsitem,
    ItemAntwort,
    Itemblock,
    Vignettenposition,
    Vignettenziehung,
)


@dataclass(frozen=True)
class NochNichtBegonnen:
    """Die Teilnahme hat noch keine Vignette gespielt."""


@dataclass(frozen=True)
class LaufendeSitzung:
    """Eine Sitzung dieser Teilnahme ist noch nicht beendet."""

    sitzung: Sitzung


@dataclass(frozen=True)
class NaechsteVignette:
    """Die nächste gezogene, noch ungespielte Vignetten-Fassung steht an."""

    vignette: Vignette


@dataclass(frozen=True)
class OffenerSitzungsblock:
    """Der Fragebogen-Block zur beendeten Sitzung ist noch nicht erledigt."""

    sitzung: Sitzung


@dataclass(frozen=True)
class OffenerAbschlussblock:
    """Der Fragebogen-Block am Ende der Erhebung ist noch nicht erledigt."""


@dataclass(frozen=True)
class Ende:
    """Für diese Erhebungsbindung steht nichts mehr an."""


Schritt = (
    NochNichtBegonnen
    | LaufendeSitzung
    | NaechsteVignette
    | OffenerSitzungsblock
    | OffenerAbschlussblock
    | Ende
)
"""Die sechs Stellen, an denen eine Erhebungsbindung stehen kann."""


def naechster_schritt(bindung: Erhebungsbindung) -> Schritt:
    """Beantwortet schreibfrei, wo diese Erhebungsbindung gerade steht.

    Die Reihenfolge der Fälle ist die des Ablaufs: Eine laufende Sitzung geht
    ihrem Fragebogen voraus, dieser der nächsten Vignette, und erst danach steht
    der Abschluss an.
    """

    if bindung.abgeschlossen_am is not None:
        return Ende()
    laufende: Sitzung | None = laufende_sitzung(bindung)
    if laufende is not None:
        return LaufendeSitzung(laufende)
    beurteilte_sitzung: Sitzung | None = _sitzung_ohne_erledigten_block(bindung)
    if beurteilte_sitzung is not None:
        return OffenerSitzungsblock(beurteilte_sitzung)
    if not bindung.teilnahme.sitzung_set.exists():
        # Vor der ersten Sitzung steht die Ziehung noch aus, die nächste Vignette
        # benennt deshalb erst das Kommando, das sie festschreibt.
        return NochNichtBegonnen()
    vignette: Vignette | None = _naechste_gezogene_vignette(bindung)
    if vignette is not None:
        return NaechsteVignette(vignette)
    if _abschlussblock_ist_offen(bindung):
        return OffenerAbschlussblock()
    return Ende()


def laufende_sitzung(bindung: Erhebungsbindung) -> Sitzung | None:
    """Liefert die noch nicht beendete Sitzung dieser Teilnahme samt Anzeigedaten."""

    return (
        Sitzung.objects.select_related("vignette", "simulationskern", "teilnahme")
        .filter(teilnahme=bindung.teilnahme, status=Sitzung.Status.LAUFEND)
        .first()
    )


def sitzung_am_zug(bindung: Erhebungsbindung) -> Sitzung | None:
    """Liefert die Sitzung, die anzuzeigen ist: die laufende oder die beurteilte."""

    match naechster_schritt(bindung):
        case LaufendeSitzung(sitzung) | OffenerSitzungsblock(sitzung):
            return sitzung
        case _:
            return None


def sitzung_mit_offenem_block(bindung: Erhebungsbindung) -> Sitzung | None:
    """Liefert die Sitzung, deren Fragebogen-Block gerade an der Reihe ist."""

    match naechster_schritt(bindung):
        case OffenerSitzungsblock(sitzung):
            return sitzung
        case _:
            return None


def _naechste_gezogene_vignette(bindung: Erhebungsbindung) -> Vignette | None:
    # Die erste gezogene Fassung, zu der noch keine Sitzung dieser Teilnahme steht.

    gespielte_ids = bindung.teilnahme.sitzung_set.values_list("vignette_id", flat=True)
    ziehung: Vignettenziehung | None = (
        bindung.vignettenziehungen.select_related("vignette")
        .exclude(vignette_id__in=gespielte_ids)
        .first()
    )
    return ziehung.vignette if ziehung is not None else None


def _sitzung_ohne_erledigten_block(bindung: Erhebungsbindung) -> Sitzung | None:
    # Liefert die älteste beendete Sitzung, deren Block noch nicht erledigt ist.

    if not _block_kann_offen_sein(bindung, Erhebungsitem.Andockpunkt.NACH_SITZUNG):
        return None
    erledigte_sitzungen = bindung.itembloecke.filter(
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        erledigt_am__isnull=False,
    ).values_list("sitzung_id", flat=True)
    return (
        bindung.teilnahme.sitzung_set.exclude(status=Sitzung.Status.LAUFEND)
        .exclude(pk__in=erledigte_sitzungen)
        .order_by("pk")
        .first()
    )


def _abschlussblock_ist_offen(bindung: Erhebungsbindung) -> bool:
    # Ein Abschluss-Block ist offen, solange er Items hat und nicht erledigt ist.

    if not _block_kann_offen_sein(bindung, Erhebungsitem.Andockpunkt.AM_ENDE):
        return False
    block: Itemblock | None = bindung.itembloecke.filter(
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE
    ).first()
    return block is None or block.erledigt_am is None


def _block_kann_offen_sein(
    bindung: Erhebungsbindung, andockpunkt: Erhebungsitem.Andockpunkt
) -> bool:
    # Nach dem Abschluss der Bindung und ohne Items am Andockpunkt bleibt an
    # diesem Andockpunkt nichts mehr offen.

    if bindung.abgeschlossen_am is not None:
        return False
    return bindung.stichprobe.erhebung.itemzugehoerigkeiten.filter(
        andockpunkt=andockpunkt
    ).exists()


def ziehung_festschreiben(bindung: Erhebungsbindung) -> None:
    """Schreibt die Vignettenreihenfolge dieser Teilnahme genau einmal fest."""

    with transaction.atomic():
        _bindung_sperren(bindung)
        bindung.vignetten_ziehen()


def vignette_beginnen(bindung: Erhebungsbindung) -> Sitzung | None:
    """Beginnt die nächste gezogene Vignette und hält ihre Position fest.

    Läuft bereits eine Sitzung, bleibt es bei ihr; steht keine Vignette mehr an,
    entsteht keine. Beides macht das Kommando gegen einen zweiten Aufruf — aus
    einem Reload wie aus einem zweiten Tab — unempfindlich.
    """

    with transaction.atomic():
        _bindung_sperren(bindung)
        ziehung_festschreiben(bindung)
        match naechster_schritt(bindung):
            case LaufendeSitzung(sitzung):
                return sitzung
            case NochNichtBegonnen() | NaechsteVignette():
                vignette: Vignette | None = _naechste_gezogene_vignette(bindung)
                if vignette is None:
                    return None
                return _sitzung_beginnen(bindung, vignette)
            case _:
                return None


def _sitzung_beginnen(bindung: Erhebungsbindung, vignette: Vignette) -> Sitzung:
    # Startet die persistierte Sitzung und schreibt ihre gezogene Position.

    kern: Simulationskern | None = vignette.gepinnter_kern
    modell_konfiguration: ModellKonfiguration | None = (
        bindung.stichprobe.erhebung.modell_konfiguration
    )
    if kern is None or modell_konfiguration is None:
        raise RuntimeError("Erhebungsvignetten brauchen Kern und Modell-Konfiguration.")
    sink: DBSink = DBSink(bindung.teilnahme)
    sitzung_starten(sink, vignette, kern, modell_konfiguration)
    sitzung: Sitzung = sink.sitzung
    Vignettenposition.objects.create(
        erhebungsbindung=bindung,
        sitzung=sitzung,
        vignette=vignette,
        position=bindung.vignettenziehungen.get(vignette=vignette).position,
    )
    return sitzung


def block_vorlegen(
    bindung: Erhebungsbindung,
    andockpunkt: Erhebungsitem.Andockpunkt,
    sitzung: Sitzung | None = None,
) -> Itemblock | None:
    """Legt Block und Antwortzeilen eines Andockpunkts einmalig an.

    Ohne Items an diesem Andockpunkt entsteht kein Block; die Rückgabe ist dann
    ``None``.
    """

    erhebungsitems: list[Erhebungsitem] = list(
        bindung.stichprobe.erhebung.itemzugehoerigkeiten.filter(andockpunkt=andockpunkt)
    )
    if not erhebungsitems:
        return None
    with transaction.atomic():
        _bindung_sperren(bindung)
        block, _ = Itemblock.objects.get_or_create(
            erhebungsbindung=bindung,
            andockpunkt=andockpunkt,
            sitzung=sitzung,
        )
        for erhebungsitem in erhebungsitems:
            ItemAntwort.objects.get_or_create(
                itemblock=block,
                erhebungsitem=erhebungsitem,
                defaults={"erhebungsbindung": bindung, "sitzung": sitzung},
            )
    return block


def block_erledigen(block: Itemblock) -> None:
    """Hält fest, dass dieser Block abgeschickt wurde — auch leer."""

    with transaction.atomic():
        _bindung_sperren(block.erhebungsbindung)
        Itemblock.objects.filter(pk=block.pk, erledigt_am__isnull=True).update(
            erledigt_am=timezone.now()
        )
        block.refresh_from_db(fields=["erledigt_am"])


def bindung_abschliessen(bindung: Erhebungsbindung) -> None:
    """Hält fest, dass diese Teilnahme fertig ist."""

    with transaction.atomic():
        _bindung_sperren(bindung)
        Erhebungsbindung.objects.filter(
            pk=bindung.pk, abgeschlossen_am__isnull=True
        ).update(abgeschlossen_am=timezone.now())
        bindung.refresh_from_db(fields=["abgeschlossen_am"])


def _bindung_sperren(bindung: Erhebungsbindung) -> None:
    # Hält die Bindungszeile bis zum Ende der Transaktion und serialisiert so die
    # Fortschritts-Kommandos derselben Teilnahme.

    Erhebungsbindung.objects.select_for_update().get(pk=bindung.pk)

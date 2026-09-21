"""Beantwortet, wo eine Erhebungsbindung steht, und schreibt ihren Fortschritt."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from sitzungen.models import Sitzung
from vignetten.models import Vignette

from .models import (
    Erhebungsbindung,
    Erhebungsitem,
    ItemAntwort,
    Itemblock,
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
    """Liefert den offenen Block, die nächste Vignette oder das Ende.

    Die beiden übrigen Fälle des Schritt-Typs bleiben dem Folgeticket #211
    vorbehalten; solange bestimmen die Views sie weiterhin selbst.
    """

    bindung.vignetten_ziehen()
    beurteilte_sitzung: Sitzung | None = _sitzung_mit_offenem_block(bindung)
    if beurteilte_sitzung:
        return OffenerSitzungsblock(beurteilte_sitzung)
    gespielte_ids = bindung.teilnahme.sitzung_set.values_list("vignette_id", flat=True)
    ziehung: Vignettenziehung | None = (
        bindung.vignettenziehungen.select_related("vignette")
        .exclude(vignette_id__in=gespielte_ids)
        .first()
    )
    if ziehung:
        return NaechsteVignette(ziehung.vignette)
    if _abschlussblock_ist_offen(bindung):
        return OffenerAbschlussblock()
    return Ende()


def _sitzung_mit_offenem_block(bindung: Erhebungsbindung) -> Sitzung | None:
    # Liefert die älteste beendete Sitzung, deren Block noch nicht erledigt ist.

    if bindung.abgeschlossen_am is not None:
        return None
    if not bindung.stichprobe.erhebung.itemzugehoerigkeiten.filter(
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG
    ).exists():
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

    if bindung.abgeschlossen_am is not None:
        return False
    if not bindung.stichprobe.erhebung.itemzugehoerigkeiten.filter(
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE
    ).exists():
        return False
    block: Itemblock | None = bindung.itembloecke.filter(
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE
    ).first()
    return block is None or block.erledigt_am is None


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

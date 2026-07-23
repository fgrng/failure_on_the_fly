"""Sequenziert die Vignetten einer Erhebungsteilnahme."""

from __future__ import annotations

from dataclasses import dataclass

from sitzungen.models import Teilnahme
from vignetten.models import Vignette

from .models import Erhebungsbindung, Erhebungsitem, ItemAntwort


@dataclass(frozen=True)
class Itemblock:
    """Die berechneten Items eines Andockpunkts."""

    andockpunkt: str
    items: list[Erhebungsitem]


def block_vorlegen(
    bindung: Erhebungsbindung, andockpunkt: str, sitzung: object | None = None
) -> list[ItemAntwort]:
    """Legt die Antwortzeilen eines Blocks einmalig an."""

    from django.db import transaction

    with transaction.atomic():
        items = bindung.stichprobe.erhebung.itemzugehoerigkeiten.filter(
            andockpunkt=andockpunkt
        )
        for erhebungsitem in items:
            ItemAntwort.objects.get_or_create(
                erhebungsbindung=bindung,
                erhebungsitem=erhebungsitem,
                sitzung=sitzung,
            )
    return list(
        ItemAntwort.objects.filter(
            erhebungsbindung=bindung,
            erhebungsitem__andockpunkt=andockpunkt,
            sitzung=sitzung,
        ).select_related("erhebungsitem__item")
        .order_by("erhebungsitem__position")
    )


def naechster_schritt(teilnahme: Teilnahme) -> Vignette | Itemblock | None:
    """Liefert die nächste ungespielte Vignette oder das definierte Ende."""

    bindung = teilnahme.erhebungsbindung
    bindung.vignetten_ziehen()
    ziehungen = bindung.vignettenziehungen.select_related("vignette")
    gespielte_ids = teilnahme.sitzung_set.values_list("vignette_id", flat=True)
    ziehung = ziehungen.exclude(vignette_id__in=gespielte_ids).first()
    if ziehung:
        return ziehung.vignette
    items = list(
        bindung.stichprobe.erhebung.itemzugehoerigkeiten.filter(
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE
        ).select_related("item")
    )
    return (
        Itemblock(Erhebungsitem.Andockpunkt.AM_ENDE, items)
        if items and bindung.abgeschlossen_am is None
        else None
    )

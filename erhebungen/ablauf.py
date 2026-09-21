"""Sequenziert die Vignetten einer Erhebungsbindung."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from sitzungen.models import Sitzung
from vignetten.models import Vignette

from .models import Erhebungsbindung, Erhebungsitem, ItemAntwort


@dataclass(frozen=True)
class Itemblock:
    """Die berechneten Items eines Andockpunkts."""

    andockpunkt: Erhebungsitem.Andockpunkt
    items: list[Erhebungsitem]
    sitzung: Sitzung | None = None


def block_vorlegen(
    bindung: Erhebungsbindung,
    andockpunkt: Erhebungsitem.Andockpunkt,
    sitzung: Sitzung | None = None,
) -> list[ItemAntwort]:
    """Legt die Antwortzeilen eines Blocks einmalig an."""

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
        )
        .select_related("erhebungsitem__item")
        .order_by("erhebungsitem__position")
    )


def naechster_schritt(bindung: Erhebungsbindung) -> Vignette | Itemblock | None:
    """Liefert die nächste ungespielte Vignette oder das definierte Ende."""

    bindung.vignetten_ziehen()
    ziehungen = bindung.vignettenziehungen.select_related("vignette")
    gespielte_ids = bindung.teilnahme.sitzung_set.values_list("vignette_id", flat=True)
    ziehung = ziehungen.exclude(vignette_id__in=gespielte_ids).first()
    if ziehung:
        return ziehung.vignette
    items = list(
        bindung.stichprobe.erhebung.itemzugehoerigkeiten.filter(
            andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE
        ).select_related("item")
    )
    if not items or bindung.abgeschlossen_am is not None:
        return None
    return Itemblock(Erhebungsitem.Andockpunkt.AM_ENDE, items, None)

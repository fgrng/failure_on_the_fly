"""Sequenziert die Vignetten einer Erhebungsteilnahme."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sitzungen.models import Teilnahme
from vignetten.models import Vignette

if TYPE_CHECKING:
    from fragebogen_items.models import FragebogenItem


def naechster_schritt(teilnahme: Teilnahme) -> Vignette | FragebogenItem | None:
    """Liefert die nächste ungespielte Vignette oder das definierte Ende."""

    bindung = teilnahme.erhebungsbindung
    bindung.vignetten_ziehen()
    vignetten = bindung.vignettenziehungen.select_related("vignette")
    gespielte_ids = teilnahme.sitzung_set.values_list("vignette_id", flat=True)
    ziehung = vignetten.exclude(vignette_id__in=gespielte_ids).first()
    return ziehung.vignette if ziehung else None
